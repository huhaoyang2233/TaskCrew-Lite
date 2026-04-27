"""
执行器 Agent - LangChain 版本
使用 LangChain Agent 调用工具执行任务
"""
import json
import time
import asyncio
from typing import AsyncGenerator, Dict, Any, List

from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage

from core.config import settings
from memory.cache import memory_cache
from prompts.manager import prompt_manager
from mcp_tools.langchain_tools import get_langchain_tools


class ExecutorAgent:
    """
    执行器 Agent
    根据规划器的步骤，调用 MCP 工具执行任务
    """
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        
        # 初始化 LangChain ChatOpenAI
        self.llm = ChatOpenAI(
            model=settings.AGENT_MODEL,
            api_key=settings.AGENT_API_KEY,
            base_url=settings.AGENT_BASE_URL,
            temperature=0.7,
            streaming=True
        )
        
        # 获取工具
        self.tools = get_langchain_tools()
        
        # 系统提示词
        self.system_prompt = prompt_manager.get_prompt("executor")
    
    def _create_agent_executor(self) -> AgentExecutor:
        """创建 LangChain AgentExecutor"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        agent = create_openai_tools_agent(self.llm, self.tools, prompt)
        
        return AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            max_iterations=settings.MAX_ITERATIONS,
            handle_parsing_errors=True
        )
    
    async def execute(self) -> AsyncGenerator[Dict[str, Any], None]:
        """执行工具调用任务 - 使用 LangChain Agent"""
        # 获取上下文
        context = memory_cache.get_context(self.session_id)
        history_message = context.get("current_thoughts", [])
        planner_message = context.get("latest_steps_message", [])
        
        # 构建聊天历史
        chat_history = self._build_chat_history(history_message + planner_message)
        
        # 创建 AgentExecutor
        agent_executor = self._create_agent_executor()
        
        # 执行器输出收集
        executor_message = []
        full_response = ""
        
        try:
            input_text = "根据规划器的步骤，调用合适的工具完成任务。"
            
            # 使用 astream 获取流式输出
            async for chunk in agent_executor.astream({
                "input": input_text,
                "chat_history": chat_history
            }):
                # 处理动作决策
                if "actions" in chunk:
                    for action in chunk["actions"]:
                        tool_msg = f"\n🔧 正在调用工具: {action.tool}"
                        yield {
                            "type": "text",
                            "content": tool_msg,
                            "agent": "executor"
                        }
                        
                        # 记录工具调用
                        tool_call_record = {
                            "role": "assistant",
                            "content": f"[工具调用]: {action.tool} - {json.dumps(action.tool_input, ensure_ascii=False)}"
                        }
                        executor_message.append(tool_call_record)
                
                # 处理消息输出
                if "messages" in chunk:
                    for message in chunk["messages"]:
                        if isinstance(message, AIMessage):
                            content = message.content
                            if content:
                                full_response += content
                                yield {
                                    "type": "text",
                                    "content": content,
                                    "agent": "executor"
                                }
                        
                        elif isinstance(message, ToolMessage):
                            tool_result = {
                                "type": "json",
                                "content": {
                                    "type": "tool_response",
                                    "id": str(int(time.time() * 1000)),
                                    "tool_name": message.name,
                                    "tool_output": message.content
                                },
                                "agent": "executor"
                            }
                            yield tool_result
                            
                            tool_response_record = {
                                "role": "tool",
                                "content": message.content
                            }
                            executor_message.append(tool_response_record)
                
                # 处理最终输出
                if "output" in chunk:
                    output = chunk["output"]
                    if output and output != full_response:
                        full_response = output
                        yield {
                            "type": "text",
                            "content": output,
                            "agent": "executor"
                        }
            
            # 记录 AI 响应
            if full_response:
                ai_record = {
                    "role": "assistant",
                    "content": "[执行器]: " + full_response
                }
                executor_message.append(ai_record)
            
            # 发送执行器完成消息
            yield {
                "type": "json",
                "content": {
                    "type": "ExecutorAgent",
                    "id": str(int(time.time() * 1000)),
                    "response": full_response
                },
                "agent": "executor"
            }
        
        except Exception as e:
            error_msg = f"执行器异常: {str(e)}"
            yield {
                "type": "error",
                "content": error_msg,
                "agent": "executor"
            }
            
            executor_message.append({
                "role": "assistant",
                "content": f"[执行器错误]: {error_msg}"
            })
        
        # 更新全局上下文
        history_message = history_message + executor_message
        memory_cache.update_context(self.session_id, "current_thoughts", history_message)
    
    def _build_chat_history(self, messages: List[Dict]) -> List:
        """将字典消息转换为 LangChain 消息对象"""
        chat_history = []
        
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            
            if role == "user":
                chat_history.append(HumanMessage(content=content))
            elif role == "assistant":
                chat_history.append(AIMessage(content=content))
            elif role == "tool":
                tool_call_id = msg.get("tool_call_id", "")
                chat_history.append(ToolMessage(content=content, tool_call_id=tool_call_id))
            elif role == "system":
                chat_history.append(SystemMessage(content=content))
        
        return chat_history

"""
协调器 Agent (主大脑)
负责协调规划器、执行器和反思器之间的工作
"""
import uuid
import asyncio
from typing import AsyncGenerator, Dict, Any, Optional

from core.config import settings
from memory.cache import memory_cache
from prompts.manager import prompt_manager
from agents.planner import PlannerAgent
from agents.executor import ExecutorAgent
from agents.reflector import ReflectorAgent


class OrchestratorAgent:
    """
    协调器 Agent
    多 Agent 系统的中央协调者
    
    工作流程：
    1. 用户输入
    2. 【规划器】运作 - 分析任务并制定计划
    3. 【执行器】运作 - 调用工具执行计划
    4. 【反思器】运作 - 评估执行结果
    5. 根据反思器决策，决定是否继续循环
    """
    
    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or f"session_{uuid.uuid4().hex[:12]}"
        self.system_prompt = prompt_manager.get_prompt("orchestrator")
        
        # 初始化会话
        memory_cache.create_session(self.session_id)
    
    async def run(self, query: str) -> AsyncGenerator[Dict[str, Any], None]:
        """
        运行协调器
        
        Args:
            query: 用户输入
        """
        try:
            # 初始化用户消息
            memory_cache.update_context(
                self.session_id,
                "user_message",
                [{"role": "user", "content": "[用户]:" + query}]
            )
            
            # 初始化当前思考
            current_thoughts = [{"role": "user", "content": query}]
            memory_cache.update_context(
                self.session_id,
                "current_thoughts",
                current_thoughts
            )
            
            yield {
                "type": "status",
                "content": f"会话已创建: {self.session_id}",
                "agent": "orchestrator"
            }
            
        except Exception as e:
            yield {
                "type": "error",
                "content": f"初始化异常，原因: {e}",
                "agent": "orchestrator"
            }
            return
        
        # 多轮迭代控制
        max_iteration_steps = settings.MAX_REFLECTION_ROUNDS
        iteration_steps = 0
        first_iteration_step = True
        function_call_state = True
        
        while function_call_state and iteration_steps <= max_iteration_steps:
            # ========== 规划器 ==========
            yield {"type": "divider", "content": "【规划器工作】", "agent": "orchestrator"}
            
            planner = PlannerAgent(self.session_id)
            async for message in planner.plan(first_iteration=first_iteration_step):
                yield message
            
            first_iteration_step = False
            yield {"type": "divider", "content": "", "agent": "orchestrator"}
            
            # ========== 执行器 ==========
            yield {"type": "divider", "content": "【执行器工作】", "agent": "orchestrator"}
            
            executor = ExecutorAgent(self.session_id)
            async for message in executor.execute():
                yield message
            
            yield {"type": "divider", "content": "", "agent": "orchestrator"}
            
            # ========== 反思器 ==========
            yield {"type": "divider", "content": "【反思器工作】", "agent": "orchestrator"}
            
            reflector = ReflectorAgent(self.session_id)
            decision = None
            async for message in reflector.reflect():
                yield message
                if message["type"] == "decision":
                    decision = message["content"]
            
            # 解析反思器决策
            if decision:
                decision_value = decision.get("decision", "complete")
                if decision_value == "complete":
                    function_call_state = False
            
            yield {"type": "divider", "content": "", "agent": "orchestrator"}
            iteration_steps += 1
        
        # 清理会话缓存
        memory_cache.clear_session(self.session_id)
        
        yield {
            "type": "status",
            "content": "任务完成",
            "agent": "orchestrator"
        }
    
    async def run_stream(self, query: str) -> AsyncGenerator[str, None]:
        """
        以 SSE 格式流式输出
        """
        async for message in self.run(query):
            # 转换为 SSE 格式
            data = f"data: {message}\n\n"
            yield data

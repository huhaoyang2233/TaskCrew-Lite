"""
规划器 Agent
负责任务分析和步骤规划
"""
import json
import time
import asyncio
from typing import AsyncGenerator, Dict, Any, List
from openai import OpenAI, APIConnectionError, APITimeoutError
import backoff

from core.config import settings
from memory.cache import memory_cache
from prompts.manager import prompt_manager


class PlannerAgent:
    """
    规划器 Agent
    分析用户需求，制定执行计划
    """
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.client = OpenAI(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL
        )
        self.system_prompt = prompt_manager.get_prompt("planner")
    
    @backoff.on_exception(
        backoff.expo,
        (APIConnectionError, APITimeoutError, TimeoutError),
        max_tries=3,
        factor=2
    )
    async def plan(self, first_iteration: bool = True) -> AsyncGenerator[Dict[str, Any], None]:
        """
        执行规划任务
        
        Args:
            first_iteration: 是否是首次迭代（需要注入历史记录）
        """
        # 获取上下文
        context = memory_cache.get_context(self.session_id)
        current_thoughts = context.get("current_thoughts", [])
        
        # 排除工具消息
        current_message = [m for m in current_thoughts if m.get("role") != "tool"]
        
        # 只有首轮需要看到用户的历史记录，后边轮次不需要
        if first_iteration:
            memory_cache.update_context(self.session_id, "current_thoughts", [])
        
        # 构建消息
        messages = [{"role": "system", "content": self.system_prompt}] + current_message
        
        print(f"规划器输入 message（摘要）: {[m['content'][:50] for m in messages]}")
        
        # 流式调用 LLM
        max_retries = 2
        retry_count = 0
        response = ""
        heartbeat_limit = 120
        
        while retry_count <= max_retries:
            try:
                print(f"🌀 第 {retry_count + 1} 次调用规划器...")
                response = ""
                last_chunk_time = time.time()
                
                chunks = self.client.chat.completions.create(
                    model=settings.LLM_MODEL,
                    messages=messages,
                    temperature=0.7,
                    stream=True,
                    timeout=180
                )
                
                for chunk in chunks:
                    # 心跳检测
                    if time.time() - last_chunk_time > heartbeat_limit:
                        raise TimeoutError("流式响应超时（超过120秒无输出）")
                    last_chunk_time = time.time()
                    
                    content = getattr(chunk.choices[0].delta, "content", "") or ""
                    response += content
                    
                    if content.strip():
                        yield {
                            "type": "text",
                            "content": content,
                            "agent": "planner"
                        }
                
                if response.strip():
                    print("✅ 规划器响应成功。")
                    break
                
                retry_count += 1
                print(f"⚠️ 第 {retry_count} 次尝试无效，将重试...")
                if retry_count <= max_retries:
                    await asyncio.sleep(5)
                    
            except (APIConnectionError, APITimeoutError, TimeoutError) as e:
                retry_count += 1
                print(f"❌ 调用规划器异常：{e}，重试({retry_count}/{max_retries})...")
                yield {
                    "type": "error",
                    "content": f"❌ 调用规划器异常：{e}",
                    "agent": "planner"
                }
                await asyncio.sleep(5)
                if retry_count > max_retries:
                    response = f"⚠️ 规划器多次调用失败：{str(e)}"
                    break
            
            except Exception as e:
                retry_count += 1
                print(f"❌ 调用规划器未知错误：{e}，重试({retry_count}/{max_retries})...")
                yield {
                    "type": "error",
                    "content": f"❌ 调用规划器未知错误：{e}",
                    "agent": "planner"
                }
                await asyncio.sleep(5)
                if retry_count > max_retries:
                    response = f"⚠️ 规划器多次调用失败：{str(e)}"
                    break
        
        # 保存结果到上下文
        if response.strip():
            planner_message = [{
                "role": "assistant",
                "content": "【规划器】" + response
            }]
            
            # 更新历史记录
            history_message = current_thoughts + planner_message
            if settings.HISTORY_LIMIT > 0 and len(history_message) > settings.HISTORY_LIMIT:
                history_message = history_message[-settings.HISTORY_LIMIT:]
            
            memory_cache.update_context(self.session_id, "current_thoughts", history_message)
            memory_cache.update_context(self.session_id, "latest_steps_message", [{
                "role": "user",
                "content": "【规划器】" + response
            }])
            
            # 发送最终结果
            yield {
                "type": "json",
                "content": {
                    "type": "PlannerAgent",
                    "id": str(int(time.time() * 1000)),
                    "response": response
                },
                "agent": "planner"
            }
        else:
            yield {
                "type": "text",
                "content": "⚠️ 规划器最终无有效输出。",
                "agent": "planner"
            }

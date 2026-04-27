"""
反思器 Agent
负责评估执行结果并决定下一步行动
"""
import json
import re
import time
import asyncio
from typing import AsyncGenerator, Dict, Any
from openai import OpenAI, APIConnectionError, APITimeoutError

from core.config import settings
from memory.cache import memory_cache
from prompts.manager import prompt_manager


class ReflectorAgent:
    """
    反思器 Agent
    评估任务执行结果，决定是继续还是完成
    """
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.client = OpenAI(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL
        )
        self.system_prompt = prompt_manager.get_prompt("reflector")
    
    async def reflect(self) -> AsyncGenerator[Dict[str, Any], None]:
        """
        执行反思任务
        返回决策结果：continue 或 complete
        """
        # 获取上下文
        context = memory_cache.get_context(self.session_id)
        history_message = context.get("current_thoughts", [])
        
        # 构建消息
        messages = [{
            "role": "system",
            "content": self.system_prompt
        }] + history_message + [{
            "role": "user",
            "content": "根据用户提的问题，【执行器】对【规划器】的执行结果，判断任务是否完成，只返回一个json"
        }]
        
        print(f"反思器输入 message（摘要）: {[m['content'][:50] for m in messages]}")
        
        response = ""
        heartbeat_limit = 120
        max_retries = 2
        retry_count = 0
        decision_data = None
        
        while retry_count <= max_retries:
            try:
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
                        raise TimeoutError("反思器流式响应超时（超过120秒无输出）")
                    last_chunk_time = time.time()
                    
                    content = getattr(chunk.choices[0].delta, "content", "") or ""
                    response += content
                
                if response.strip():
                    break
                
                retry_count += 1
                await asyncio.sleep(5)
                
            except (APIConnectionError, APITimeoutError, TimeoutError) as e:
                retry_count += 1
                yield {
                    "type": "error",
                    "content": f"❌ 反思器调用异常：{e}，重试({retry_count}/{max_retries})",
                    "agent": "reflector"
                }
                await asyncio.sleep(5)
                if retry_count > max_retries:
                    response = f"⚠️ 反思器多次调用失败：{str(e)}"
                    break
            
            except Exception as e:
                retry_count += 1
                yield {
                    "type": "error",
                    "content": f"❌ 反思器未知错误：{e}，重试({retry_count}/{max_retries})",
                    "agent": "reflector"
                }
                await asyncio.sleep(5)
                if retry_count > max_retries:
                    response = f"⚠️ 反思器多次调用失败：{str(e)}"
                    break
        
        # 解析 JSON 响应
        try:
            cleaned = re.sub(r"^```json\s*|\s*```$", "", response.strip(), flags=re.IGNORECASE)
            
            try:
                decision_data = json.loads(cleaned)
            except json.JSONDecodeError:
                # 尝试正则提取 JSON
                match = re.search(r'\{.*\}', response, flags=re.DOTALL)
                if match:
                    try:
                        decision_data = json.loads(match.group(0))
                    except json.JSONDecodeError:
                        decision_data = None
                        yield {
                            "type": "error",
                            "content": "❌ 正则提取 JSON 解析失败",
                            "agent": "reflector"
                        }
                else:
                    decision_data = None
                    yield {
                        "type": "error",
                        "content": "❌ 未找到 JSON 数据",
                        "agent": "reflector"
                    }
            
            if not decision_data:
                decision_data = {"decision": "complete", "reason": "反思内容解析错误"}
            
            reason_text = decision_data.get("reason", "无反思内容")
            
            reflector_message = [{
                "role": "assistant",
                "content": "[反思器]：" + reason_text
            }]
            
            # 发送反思结果
            yield {
                "type": "text",
                "content": reason_text,
                "agent": "reflector"
            }
            
            yield {
                "type": "json",
                "content": {
                    "type": "ReflectorAgent",
                    "id": str(int(time.time() * 1000)),
                    "response": reason_text,
                    "decision": decision_data.get("decision", "complete")
                },
                "agent": "reflector"
            }
            
            # 更新历史记录
            history_message = history_message + reflector_message
            if settings.HISTORY_LIMIT > 0 and len(history_message) > settings.HISTORY_LIMIT:
                history_message = history_message[-settings.HISTORY_LIMIT:]
            
            memory_cache.update_context(self.session_id, "current_thoughts", history_message)
            memory_cache.update_context(self.session_id, "reflector_message", reflector_message)
            
        except Exception as e:
            yield {
                "type": "error",
                "content": f"❌ 处理反思器消息异常: {e}",
                "agent": "reflector"
            }
            yield {
                "type": "text",
                "content": response,
                "agent": "reflector"
            }
            decision_data = {"decision": "complete", "reason": "异常处理"}
        
        # 返回最终决策
        yield {
            "type": "decision",
            "content": decision_data,
            "agent": "reflector"
        }

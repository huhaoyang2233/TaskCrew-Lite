"""
API 路由定义
"""
import json
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from agents.orchestrator import OrchestratorAgent
from memory.cache import memory_cache
from prompts.manager import prompt_manager
from mcp_tools.server import mcp_server


router = APIRouter()


# ========== 请求模型 ==========

class ChatRequest(BaseModel):
    """聊天请求"""
    query: str = Field(..., description="用户输入")
    session_id: Optional[str] = Field(None, description="会话ID，不传则创建新会话")
    stream: bool = Field(True, description="是否流式输出")


class PromptUpdateRequest(BaseModel):
    """更新提示词请求"""
    content: str = Field(..., description="提示词内容")


class PromptCreateRequest(BaseModel):
    """创建提示词请求"""
    name: str = Field(..., description="提示词名称")
    content: str = Field(..., description="提示词内容")
    description: str = Field("", description="提示词描述")


# ========== 聊天接口 ==========

@router.post("/chat")
async def chat(request: ChatRequest):
    """
    执行 Agent 对话
    
    协调器 -> 规划器 -> 执行器 -> 反思器 循环工作
    """
    try:
        orchestrator = OrchestratorAgent(session_id=request.session_id)
        
        if request.stream:
            # 流式输出
            async def event_generator():
                async for message in orchestrator.run(request.query):
                    yield f"data: {json.dumps(message, ensure_ascii=False)}\n\n"
            
            return StreamingResponse(
                event_generator(),
                media_type="text/event-stream"
            )
        else:
            # 非流式输出
            messages = []
            async for message in orchestrator.run(request.query):
                messages.append(message)
            return {
                "success": True,
                "session_id": orchestrator.session_id,
                "messages": messages
            }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chat/stream")
async def chat_stream(
    query: str = Query(..., description="用户输入"),
    session_id: Optional[str] = Query(None, description="会话ID")
):
    """
    GET 方式流式聊天接口
    """
    try:
        orchestrator = OrchestratorAgent(session_id=session_id)
        
        async def event_generator():
            async for message in orchestrator.run(query):
                yield f"data: {json.dumps(message, ensure_ascii=False)}\n\n"
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream"
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== 会话管理接口 ==========

@router.get("/sessions")
async def list_sessions():
    """获取缓存统计信息"""
    return memory_cache.get_stats()


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """删除会话"""
    success = memory_cache.delete_session(session_id)
    if success:
        return {"success": True, "message": f"会话 {session_id} 已删除"}
    raise HTTPException(status_code=404, detail="会话不存在")


@router.get("/sessions/{session_id}/context")
async def get_session_context(session_id: str):
    """获取会话上下文"""
    context = memory_cache.get_context(session_id)
    if context:
        return {"success": True, "context": context}
    raise HTTPException(status_code=404, detail="会话不存在")


# ========== 提示词管理接口 ==========

@router.get("/prompts")
async def list_prompts():
    """列出所有提示词"""
    return {
        "success": True,
        "prompts": {
            "orchestrator": "协调器系统提示词",
            "planner": "规划器系统提示词",
            "executor": "执行器系统提示词",
            "reflector": "反思器系统提示词"
        }
    }


@router.get("/prompts/{name}")
async def get_prompt(name: str):
    """获取提示词内容"""
    content = prompt_manager.get_prompt(name)
    if content:
        return {
            "success": True,
            "name": name,
            "content": content
        }
    raise HTTPException(status_code=404, detail="提示词不存在")


@router.put("/prompts/{name}")
async def update_prompt(name: str, request: PromptUpdateRequest):
    """更新提示词"""
    success = prompt_manager.update_prompt(name, request.content)
    if success:
        return {
            "success": True,
            "message": f"提示词 {name} 已更新"
        }
    raise HTTPException(status_code=404, detail="提示词不存在或不可修改")


@router.post("/prompts")
async def create_prompt(request: PromptCreateRequest):
    """创建新提示词"""
    from prompts.manager import PromptTemplate
    
    template = PromptTemplate(
        name=request.name,
        content=request.content,
        description=request.description
    )
    prompt_manager.register_prompt(template)
    return {
        "success": True,
        "message": f"提示词 {request.name} 已创建"
    }


# ========== MCP 工具接口 ==========

@router.get("/tools")
async def list_tools():
    """列出所有可用 MCP 工具"""
    tools = mcp_server.get_available_tools()
    return {
        "success": True,
        "tools": tools
    }


@router.post("/tools/{tool_name}/invoke")
async def invoke_tool(tool_name: str, parameters: dict):
    """调用指定工具"""
    try:
        result = await mcp_server.invoke_tool(tool_name, parameters)
        return {
            "success": result.success,
            "data": result.data,
            "error": result.error
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== 系统接口 ==========

@router.get("/system/status")
async def system_status():
    """获取系统状态"""
    return {
        "success": True,
        "status": "running",
        "version": "2.0.0",
        "components": {
            "memory_cache": memory_cache.get_stats(),
            "tools": len(mcp_server.get_available_tools())
        }
    }

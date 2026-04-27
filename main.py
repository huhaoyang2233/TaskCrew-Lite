"""
Deep Agents - FastAPI + LangChain + MCP 版本
基于 FastAPI 和 LangChain 的多 Agent 智能体系统
"""
import uvicorn
from fastapi import FastAPI
from contextlib import asynccontextmanager

from api.routes import router
from core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    print("🚀 Deep Agents 服务启动中...")
    yield
    # 关闭时执行
    print("🛑 Deep Agents 服务关闭中...")


app = FastAPI(
    title="Deep Agents API",
    description="基于 FastAPI + LangChain + MCP 的多 Agent 智能体系统",
    version="2.0.0",
    lifespan=lifespan
)

# 注册路由
app.include_router(router, prefix="/api/v1")


@app.get("/")
async def root():
    return {
        "message": "Deep Agents API 服务运行中",
        "version": "2.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )

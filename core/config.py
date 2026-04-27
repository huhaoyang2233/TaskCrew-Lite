"""
配置管理模块
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """应用配置"""
    # 服务配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True
    
    # 大模型配置 - 通用模型
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_BASE_URL: str = "https://api.openai.com/v1"
    LLM_API_KEY: str = ""
    
    # 大模型配置 - Agent 工具调用模型
    AGENT_MODEL: str = "gpt-4o-mini"
    AGENT_BASE_URL: str = "https://api.openai.com/v1"
    AGENT_API_KEY: str = ""
    
    # MCP 配置
    MCP_SERVER_URL: Optional[str] = None
    MCP_TIMEOUT: int = 30
    
    # 历史记录配置
    ENABLE_HISTORY: bool = True
    HISTORY_LIMIT: int = 10
    ENABLE_HISTORY_PATTERN: bool = False
    HISTORY_PATTERN: str = r"【(.*?)】"
    
    # Agent 配置
    MAX_ITERATIONS: int = 10
    MAX_REFLECTION_ROUNDS: int = 4
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

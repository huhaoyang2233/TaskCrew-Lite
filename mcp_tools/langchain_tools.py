"""
将 MCP 工具转换为 LangChain 工具
"""
import json
from typing import Type
from pydantic import BaseModel, Field
from langchain.tools import BaseTool
from langchain.callbacks.manager import CallbackManagerForToolRun

from mcp_tools.server import mcp_server


class CalculatorInput(BaseModel):
    expression: str = Field(description="数学表达式")


class WeatherInput(BaseModel):
    city: str = Field(description="城市名称")
    date: str = Field(default="today", description="日期")


class SearchInput(BaseModel):
    query: str = Field(description="搜索关键词")
    limit: int = Field(default=5, description="返回数量")


class KnowledgeInput(BaseModel):
    query: str = Field(description="查询内容")
    category: str = Field(default="通用", description="知识类别")


class CalculatorTool(BaseTool):
    name: str = "calculator"
    description: str = "执行数学计算"
    args_schema: Type[BaseModel] = CalculatorInput
    
    def _run(self, expression: str, run_manager: CallbackManagerForToolRun = None) -> str:
        import asyncio
        return asyncio.get_event_loop().run_until_complete(self._arun(expression, run_manager))
    
    async def _arun(self, expression: str, run_manager: CallbackManagerForToolRun = None) -> str:
        result = await mcp_server.invoke_tool("calculator", {"expression": expression})
        return json.dumps(result.data, ensure_ascii=False) if result.success else f"错误: {result.error}"


class WeatherTool(BaseTool):
    name: str = "get_weather"
    description: str = "获取天气信息"
    args_schema: Type[BaseModel] = WeatherInput
    
    def _run(self, city: str, date: str = "today", run_manager: CallbackManagerForToolRun = None) -> str:
        import asyncio
        return asyncio.get_event_loop().run_until_complete(self._arun(city, date, run_manager))
    
    async def _arun(self, city: str, date: str = "today", run_manager: CallbackManagerForToolRun = None) -> str:
        result = await mcp_server.invoke_tool("get_weather", {"city": city, "date": date})
        return json.dumps(result.data, ensure_ascii=False) if result.success else f"错误: {result.error}"


class SearchTool(BaseTool):
    name: str = "web_search"
    description: str = "搜索网络信息"
    args_schema: Type[BaseModel] = SearchInput
    
    def _run(self, query: str, limit: int = 5, run_manager: CallbackManagerForToolRun = None) -> str:
        import asyncio
        return asyncio.get_event_loop().run_until_complete(self._arun(query, limit, run_manager))
    
    async def _arun(self, query: str, limit: int = 5, run_manager: CallbackManagerForToolRun = None) -> str:
        result = await mcp_server.invoke_tool("web_search", {"query": query, "limit": limit})
        return json.dumps(result.data, ensure_ascii=False) if result.success else f"错误: {result.error}"


class KnowledgeTool(BaseTool):
    name: str = "query_knowledge"
    description: str = "查询知识库"
    args_schema: Type[BaseModel] = KnowledgeInput
    
    def _run(self, query: str, category: str = "通用", run_manager: CallbackManagerForToolRun = None) -> str:
        import asyncio
        return asyncio.get_event_loop().run_until_complete(self._arun(query, category, run_manager))
    
    async def _arun(self, query: str, category: str = "通用", run_manager: CallbackManagerForToolRun = None) -> str:
        result = await mcp_server.invoke_tool("query_knowledge", {"query": query, "category": category})
        return json.dumps(result.data, ensure_ascii=False) if result.success else f"错误: {result.error}"


def get_langchain_tools() -> list:
    return [CalculatorTool(), WeatherTool(), SearchTool(), KnowledgeTool()]

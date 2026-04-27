"""
MCP 工具服务器
"""
import json
import asyncio
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum


class ToolParameterType(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"


@dataclass
class ToolParameter:
    name: str
    type: ToolParameterType
    description: str
    required: bool = True
    enum: Optional[List[str]] = None
    default: Any = None


@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: List[ToolParameter] = field(default_factory=list)
    
    def to_openai_format(self) -> Dict[str, Any]:
        properties = {}
        required = []
        for param in self.parameters:
            prop = {"type": param.type.value, "description": param.description}
            if param.enum:
                prop["enum"] = param.enum
            properties[param.name] = prop
            if param.required:
                required.append(param.name)
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
        }


@dataclass
class ToolResult:
    success: bool
    data: Any
    error: Optional[str] = None


class MCPToolRegistry:
    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
        self._handlers: Dict[str, Callable] = {}
    
    def register_tool(self, definition: ToolDefinition, handler: Callable) -> bool:
        self._tools[definition.name] = definition
        self._handlers[definition.name] = handler
        return True
    
    def get_handler(self, name: str) -> Optional[Callable]:
        return self._handlers.get(name)
    
    def get_tools_openai_format(self) -> List[Dict[str, Any]]:
        return [tool.to_openai_format() for tool in self._tools.values()]


class MCPServer:
    def __init__(self):
        self.registry = MCPToolRegistry()
        self._init_mock_tools()
    
    def _init_mock_tools(self):
        search_tool = ToolDefinition(
            name="web_search",
            description="搜索网络信息",
            parameters=[
                ToolParameter(name="query", type=ToolParameterType.STRING, description="搜索关键词"),
                ToolParameter(name="limit", type=ToolParameterType.INTEGER, description="返回数量", required=False)
            ]
        )
        async def search_handler(query: str, limit: int = 5) -> ToolResult:
            await asyncio.sleep(0.5)
            return ToolResult(success=True, data={"query": query, "results": []})
        self.registry.register_tool(search_tool, search_handler)
        
        calculator_tool = ToolDefinition(
            name="calculator",
            description="执行数学计算",
            parameters=[ToolParameter(name="expression", type=ToolParameterType.STRING, description="数学表达式")]
        )
        async def calculator_handler(expression: str) -> ToolResult:
            try:
                result = eval(expression)
                return ToolResult(success=True, data={"expression": expression, "result": result})
            except Exception as e:
                return ToolResult(success=False, data=None, error=str(e))
        self.registry.register_tool(calculator_tool, calculator_handler)
        
        weather_tool = ToolDefinition(
            name="get_weather",
            description="获取天气信息",
            parameters=[
                ToolParameter(name="city", type=ToolParameterType.STRING, description="城市名称"),
                ToolParameter(name="date", type=ToolParameterType.STRING, description="日期", required=False)
            ]
        )
        async def weather_handler(city: str, date: str = "today") -> ToolResult:
            await asyncio.sleep(0.3)
            return ToolResult(success=True, data={"city": city, "temperature": 25, "condition": "晴"})
        self.registry.register_tool(weather_tool, weather_handler)
        
        knowledge_tool = ToolDefinition(
            name="query_knowledge",
            description="查询知识库",
            parameters=[
                ToolParameter(name="query", type=ToolParameterType.STRING, description="查询内容"),
                ToolParameter(name="category", type=ToolParameterType.STRING, description="类别", required=False)
            ]
        )
        async def knowledge_handler(query: str, category: str = "通用") -> ToolResult:
            await asyncio.sleep(0.4)
            return ToolResult(success=True, data={"query": query, "results": []})
        self.registry.register_tool(knowledge_tool, knowledge_handler)
    
    async def invoke_tool(self, tool_name: str, parameters: Dict[str, Any]) -> ToolResult:
        handler = self.registry.get_handler(tool_name)
        if not handler:
            return ToolResult(success=False, data=None, error=f"工具 '{tool_name}' 不存在")
        try:
            if asyncio.iscoroutinefunction(handler):
                result = await handler(**parameters)
            else:
                result = handler(**parameters)
            return result
        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e))
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        return self.registry.get_tools_openai_format()


mcp_server = MCPServer()

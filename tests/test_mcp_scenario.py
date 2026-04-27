"""
MCP 测试场景
模拟真实使用场景测试 MCP 工具调用
"""
import asyncio
import json
from typing import List, Dict, Any

from mcp_tools.server import mcp_server, ToolDefinition, ToolParameter, ToolResult
from memory.cache import memory_cache


class MCPTestScenario:
    """
    MCP 测试场景类
    提供各种测试场景验证 MCP 工具调用
    """
    
    def __init__(self):
        self.results: List[Dict[str, Any]] = []
    
    async def test_single_tool(self, tool_name: str, parameters: Dict) -> Dict:
        """测试单个工具调用"""
        print(f"\n{'='*50}")
        print(f"测试工具: {tool_name}")
        print(f"参数: {json.dumps(parameters, ensure_ascii=False)}")
        print(f"{'='*50}")
        
        result = await mcp_server.invoke_tool(tool_name, parameters)
        
        test_result = {
            "tool": tool_name,
            "parameters": parameters,
            "success": result.success,
            "data": result.data,
            "error": result.error
        }
        
        if result.success:
            print(f"✅ 成功: {json.dumps(result.data, ensure_ascii=False, indent=2)[:500]}")
        else:
            print(f"❌ 失败: {result.error}")
        
        self.results.append(test_result)
        return test_result
    
    async def test_calculator(self):
        """测试计算器工具"""
        print("\n📐 场景1: 数学计算")
        
        test_cases = [
            {"expression": "2 + 2"},
            {"expression": "10 * 5"},
            {"expression": "sqrt(16)"},
            {"expression": "100 / 4"},
        ]
        
        for params in test_cases:
            await self.test_single_tool("calculator", params)
    
    async def test_weather(self):
        """测试天气查询工具"""
        print("\n🌤 场景2: 天气查询")
        
        test_cases = [
            {"city": "北京"},
            {"city": "上海", "date": "2024-01-01"},
            {"city": "广州"},
        ]
        
        for params in test_cases:
            await self.test_single_tool("get_weather", params)
    
    async def test_search(self):
        """测试搜索工具"""
        print("\n🔍 场景3: 网络搜索")
        
        test_cases = [
            {"query": "FastAPI 教程", "limit": 3},
            {"query": "Python 异步编程"},
        ]
        
        for params in test_cases:
            await self.test_single_tool("web_search", params)
    
    async def test_knowledge(self):
        """测试知识库查询工具"""
        print("\n📚 场景4: 知识库查询")
        
        test_cases = [
            {"query": "FastAPI 最佳实践", "category": "技术"},
            {"query": "产品发布流程", "category": "产品"},
            {"query": "公司介绍"},
        ]
        
        for params in test_cases:
            await self.test_single_tool("query_knowledge", params)
    
    async def test_memory_cache(self):
        """测试内存缓存"""
        print("\n💾 场景5: 内存缓存测试")
        print(f"{'='*50}")
        
        # 创建会话
        session_id = memory_cache.create_session()
        print(f"创建会话: {session_id}")
        
        # 添加消息
        memory_cache.add_message(session_id, "user", "你好")
        memory_cache.add_message(session_id, "assistant", "你好！有什么可以帮助你？")
        memory_cache.add_message(session_id, "user", "查询天气")
        
        # 获取消息
        messages = memory_cache.get_messages(session_id)
        print(f"消息数量: {len(messages)}")
        print(f"消息内容: {json.dumps(messages, ensure_ascii=False, indent=2)}")
        
        # 更新上下文
        memory_cache.update_context(session_id, "current_thoughts", messages)
        context = memory_cache.get_context(session_id)
        print(f"上下文: {json.dumps(context, ensure_ascii=False, indent=2)[:500]}")
        
        # 清理
        memory_cache.clear_session(session_id)
        print(f"✅ 缓存测试完成")
        
        self.results.append({
            "scenario": "memory_cache",
            "success": True,
            "session_id": session_id
        })
    
    async def run_all_tests(self):
        """运行所有测试"""
        print("\n" + "="*60)
        print("🧪 MCP 测试场景开始")
        print("="*60)
        
        await self.test_calculator()
        await self.test_weather()
        await self.test_search()
        await self.test_knowledge()
        await self.test_memory_cache()
        
        print("\n" + "="*60)
        print("📊 测试总结")
        print("="*60)
        
        success_count = sum(1 for r in self.results if r.get("success"))
        total_count = len(self.results)
        
        print(f"总测试数: {total_count}")
        print(f"成功: {success_count}")
        print(f"失败: {total_count - success_count}")
        
        return self.results


async def main():
    """主函数"""
    scenario = MCPTestScenario()
    results = await scenario.run_all_tests()
    
    # 保存测试结果
    with open("test_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print("\n💾 测试结果已保存到 test_results.json")


if __name__ == "__main__":
    asyncio.run(main())

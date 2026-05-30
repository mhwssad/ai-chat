"""core/tools 模块使用示例。

演示工具发现、搜索、执行、绑定和 API 调用的完整流程。

运行: PYTHONPATH=. uv run python docs/examples/tool_usage.py
"""


import sys
import io

# Windows 终端 UTF-8 兼容
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


# ── 1. 列出工具 ──────────────────────────────────────────


def demo_list_tools():
    """列出所有已注册工具。"""
    from src.ai.core.tools import tool_manager

    tools = tool_manager.list_tools()
    enabled = tool_manager.list_tools(enabled_only=True)

    print("=== 列出工具 ===")
    print(f"  全部工具: {len(tools)} 个")
    print(f"  已启用:   {len(enabled)} 个")
    print()
    for t in enabled[:10]:
        desc = t.description[:60] if t.description else ""
        print(f"  - {t.name}: {desc}")
    if len(enabled) > 10:
        print(f"  ... 共 {len(enabled)} 个")
    print()


# ── 2. 搜索工具 ──────────────────────────────────────────


def demo_search_tools():
    """按关键词搜索工具。"""
    from src.ai.core.tools import tool_manager

    print("=== 搜索工具 ===")
    for query in ["file", "bash", "search", "sleep"]:
        results = tool_manager.search_tools(query)
        names = [t.name for t in results]
        print(f'  "{query}": {names}')
    print()


# ── 3. 异步执行工具 ──────────────────────────────────────────


async def demo_execute_async():
    """异步执行工具调用。"""
    from src.ai.core.tools import tool_manager

    print("=== 异步执行工具 ===")

    result = await tool_manager.execute("glob_files", {"pattern": "*.md"})
    preview = str(result)[:100] if result else "(空)"
    print(f"  glob_files: {preview}...")

    result2 = await tool_manager.execute("tool_search", {"query": "file"})
    preview2 = str(result2)[:100] if result2 else "(空)"
    print(f"  tool_search: {preview2}...")
    print()


# ── 4. API 端点参考 ──────────────────────────────────────────


def demo_api_endpoints():
    """工具 API 端点调用方式。"""
    print("=== API 端点参考 ===")
    print()
    print("# 列出工具")
    print('curl http://127.0.0.1:8000/api/tools')
    print()
    print("# 列出已启用工具")
    print('curl "http://127.0.0.1:8000/api/tools?enabled_only=true"')
    print()
    print("# 调用工具")
    print('curl -X POST http://127.0.0.1:8000/api/tools/call \\')
    print('  -H "Content-Type: application/json" \\')
    print('  -d \'{"tool_name": "glob_files", "arguments": {"pattern": "**/*.md"}}\'')
    print()


# ── 主入口 ──────────────────────────────────────────────

if __name__ == "__main__":
    import asyncio

    print(">>> Tools 模块示例 <<<\n")

    demo_list_tools()
    demo_search_tools()
    asyncio.run(demo_execute_async())
    demo_api_endpoints()

    print(">>> 示例结束 <<<")

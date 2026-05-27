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
        print(f"  - {t.name} ({t.source_type}): {desc}")
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


# ── 3. 同步执行工具 ──────────────────────────────────────────


def demo_execute_sync():
    """同步执行工具调用。"""
    from src.ai.core.tools import ToolCallRequest, tool_manager

    print("=== 同步执行工具 ===")

    # 执行 Sleep 工具
    result = tool_manager.execute_sync(ToolCallRequest(
        tool_name="Sleep",
        arguments={"seconds": 0.1},
    ))
    print(f"  Sleep: content={result.content}, is_error={result.is_error}")

    # 执行 ToolSearch
    result2 = tool_manager.execute_sync(ToolCallRequest(
        tool_name="ToolSearch",
        arguments={"query": "file"},
    ))
    content_preview = str(result2.content)[:100] if result2.content else "(空)"
    print(f"  ToolSearch: {content_preview}...")
    print()


# ── 4. ToolBinding 构造 ──────────────────────────────────────────


def demo_tool_binding():
    """ToolBinding 和 ChatRequest 构造。"""
    from src.ai.core.models import ChatMessage, ChatRequest
    from src.ai.core.models.types import ToolBinding

    tools = [
        ToolBinding(
            name="file_read",
            description="读取本地文件内容",
            input_schema={
                "type": "object",
                "properties": {"path": {"type": "string", "description": "文件路径"}},
                "required": ["path"],
            },
        ),
    ]

    request = ChatRequest(
        messages=[
            ChatMessage(role="system", content="你是一个文件助手。"),
            ChatMessage(role="user", content="读取 README.md"),
        ],
        temperature=0.7,
        max_tokens=200,
        tools=tools,
        tool_choice="auto",
    )

    print("=== ToolBinding + ChatRequest ===")
    print(f"  tools: {[t.name for t in request.tools]}")
    print(f"  tool_choice: {request.tool_choice}")
    print(f"  messages: {len(request.messages)} 条")
    print()


# ── 5. bind_tools 流程 ──────────────────────────────────────────


def demo_bind_tools_in_chat():
    """bind_tools 在 ChatService 中的工作方式。"""
    from src.ai.core.tools import tool_manager

    print("=== bind_tools 工作流程 ===")
    print("  1. ChatCompletionRequest.bind_tools = True")
    print("  2. ChatService._to_chat_request() 调用 tool_manager.list_tool_bindings()")
    print("  3. 返回 list[ToolBinding]，绑定到 ChatRequest.tools")
    print("  4. ModelClient 将 ToolBinding 转为 LangChain function schema")
    print("  5. llm.bind_tools(schema) 绑定到模型调用")
    print()

    bindings = tool_manager.list_tool_bindings(essential_only=True)
    print(f"  essential 工具 bindings: {len(bindings)} 个")
    for b in bindings[:5]:
        print(f"  - {b.name} ({b.source_type})")
    print()


# ── 6. API 端点参考 ──────────────────────────────────────────


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
    print('  -d \'{"tool_name": "Sleep", "arguments": {"seconds": 1}}\'')
    print()
    print("# 带工具的 Chat 请求")
    print('curl -X POST http://127.0.0.1:8000/api/chat/completions \\')
    print('  -H "Content-Type: application/json" \\')
    print('  -d \'{"messages": [{"role": "user", "content": "读取 README.md"}],')
    print('       "bind_tools": true,')
    print('       "tool_choice": "auto"}\'')
    print()


# ── 主入口 ──────────────────────────────────────────────

if __name__ == "__main__":
    print(">>> Tools 模块示例 <<<\n")

    demo_list_tools()
    demo_search_tools()
    demo_execute_sync()
    demo_tool_binding()
    demo_bind_tools_in_chat()
    demo_api_endpoints()

    print(">>> 示例结束 <<<")

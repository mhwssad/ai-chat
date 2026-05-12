"""MCP 模块管理入口。"""

from src.ai_chat.mcp import mcp_settings, mcp_client_manager, mcp_server_manager


def _choose(prompt: str, options: list[str]) -> int:
    for i, opt in enumerate(options, 1):
        print(f"  {i}. {opt}")
    while True:
        raw = input(prompt).strip()
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return int(raw)


def menu_mcp():
    """MCP 管理 — 状态、加载工具、启动服务器。"""
    while True:
        print("\n── MCP 管理 ──")
        idx = _choose("操作: ", [
            "查看 MCP 状态",
            "加载 MCP 工具",
            "启动 MCP 服务器（暴露内置工具）",
            "返回上级",
        ])
        if idx == 4:
            return

        if idx == 1:
            print(f"\n  MCP 客户端: {'已启用' if mcp_settings.mcp_enabled else '未启用'}")
            print(f"  MCP 服务器: {'已启用' if mcp_settings.mcp_server_enabled else '未启用'}")
            configs = mcp_settings.get_server_configs()
            if configs:
                print(f"  已配置服务器: {', '.join(configs.keys())}")
            else:
                print("  已配置服务器: （无）")
            if mcp_client_manager.is_initialized:
                tools = mcp_client_manager.tools
                print(f"  已加载 MCP 工具: {len(tools)} 个")
                for t in tools:
                    desc = t.description.split("\n")[0] if t.description else "无描述"
                    print(f"    - {t.name}: {desc}")
            else:
                print("  已加载 MCP 工具: （未初始化）")
            print()

        elif idx == 2:
            if mcp_client_manager.is_initialized:
                print("  MCP 工具已加载，无需重复初始化。\n")
                continue
            count = mcp_client_manager.run_sync(mcp_client_manager.initialize())
            print(f"  已加载 {count} 个 MCP 工具\n")

        elif idx == 3:
            print(f"\n  启动 MCP 服务器: {mcp_settings.mcp_server_host}:{mcp_settings.mcp_server_port}")
            print(f"  传输方式: {mcp_settings.mcp_server_transport}")
            print("  按 Ctrl+C 停止\n")
            try:
                mcp_server_manager.start()
            except KeyboardInterrupt:
                print("\n  MCP 服务器已停止。\n")

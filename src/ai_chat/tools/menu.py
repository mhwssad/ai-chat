"""Tools 模块管理入口。"""

from src.ai_chat.tools.registry import tool_registry


def _choose(prompt: str, options: list[str]) -> int:
    for i, opt in enumerate(options, 1):
        print(f"  {i}. {opt}")
    while True:
        raw = input(prompt).strip()
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return int(raw)


def menu_tools():
    """工具管理 — 列出已注册工具。"""
    while True:
        print("\n── 工具管理 ──")
        idx = _choose("操作: ", [
            "列出已注册工具",
            "返回上级",
        ])
        if idx == 2:
            return

        tools = tool_registry.get_all()
        if not tools:
            print("  （无）\n")
            continue
        for t in tools:
            desc = t.description.split("\n")[0] if t.description else "无描述"
            tool_type = tool_registry.get_record(t.name).tool_type.value
            print(f"  {t.name} [{tool_type}]: {desc}")
        print()

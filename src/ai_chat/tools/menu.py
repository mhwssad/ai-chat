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
            "查看工具详情",
            "返回上级",
        ])
        if idx == 3:
            return

        if idx == 1:
            tools = tool_registry.get_all()
            if not tools:
                print("  （无）\n")
                continue
            for t in tools:
                record = tool_registry.get_record(t.name)
                desc = t.description.split("\n")[0] if t.description else "无描述"
                print(f"  {t.name} [{record.tool_type.value}] v{record.version}: {desc}")
            print()

        elif idx == 2:
            name = input("  工具名称: ").strip()
            try:
                record = tool_registry.get_record(name)
                t = record.tool
                print(f"\n  名称: {t.name}")
                print(f"  类型: {record.tool_type.value}")
                print(f"  版本: {record.version}")
                if record.author:
                    print(f"  作者: {record.author}")
                print(f"  来源: {record.source_module or '未知'}")
                print(f"  描述: {t.description.split(chr(10))[0] if t.description else '无'}")
                print()
            except KeyError as e:
                print(f"  {e}\n")

"""Skills 模块管理入口。"""

from src.ai_chat.skills import skill_registry


def _choose(prompt: str, options: list[str]) -> int:
    for i, opt in enumerate(options, 1):
        print(f"  {i}. {opt}")
    while True:
        raw = input(prompt).strip()
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return int(raw)


def _print_skills():
    skills = skill_registry.get_all(enabled_only=True)
    if not skills:
        print("  （无可用技能）\n")
        return
    print("\n  可用技能：")
    print(f"  {'命令':<20} {'优先级':<8} {'说明'}")
    print(f"  {'-' * 20} {'-' * 8} {'-' * 30}")
    for s in skills:
        print(f"  /{s.name:<19} {s.priority:<8} {s.description}")
    print(f"\n  {'/clear':<20} 清除当前技能")
    print(f"  {'/skills':<20} 显示此帮助")
    print()


def menu_skills():
    """技能管理 — 列出、查看详情。"""
    while True:
        print("\n── 技能管理 ──")
        idx = _choose("操作: ", [
            "列出可用技能",
            "查看技能详情",
            "返回上级",
        ])
        if idx == 3:
            return

        if idx == 1:
            _print_skills()

        elif idx == 2:
            name = input("  技能名称: ").strip().lstrip("/")
            try:
                skill = skill_registry.get(name)
                print(f"\n  名称: /{skill.name}")
                print(f"  描述: {skill.description}")
                print(f"  工具: {', '.join(skill.tools) if skill.tools else '全部'}")
                print(f"  模型: {skill.model or '默认'}")
                print(f"  参数: {skill.args_template or '无'}")
                print(f"  优先级: {skill.priority}")
                print(f"  状态: {'启用' if skill.enabled else '禁用'}")
                print(f"\n  指令:\n  {skill.system_prompt}\n")
            except KeyError as e:
                print(f"  {e}\n")

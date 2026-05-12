"""Graphs 模块管理入口 — Agent 选择、对话循环、技能支持。"""

from src.ai_chat.graphs.factory import agent_factory
from src.ai_chat.mcp import mcp_settings, mcp_client_manager
from src.ai_chat.skills import skill_registry
from src.ai_chat.skills.models import SkillConfig
from src.ai_chat.tools import tool_registry


def _choose(prompt: str, options: list[str]) -> int:
    for i, opt in enumerate(options, 1):
        print(f"  {i}. {opt}")
    while True:
        raw = input(prompt).strip()
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return int(raw)


def _choose_model() -> str:
    model = input("  模型名称（回车默认 qwen-turbo）: ").strip()
    return model or "qwen-turbo"


def _ensure_mcp_tools():
    if not mcp_settings.mcp_enabled:
        return
    if mcp_client_manager.is_initialized:
        return
    print("正在加载 MCP 工具...")
    count = mcp_client_manager.run_sync(mcp_client_manager.initialize())
    print(f"已加载 {count} 个 MCP 工具\n")


def _print_skills():
    skills = skill_registry.get_all()
    if not skills:
        print("  （无可用技能）\n")
        return
    print("\n  可用技能：")
    print(f"  {'命令':<20} {'说明'}")
    print(f"  {'-' * 20} {'-' * 30}")
    for s in skills:
        print(f"  /{s.name:<19} {s.description}")
    print(f"\n  {'/clear':<20} 清除当前技能")
    print(f"  {'/skills':<20} 显示此帮助")
    print()


def _extract_skill_args(text: str, skill_name: str) -> str:
    prefix = f"/{skill_name}"
    if text == prefix:
        return ""
    if text.startswith(prefix + " "):
        return text[len(prefix):].strip()
    return ""


def _invoke_skill(agent, skill: SkillConfig, user_text: str):
    try:
        kwargs = dict(
            system_prompt_override=skill.system_prompt,
            tools_override=_get_skill_tools(skill),
            model_override=skill.model,
        )
        response = agent.invoke(user_text, **kwargs)
        print(f"AI: {response}\n")
    except Exception as e:
        print(f"  技能执行失败：{e}\n")


def _get_skill_tools(skill: SkillConfig):
    if not skill.tools:
        return None
    all_tools = tool_registry.get_all()
    return [t for t in all_tools if t.name in skill.tools]


_AGENT_MENU = {
    1: ("unified", "UnifiedAgent（记忆 + 工具 + RAG + 技能）"),
    2: ("chat", "ChatAgent（ReAct + 工具 + 技能）"),
    3: ("chat_graph", "ChatGraph（意图分类 + RAG）"),
}


def menu_chat():
    """graphs 模块管理入口 — 选择 agent、进入对话。"""
    while True:
        print("\n── 对话模式 ──")
        labels = [v[1] for v in _AGENT_MENU.values()] + ["返回上级"]
        idx = _choose("选择 Agent: ", labels)
        if idx == len(labels):
            return

        name = _AGENT_MENU[idx][0]
        model = _choose_model()
        _ensure_mcp_tools()

        agent = agent_factory.create(name, model_name=model)

        if agent_factory.has_chat(name):
            agent.chat()
        else:
            _chat_loop(agent, name)


def _chat_loop(agent, agent_name: str):
    """通用对话循环，含技能支持。"""
    supports_skills = agent_factory.supports_overrides(agent_name)
    if supports_skills:
        print("输入 'quit' 或 'exit' 退出，'/skills' 查看可用技能\n")
    else:
        print("输入 'quit' 或 'exit' 退出\n")

    active_skill: SkillConfig | None = None

    while True:
        user_input = input("你: ").strip()
        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit"):
            break

        # 内置命令（仅技能支持时）
        if supports_skills:
            if user_input in ("/skills", "/help"):
                _print_skills()
                continue
            if user_input == "/clear":
                active_skill = None
                print("  已清除技能，恢复默认对话模式。\n")
                continue

            # 技能匹配
            matched = skill_registry.find_by_trigger(user_input)
            if matched is not None:
                active_skill = matched
                args = _extract_skill_args(user_input, matched.name)
                if args:
                    _invoke_skill(agent, active_skill, args)
                    active_skill = None
                else:
                    print(f"  已激活技能: /{matched.name} — {matched.description}")
                    print(f"  输入内容后按回车执行，或 /clear 取消。\n")
                continue

            # 技能模式执行
            if active_skill is not None:
                _invoke_skill(agent, active_skill, user_input)
                active_skill = None
                continue

        # 普通对话
        response = agent.invoke(user_input)
        print(f"AI: {response}\n")

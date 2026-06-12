"""Skills 模块使用示例。

演示 Skills 与 LLM 的完整集成：发现技能 → 激活 → 注入上下文 → 调用模型。
Skills 从文件系统（SKILL.md）发现，遵循 Agent Skills 开放标准。

运行: PYTHONPATH=. uv run python docs/examples/skill_usage.py
"""


import json
import re
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from src.ai.config.model_settings import chat_model_config
from src.ai.core.container import container
from src.ai.core.skills import SkillLoader
from src.ai.exception.skill_exception import SkillError

# 从容器获取服务实例
model_registry = container.model_container.model_registry()
skill_service = container.skill_container.skill_service()


def _build_llm():
    """构建 LangChain BaseChatModel。"""
    builder = model_registry.get_builder("chat", chat_model_config.backend)
    return builder.build(chat_model_config)


def demo_discover() -> None:
    """发现所有技能（从 skills/ 目录扫描 SKILL.md）。"""
    skills = skill_service.discover()
    print(f"[discover] 发现 {len(skills)} 个技能:")
    for s in skills:
        print(
            f"  - {s.name}: auto={s.is_auto_triggerable}, "
            f"arg_hint={s.argument_hint}, user_invocable={s.user_invocable}"
        )


def demo_get_single() -> None:
    """按 name 获取单个技能。"""
    skill = skill_service.get("translate")
    if skill:
        print(f"[get] translate: {skill.description}")
        print(f"       指令模板长度: {len(skill.instruction_template)} 字符")
    else:
        print("[get] translate 技能不存在")


def demo_activate() -> None:
    """激活技能（Level 2：$ARGUMENTS 替换 + !`command` 执行）。"""
    result = skill_service.activate("translate", arguments="hello world to 日语")
    print("[activate] translate 渲染结果:")
    print(result)
    print()


def demo_progressive_disclosure() -> None:
    """渐进式披露：Level 1 → Level 2 → Level 3。"""
    # Level 1: 元数据 — 始终加载，约 100 tokens/技能
    metadata = skill_service.get_skill_metadata()
    print(f"[Level 1] {len(metadata)} 个技能元数据（~100 tokens/技能）:")
    for m in metadata:
        print(f"  - {m.name}: {m.description[:50]}...")
    print()

    # Level 2: 完整指令 — 激活时加载
    skill = skill_service.get("code-review")
    if skill:
        print(f"[Level 2] 完整指令 ({len(skill.instruction_template)} 字符):")
        print(f"  {skill.instruction_template[:100]}...")
    print()

    # Level 3: 辅助文件 — 按需读取（本示例无辅助文件）
    refs = skill_service.list_references("code-review")
    scripts = skill_service.list_scripts("code-review")
    print(f"[Level 3] references: {refs}, scripts: {scripts}")


def demo_slash_command_matching() -> None:
    """斜杠命令匹配。"""
    match = skill_service.match_slash_command("/translate hello to 中文")
    print(f"[match] /translate: {match.name if match else None}")

    match2 = skill_service.match_slash_command("/unknown")
    print(f"[match] /unknown: {match2}")

    cmds = skill_service.get_slash_commands()
    print(f"[commands] 可用斜杠命令: {[c['command'] for c in cmds]}")


def demo_chat_with_skill() -> None:
    """端到端：激活技能 → 注入 LLM 上下文 → 获得回复。"""
    llm = _build_llm()

    # 激活翻译技能，获取渲染后的指令
    skill_prompt = skill_service.activate("summarize", arguments="Python is a versatile programming language")

    # 将技能指令注入为 SystemMessage
    messages = [
        SystemMessage(content=skill_prompt),
        HumanMessage(content="请执行上述技能指令。"),
    ]

    print("[chat] 发送带技能上下文的请求...")
    response: AIMessage = llm.invoke(messages)
    print(f"[chat] 模型回复:")
    print(f"  {response.content[:300]}...")


def demo_invalidate_and_reload() -> None:
    """清除缓存并重新扫描。"""
    skill_service.invalidate()
    skills = skill_service.discover()
    print(f"[reload] 重新扫描发现 {len(skills)} 个技能")


def demo_custom_loader() -> None:
    """自定义扫描路径。"""
    loader = SkillLoader(base_dirs=["skills"])
    custom_skills = loader.discover()
    print(f"[custom] 从 skills/ 目录发现 {len(custom_skills)} 个技能:")
    for s in custom_skills.values():
        print(f"  - {s.name} ({s.source_path})")


def _build_skill_routing_prompt() -> str:
    """构建技能路由系统提示词 — 将可用技能元数据注入 LLM 上下文。"""
    auto_skills = skill_service.list_auto_triggerable()
    if not auto_skills:
        return "你是一个有用的助手。"

    skill_lines = []
    for s in auto_skills:
        hint = f" 参数格式: {s.argument_hint}" if s.argument_hint else ""
        skill_lines.append(f"- /{s.name}: {s.description}{hint}")
    skill_list = "\n".join(skill_lines)

    return (
        "你是一个智能助手，可以使用以下技能来更好地帮助用户。\n"
        "可用技能:\n"
        f"{skill_list}\n\n"
        "请根据用户的消息判断是否需要使用某个技能。如果需要，请严格按以下 JSON 格式回复，"
        "不要输出任何其他内容:\n"
        '{"skill": "<技能名称，不带斜杠前缀>", "arguments": "<用户输入中与技能相关的参数>"}\n\n'
        "如果不需要使用任何技能，直接正常回复用户即可。"
    )


def _parse_skill_selection(response: str) -> dict | None:
    """从模型回复中提取技能选择结果。"""
    match = re.search(r'\{[^{}]*"skill"\s*:\s*"[^"]+"[^{}]*\}', response)
    if not match:
        return None
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return None


def demo_model_auto_skill() -> None:
    """模型自动选择技能：两轮调用实现技能自动匹配与执行。

    流程：
    1. 注入技能元数据到系统提示词（Level 1）
    2. 第一轮：模型分析用户意图 → 选择技能 + 提取参数
    3. 激活选中技能，渲染完整指令（Level 2）
    4. 第二轮：模型按技能指令生成最终回复
    """
    llm = _build_llm()
    routing_prompt = _build_skill_routing_prompt()

    # ── 测试场景：用户自然语言，模型自动匹配技能 ──
    test_messages = [
        "帮我把这段话翻译成法语：今天天气真好",
        "帮我总结一下这篇文章的核心观点：Python is a versatile programming language.",
        "今天星期几？",  # 无需技能
    ]

    for user_msg in test_messages:
        print(f"[auto-skill] 用户: {user_msg}")

        # 第一轮：模型选择技能
        messages = [
            SystemMessage(content=routing_prompt),
            HumanMessage(content=user_msg),
        ]
        response: AIMessage = llm.invoke(messages)
        selection = _parse_skill_selection(str(response.content))

        if selection:
            skill_name = selection["skill"].lstrip("/")
            arguments = selection.get("arguments", "")
            print(f"[auto-skill] 模型选择: {skill_name}, 参数: {arguments}")

            # 激活技能，渲染完整指令
            skill_prompt = skill_service.activate(skill_name, arguments=arguments)

            # 第二轮：注入技能指令，生成最终回复
            messages = [
                SystemMessage(content=skill_prompt),
                HumanMessage(content=arguments),
            ]
            final_response: AIMessage = llm.invoke(messages)
            print(f"[auto-skill] 技能回复: {final_response.content[:200]}...")
        else:
            print(f"[auto-skill] 无需技能，直接回复: {response.content[:200]}...")

        print()


def demo_error_handling() -> None:
    """错误处理。"""
    try:
        skill_service.activate("nonexistent")
    except SkillError as e:
        print(f"[error] 预期捕获: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("Skills 模块使用示例")
    print("=" * 60)

    demo_discover()
    print()

    demo_get_single()
    print()

    demo_activate()
    print()

    demo_progressive_disclosure()
    print()

    demo_slash_command_matching()
    print()

    demo_chat_with_skill()
    print()

    demo_model_auto_skill()
    print()

    demo_invalidate_and_reload()
    print()

    demo_custom_loader()
    print()

    demo_error_handling()

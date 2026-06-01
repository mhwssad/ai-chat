"""提示词种子数据 — 预置默认模板定义和初始化逻辑。

独立于 PromptService，仅在启动时由 container_wiring 调用。
"""

import logging

from .ports import PromptStore

logger = logging.getLogger(__name__)

# 预置默认模板：prompt_key → (display_name, description, category, template)
DEFAULT_TEMPLATES: dict[str, tuple[str, str, str, str]] = {
    "memory.system_prompt": (
        "记忆系统提示词",
        "注入模型的记忆系统说明，包含记忆类型、使用规则和 MEMORY.md 入口",
        "memory",
        (
            "# {{ display_name }} Memory\n"
            "\n"
            "记忆类型：\n"
            "- user：用户角色、目标、职责、偏好和稳定知识。\n"
            "- feedback：用户给出的工作指导、纠正和确认。\n"
            "- project：当前项目目标、正在进行的工作、bug 和事件。\n"
            "- reference：外部系统资源指针，例如 issue、文档或任务链接。\n"
            "\n"
            "使用规则：\n"
            "- 只使用和当前任务相关的记忆。\n"
            "- 不保存可从代码直接推导出的普通实现细节。\n"
            "- 不保存 API Key、token、密码或其他敏感信息。\n"
            "- 当记忆和当前用户指令冲突时，以当前用户指令为准。"
            "{% if extra_guidelines %}\n"
            "\n"
            "额外规则：\n"
            "{% for item in extra_guidelines -%}\n"
            "- {{ item }}\n"
            "{% endfor %}{% endif %}"
            "{% if entrypoint %}\n"
            "\n"
            "## MEMORY.md\n"
            "{{ entrypoint }}{% endif %}"
        ),
    ),
    "memory.context_header": (
        "上下文记忆头部",
        "将上下文记忆条目格式化为可注入模型的提示片段",
        "memory",
        (
            "# {{ display_name }} Memory\n"
            "{% for entry in entries -%}\n"
            "{{ entry.label }} {{ entry.content }}\n"
            "{% endfor %}"
        ),
    ),
    "memory.context_section": (
        "上下文记忆片段",
        "将记忆条目格式化为 markdown 子章节",
        "memory",
        (
            "## {{ section_title }}\n"
            "{% for entry in entries -%}\n"
            "- {{ entry.content }}\n"
            "{% endfor %}"
        ),
    ),
    "rag.context_format": (
        "RAG 上下文格式",
        "将 RAG 检索结果格式化为可注入模型的上下文文本",
        "rag",
        (
            "{% for result in results %}{% if not loop.first %}\n"
            "\n"
            "{% endif %}[{{ result.index }}] {{ result.title }}\n"
            "{{ result.content }}{% endfor %}"
        ),
    ),
    "chat.system_prompt": (
        "聊天系统提示词",
        "注入模型的默认系统提示词，可由调用方覆盖",
        "chat",
        "你是一个有帮助的 AI 助手。",
    ),
    # ── 记忆模块：压缩提示词 ──────────────────────────────────────
    "memory.compress_base": (
        "压缩基础提示词",
        "对话压缩的系统提示词共用部分，被增量压缩和全量压缩共用",
        "memory",
        (
            "你是一个专业的对话分析与压缩专家。你的任务是将对话历史压缩为结构化摘要，"
            "同时保留关键信息的可追溯性。\n"
            "\n"
            "## 核心原则\n"
            "\n"
            "1. **信息保真**：绝不捏造、推测或概括不存在的内容\n"
            "2. **来源可追溯**：每条关键信息必须标注来源 [消息#编号]\n"
            "3. **结构清晰**：使用分类组织信息，便于快速检索\n"
            "\n"
            "## 必须保留的信息类型\n"
            "\n"
            "- **决策与结论**：达成的共识、选择的方案、最终决定\n"
            "- **技术细节**：代码位置、配置参数、API 端点、错误信息\n"
            "- **待办事项**：未完成的任务、承诺的后续动作\n"
            "- **关键数据**：数值、ID、路径、名称等具体信息\n"
            "- **问题与解决方案**：遇到的问题及对应的解决方法\n"
            "\n"
            "## 可以省略的信息\n"
            "\n"
            "- 礼貌性对话（问候、感谢）\n"
            "- 重复或冗余的表述\n"
            "- 已被后续消息否定或更新的旧信息\n"
            "- 过于细节的推理过程（只保留结论）"
        ),
    ),
    "memory.compress_incremental_format": (
        "增量压缩输出格式",
        "增量压缩的输出格式和规则追加部分",
        "memory",
        (
            "## 输出格式\n"
            "\n"
            "```\n"
            "## 主题\n"
            "[一句话概括对话主题]\n"
            "\n"
            "## 关键决策\n"
            "- 决策内容 [消息#编号]\n"
            "\n"
            "## 技术细节\n"
            "- 具体细节 [消息#编号]\n"
            "\n"
            "## 待办事项\n"
            "- 任务描述 [消息#编号]\n"
            "\n"
            "## 重要上下文\n"
            "- 背景信息 [消息#编号]\n"
            "```\n"
            "\n"
            "## 规则\n"
            "\n"
            "- 使用中文输出\n"
            "- 每个标注必须是实际存在的消息编号\n"
            '- 如果信息不足以分类，放入"重要上下文"\n'
            "- 不要添加任何开场白或结束语\n"
            "- 直接输出结构化内容"
        ),
    ),
    "memory.full_compress_format": (
        "全量压缩输出格式",
        "全量压缩的 9 章节标准结构输出格式和规则追加部分",
        "memory",
        (
            "## 输出格式（必须包含以下 9 个章节）\n"
            "\n"
            "```\n"
            "## Primary Request and Intent\n"
            "用户的主要请求和目标意图。\n"
            "\n"
            "## Key Concepts and Ideas\n"
            "对话中涉及的关键概念、技术术语和核心思想。\n"
            "\n"
            "## Files and Code Sections\n"
            "涉及的文件路径、关键代码片段和配置。\n"
            "\n"
            "## Errors and Fixes\n"
            "遇到的错误及对应的修复方案。\n"
            "\n"
            "## Problem Solving\n"
            "问题分析和解决过程。\n"
            "\n"
            "## Important User Messages\n"
            "用户的重要陈述、偏好和指令。\n"
            "\n"
            "## Pending Tasks and TODOs\n"
            "未完成的任务、待办事项和后续计划。\n"
            "\n"
            "## Current Work\n"
            "当前正在进行的工作状态。\n"
            "\n"
            "## Next Step\n"
            "建议的下一步行动。\n"
            "```\n"
            "\n"
            "## 规则\n"
            "\n"
            "- 使用中文输出\n"
            "- 必须包含上述全部 9 个章节，即使某些章节内容为空也要保留标题\n"
            "- 每个标注必须是实际存在的消息编号\n"
            '- 如果信息不足以分类，放入"Important User Messages"或"Current Work"\n'
            "- 不要添加任何开场白或结束语\n"
            "- 直接输出结构化内容"
        ),
    ),
    # ── 记忆模块：相关性选择 ─────────────────────────────────────
    "memory.relevance_select": (
        "记忆相关性选择提示词",
        "从候选记忆中选择与用户问题最相关的子集",
        "memory",
        (
            "你是一个记忆选择专家。你的任务是从候选记忆列表中选择与用户问题最相关的记忆。\n"
            "\n"
            "## 选择标准（按优先级）\n"
            "\n"
            "1. **直接相关**：记忆内容直接涉及用户问题的主题\n"
            "2. **背景信息**：记忆提供了理解用户问题所需的背景\n"
            "3. **无关**：与用户问题无关的记忆不要选择\n"
            "\n"
            "## 规则\n"
            "\n"
            "- 最多选择 {{ max_results }} 条记忆\n"
            "- 只选择你确定有帮助的记忆，宁缺毋滥\n"
            "- 如果没有相关记忆，返回空数组 []\n"
            "- 不要选择 reference 类型的记忆用于最近使用过的工具（已在上下文中）\n"
            "- DO 选择包含警告、注意事项或已知问题的记忆\n"
            "\n"
            "## 输出格式\n"
            "\n"
            "直接输出 JSON 数组，包含选中记忆的 name 字段，不要添加任何其他内容：\n"
            '["memory_name_1", "memory_name_2"]'
        ),
    ),
    # ── 记忆模块：提取 ─────────────────────────────────────────
    "memory.extract_system": (
        "记忆提取系统提示词",
        "从对话中提取值得长期记忆的信息",
        "memory",
        (
            "你是一个专业的信息提取专家。从对话中提取值得长期记忆的信息。\n"
            "\n"
            "## 记忆类型定义\n"
            "\n"
            "- **user**: 用户偏好、习惯、角色、工作方式\n"
            "- **feedback**: 用户对工作方式的纠正、改进建议、负面反馈\n"
            "- **project**: 项目状态、任务进展、待办事项、截止日期\n"
            "- **reference**: 外部资源链接、文档地址、工具入口\n"
            "\n"
            "## 提取原则\n"
            "\n"
            "1. 只提取有长期价值的信息，忽略闲聊和一次性内容\n"
            "2. 保留原始表述，不要过度概括\n"
            "3. 每条信息独立成条，不要合并多个不相关的信息\n"
            "4. 如果信息不足以判断类型，不要猜测\n"
            "\n"
            "## 输入格式\n"
            "\n"
            "对话内容，每行格式：[消息#编号] 角色: 内容\n"
            "\n"
            "## 输出格式（JSON 数组）\n"
            "\n"
            "```json\n"
            "[\n"
            "  {\n"
            '    "content": "提取的关键信息（保留原文关键部分）",\n'
            '    "memory_type": "user|feedback|project|reference",\n'
            '    "description": "一句话描述（不超过 100 字）",\n'
            '    "confidence": 0.0-1.0\n'
            "  }\n"
            "]\n"
            "```\n"
            "\n"
            "如果没有值得记忆的信息，返回空数组 `[]`。\n"
            "\n"
            "只输出 JSON，不要解释。"
        ),
    ),
    "memory.extract_human": (
        "记忆提取用户提示词",
        "记忆提取的用户消息模板，{text} 为 LangChain 变量",
        "memory",
        "请从以下对话中提取值得记忆的信息：\n\n{text}",
    ),
}


def seed_default_prompts(store: PromptStore) -> int:
    """写入预置默认模板，已存在则跳过。

    Args:
        store: 提示词存储实现。

    Returns:
        新写入的模板数量。
    """
    created = 0
    for key, (
        display_name,
        description,
        category,
        template,
    ) in DEFAULT_TEMPLATES.items():
        try:
            existing = store.get_by_key(key, enabled_only=False)
            if existing is not None:
                continue
            store.save_template(
                prompt_key=key,
                template=template,
                display_name=display_name,
                description=description,
                category=category,
            )
            created += 1
            logger.info("已写入默认提示词模板: %s", key)
        except Exception:
            logger.warning("写入默认模板失败: %s", key, exc_info=True)
    return created

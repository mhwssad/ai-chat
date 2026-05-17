"""内置提示词种子数据 — 首次启动时自动导入数据库。

每个条目是一个 PromptCreateRequest 的参数字典。
所有内置提示词标记 is_builtin=True，不可通过管理接口删除。
"""

BUILTIN_PROMPTS: list[dict] = [
    # ── Chains ──────────────────────────────────────
    {
        "name": "chain.chat",
        "source_type": "file",
        "file_path": "chain_chat.jinja2",
        "content": (
            "== system ==\n你是一个有帮助的 AI 助手。请用中文回答用户的问题。\n"
            "== human ==\n{{ message }}"
        ),
        "description": "通用对话提示词",
        "tags": "chain,chat",
    },
    {
        "name": "chain.summarize",
        "source_type": "file",
        "file_path": "chain_summarize.jinja2",
        "content": (
            "== system ==\n你是一个专业的文本摘要助手。请用{{ language }}输出摘要。\n"
            "== human ==\n{{ instruction }}\n\n{{ text }}"
        ),
        "description": "文本摘要提示词",
        "tags": "chain,summarize",
    },
    {
        "name": "chain.translate",
        "source_type": "file",
        "file_path": "chain_translate.jinja2",
        "content": (
            "== system ==\n你是一个专业翻译。请将以下文本翻译成{{ target }}，只输出译文，不要解释。\n"
            "== human ==\n{{ text }}"
        ),
        "description": "翻译提示词",
        "tags": "chain,translate",
    },
    {
        "name": "chain.extraction",
        "source_type": "file",
        "file_path": "chain_extraction.jinja2",
        "content": (
            "== system ==\n你是一个信息抽取助手。从用户提供的文本中提取指定字段。"
            "需要提取的字段：{{ fields_desc }}\n"
            "严格以 JSON 格式输出，字段名即上述名称。如果某字段在文本中找不到，值设为 null。"
            "只输出 JSON，不要输出其他内容。\n"
            "== human ==\n{{ text }}"
        ),
        "description": "信息抽取提示词",
        "tags": "chain,extraction",
    },
    {
        "name": "chain.refine",
        "source_type": "file",
        "file_path": "chain_refine.jinja2",
        "content": (
            "== system ==\n你是一个专业的文本编辑。请用{{ language }}输出优化后的文本。"
            "根据用户的指令对提供的文本进行优化，只输出优化后的完整文本，不要解释。\n"
            "== human ==\n优化指令：{{ instruction }}\n\n原始文本：\n{{ text }}"
        ),
        "description": "文本优化提示词",
        "tags": "chain,refine",
    },
    # ── Agent / Graph ───────────────────────────────
    {
        "name": "agent.react.system",
        "source_type": "inline",
        "content": "== system ==\n你是一个有帮助的 AI 助手。请用中文回答用户的问题。你可以使用工具来完成任务。",
        "description": "ReAct Agent 系统提示词",
        "tags": "agent,react",
    },
    {
        "name": "graph.chat.system",
        "source_type": "inline",
        "content": "== system ==\n你是一个有帮助的 AI 助手。请用中文回答用户的问题。",
        "description": "Graph Chat 系统提示词",
        "tags": "graph,chat",
    },
    {
        "name": "graph.intent.chat_or_rag",
        "source_type": "file",
        "file_path": "graph_intent_chat_or_rag.jinja2",
        "content": (
            "== system ==\n你是一个意图分类器。根据用户消息判断意图，只回答一个词：\n\n"
            '- "rag"：用户在询问事实性问题，需要检索知识库来回答\n'
            '- "chat"：普通聊天、问候、创意写作、关于你自身的问题\n\n'
            '只回答 "rag" 或 "chat"，不要输出其他内容。\n'
            "== human ==\n{{ question }}"
        ),
        "description": "意图分类（chat/rag）",
        "tags": "graph,intent",
    },
    {
        "name": "graph.intent.react_or_rag",
        "source_type": "file",
        "file_path": "graph_intent_react_or_rag.jinja2",
        "content": (
            "== system ==\n你是一个意图分类器。根据用户消息判断意图，只回答一个词：\n\n"
            '- "rag"：用户在询问事实性问题，需要检索知识库来回答\n'
            '- "react"：普通聊天、问候、创意写作、关于你自身的问题、需要使用工具完成操作\n\n'
            '只回答 "rag" 或 "react"，不要输出其他内容。\n'
            "== human ==\n{{ question }}"
        ),
        "description": "意图分类（react/rag）",
        "tags": "graph,intent",
    },
    {
        "name": "graph.rag.answer",
        "source_type": "file",
        "file_path": "graph_rag_answer.jinja2",
        "content": (
            "== system ==\n你是一个有帮助的 AI 助手。请根据提供的参考资料回答用户问题。"
            "如果资料中没有相关信息，请说明。请用中文回答。\n"
            "== human ==\n参考资料：\n{{ context }}\n\n用户问题：{{ question }}"
        ),
        "description": "RAG 回答提示词",
        "tags": "graph,rag",
    },
]

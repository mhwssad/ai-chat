"""内置 prompts — 为 chains 与 graphs 提供统一提示词定义。"""

from langchain_core.prompts import ChatPromptTemplate

from .registry import register_prompt


def _messages_template(messages: list[tuple[str, str]]) -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages(messages, template_format="jinja2")


@register_prompt("chain.chat")
def _chain_chat_prompt() -> ChatPromptTemplate:
    return _messages_template([
        ("system", "你是一个有帮助的 AI 助手。请用中文回答用户的问题。"),
        ("human", "{{ message }}"),
    ])


@register_prompt("chain.summarize")
def _chain_summarize_prompt() -> ChatPromptTemplate:
    return _messages_template([
        ("system", "你是一个专业的文本摘要助手。请用{{ language }}输出摘要。"),
        ("human", "{{ instruction }}\n\n{{ text }}"),
    ])


@register_prompt("chain.translate")
def _chain_translate_prompt() -> ChatPromptTemplate:
    return _messages_template([
        ("system", "你是一个专业翻译。请将以下文本翻译成{{ target }}，只输出译文，不要解释。"),
        ("human", "{{ text }}"),
    ])


@register_prompt("chain.extraction")
def _chain_extraction_prompt() -> ChatPromptTemplate:
    return _messages_template([
        (
            "system",
            "你是一个信息抽取助手。从用户提供的文本中提取指定字段。"
            "需要提取的字段：{{ fields_desc }}\n"
            "严格以 JSON 格式输出，字段名即上述名称。如果某字段在文本中找不到，值设为 null。"
            "只输出 JSON，不要输出其他内容。",
        ),
        ("human", "{{ text }}"),
    ])


@register_prompt("chain.refine")
def _chain_refine_prompt() -> ChatPromptTemplate:
    return _messages_template([
        (
            "system",
            "你是一个专业的文本编辑。请用{{ language }}输出优化后的文本。"
            "根据用户的指令对提供的文本进行优化，只输出优化后的完整文本，不要解释。",
        ),
        ("human", "优化指令：{{ instruction }}\n\n原始文本：\n{{ text }}"),
    ])


@register_prompt("agent.react.system")
def _agent_react_system_prompt() -> ChatPromptTemplate:
    return _messages_template([
        ("system", "你是一个有帮助的 AI 助手。请用中文回答用户的问题。你可以使用工具来完成任务。"),
    ])


@register_prompt("graph.chat.system")
def _graph_chat_system_prompt() -> ChatPromptTemplate:
    return _messages_template([
        ("system", "你是一个有帮助的 AI 助手。请用中文回答用户的问题。"),
    ])


@register_prompt("graph.intent.chat_or_rag")
def _graph_intent_chat_or_rag_prompt() -> ChatPromptTemplate:
    return _messages_template([
        (
            "system",
            "你是一个意图分类器。根据用户消息判断意图，只回答一个词：\n\n"
            '- "rag"：用户在询问事实性问题，需要检索知识库来回答\n'
            '- "chat"：普通聊天、问候、创意写作、关于你自身的问题\n\n'
            '只回答 "rag" 或 "chat"，不要输出其他内容。',
        ),
        ("human", "{{ question }}"),
    ])


@register_prompt("graph.intent.react_or_rag")
def _graph_intent_react_or_rag_prompt() -> ChatPromptTemplate:
    return _messages_template([
        (
            "system",
            "你是一个意图分类器。根据用户消息判断意图，只回答一个词：\n\n"
            '- "rag"：用户在询问事实性问题，需要检索知识库来回答\n'
            '- "react"：普通聊天、问候、创意写作、关于你自身的问题、需要使用工具完成操作\n\n'
            '只回答 "rag" 或 "react"，不要输出其他内容。',
        ),
        ("human", "{{ question }}"),
    ])


@register_prompt("graph.rag.answer")
def _graph_rag_answer_prompt() -> ChatPromptTemplate:
    return _messages_template([
        (
            "system",
            "你是一个有帮助的 AI 助手。请根据提供的参考资料回答用户问题。"
            "如果资料中没有相关信息，请说明。请用中文回答。",
        ),
        ("human", "参考资料：\n{{ context }}\n\n用户问题：{{ question }}"),
    ])

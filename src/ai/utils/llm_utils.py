"""LLM 链构建工具。

提供 LCEL 链构建函数：
- build_llm_chain(): 统一构建 ChatPromptTemplate | llm | StrOutputParser 链
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel
    from langchain_core.runnables import RunnableSequence


def build_llm_chain(
    llm: BaseChatModel,
    system_prompt: str,
    human_template: str,
) -> RunnableSequence:
    """构建 ChatPromptTemplate | llm | StrOutputParser 链。

    Args:
        llm: LangChain 聊天模型。
        system_prompt: 系统提示词。
        human_template: 人类消息模板，使用 {variable} 格式。

    Returns:
        可调用的 LCEL 链。
    """
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.prompts import ChatPromptTemplate

    return (
        ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                ("human", human_template),
            ]
        )
        | llm
        | StrOutputParser()
    )

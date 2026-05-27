"""LLM 构建工具 — 消除重复的 LLM 实例和链构建。

提供两个公共函数：
- get_chat_llm(): 获取缓存的聊天 LLM 实例
- build_llm_chain(): 统一构建 ChatPromptTemplate | llm | StrOutputParser 链
"""

import logging

from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableSequence

logger = logging.getLogger(__name__)

_cached_llm: BaseChatModel | None = None


def get_chat_llm() -> BaseChatModel:
    """获取缓存的聊天 LLM 实例。

    首次调用时从 model_registry 构建，后续返回缓存。
    chat_model_config 在运行期间不变，缓存安全。
    """
    global _cached_llm
    if _cached_llm is None:
        from src.ai.core.models.builders.registry import model_registry
        from src.ai.config.model_settings import chat_model_config

        builder = model_registry.get_builder("chat", chat_model_config.backend)
        _cached_llm = builder.build(chat_model_config)
        logger.info("LLM 实例已构建并缓存: %s", chat_model_config.backend)
    return _cached_llm


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


def reset_chat_llm() -> None:
    """重置 LLM 缓存（测试用）。"""
    global _cached_llm
    _cached_llm = None

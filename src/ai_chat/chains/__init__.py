"""Chain 模块 — 调用链工厂 + 管理入口。"""

from .chat_chain import (
    ChatChain,
    SummarizeChain,
    TranslateChain,
    ExtractionChain,
    RefineChain,
)
from .factory import chain_factory
from .menu import menu_chains

# 注册所有 chain
chain_factory.register("chat", ChatChain)
chain_factory.register("summarize", SummarizeChain)
chain_factory.register("translate", TranslateChain)
chain_factory.register("extraction", ExtractionChain)
chain_factory.register("refine", RefineChain)

__all__ = [
    "ChatChain",
    "SummarizeChain",
    "TranslateChain",
    "ExtractionChain",
    "RefineChain",
    "chain_factory",
    "menu_chains",
]

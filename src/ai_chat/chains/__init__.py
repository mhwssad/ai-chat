"""Chain 模块 — 调用链工厂 + 管理入口。"""

from .base import ChainConfig, ChainError, PromptContext, _BasePromptChain
from .chat_chain import (
    ChatChain,
    SummarizeChain,
    TranslateChain,
    ExtractionChain,
    RefineChain,
)
from .rag_chain import RAGChain
from .summary_chain import ConversationSummaryChain
from .code_review_chain import CodeReviewChain
from .composition import SequentialChain, RouterChain
from .batch_chain import BatchChain, BatchResult
from .observability import ChainMetrics, MetricsCollector, MetricsSummary, metrics_collector
from .factory import chain_factory, register_chain
from .models import ChainCreateRequest, ChainRecord, ChainTable
from .store import ChainStore
from .manager import ChainManager, chain_manager
from .menu import menu_chains

# 注册所有 chain
chain_factory.register("chat", ChatChain)
chain_factory.register("summarize", SummarizeChain)
chain_factory.register("translate", TranslateChain)
chain_factory.register("extraction", ExtractionChain)
chain_factory.register("refine", RefineChain)
chain_factory.register("rag", RAGChain)
chain_factory.register("code_review", CodeReviewChain)

__all__ = [
    # 基类与配置
    "ChainConfig",
    "ChainError",
    "PromptContext",
    "_BasePromptChain",
    # 调用链
    "ChatChain",
    "SummarizeChain",
    "TranslateChain",
    "ExtractionChain",
    "RefineChain",
    "RAGChain",
    "ConversationSummaryChain",
    "CodeReviewChain",
    # 组合
    "SequentialChain",
    "RouterChain",
    "BatchChain",
    "BatchResult",
    # 可观测性
    "ChainMetrics",
    "MetricsCollector",
    "MetricsSummary",
    "metrics_collector",
    # 工厂
    "chain_factory",
    "register_chain",
    # 持久化
    "ChainTable",
    "ChainRecord",
    "ChainCreateRequest",
    "ChainStore",
    "ChainManager",
    "chain_manager",
    # 菜单
    "menu_chains",
]

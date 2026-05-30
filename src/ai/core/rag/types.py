"""RAG 模块类型定义。"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RAGSearchConfig:
    """RAG 检索配置。"""

    enabled: bool = True
    top_k: int = 5
    optimize_query: bool = True
    merge_strategy: str = "deduplicate"


@dataclass
class RAGSearchResult:
    """RAG 双路检索合并结果。"""

    content: str = ""
    raw_results: list = field(default_factory=list)
    original_query: str = ""
    optimized_query: str = ""

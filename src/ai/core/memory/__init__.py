"""统一记忆与上下文管理模块。

集成长期记忆（文件系统）、对话历史（LangChain SQLChatMessageHistory）
和上下文构建（策略驱动）。
"""

# 记忆异常
from src.ai.exception.memory_exception import (
    MemoryError,
    MemoryPathError,
    MemoryScanError,
)

# 长期记忆（文件系统）
from src.ai.core.memory.extractor import MemoryExtractor
from src.ai.core.memory.frontmatter import parse_frontmatter, parse_memory_file
from src.ai.core.memory.llm_utils import build_llm_chain, get_chat_llm
from src.ai.core.memory.paths import (
    MemoryPathResolver,
    sanitize_path_name,
    validate_memory_path,
)
from src.ai.core.memory.prompt import MemoryPromptBuilder
from src.ai.core.memory.scanner import MemoryScanner
from src.ai.core.memory.store import MemoryStore

# 文件历史存储
from src.ai.core.memory.history_store import FileHistoryStore

# 类型
from src.ai.core.memory.types import (
    MEMORY_TYPES,
    CompressedSummary,
    ContextBuildRequest,
    ContextBuildResult,
    ContextSourceBudget,
    ContextSourcePriority,
    MemoryEntry,
    MemorySearchResult,
    MemoryStrategyType,
    MemoryWriteRequest,
    RAGSearchConfig,
)

# 服务
from src.ai.core.memory.service import MemoryService, memory_service

# 对话历史
from src.ai.core.memory.history import ChatHistoryManager, get_chat_history_manager

# RAG 查询优化器
from src.ai.core.memory.rag_encoder import RAGQueryEncoder

# 策略
from src.ai.core.memory.strategies import create_memory_strategy
from src.ai.core.memory.strategies.base import BaseMemoryStrategy
from src.ai.core.memory.strategies.compression import CompressionStrategy

# 上下文构建
from src.ai.core.memory.context import ContextBuilder

__all__ = [
    # 类型
    "MEMORY_TYPES",
    "CompressedSummary",
    "ContextBuildRequest",
    "ContextBuildResult",
    "ContextSourceBudget",
    "ContextSourcePriority",
    "MemoryEntry",
    "MemorySearchResult",
    "MemoryStrategyType",
    "MemoryWriteRequest",
    "RAGSearchConfig",
    # 长期记忆
    "MemoryExtractor",
    "MemoryPathResolver",
    "MemoryPromptBuilder",
    "MemoryScanner",
    "MemoryStore",
    "memory_service",
    "MemoryService",
    "parse_frontmatter",
    "parse_memory_file",
    "sanitize_path_name",
    "validate_memory_path",
    # LLM 工具
    "build_llm_chain",
    "get_chat_llm",
    # 文件历史存储
    "FileHistoryStore",
    # 对话历史
    "ChatHistoryManager",
    "get_chat_history_manager",
    # RAG 查询优化器
    "RAGQueryEncoder",
    # 策略
    "BaseMemoryStrategy",
    "CompressionStrategy",
    "create_memory_strategy",
    # 上下文构建
    "ContextBuilder",
    # 异常
    "MemoryError",
    "MemoryPathError",
    "MemoryScanError",
]

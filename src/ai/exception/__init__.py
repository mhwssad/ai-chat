"""项目统一异常。"""

from src.ai.exception.base_exception import BaseExceptions
from src.ai.exception.http_exception import ConverterError, HttpError
from src.ai.exception.loader_exception import (
    LoadPermissionError,
    LoaderError,
    UnsupportedFileTypeError,
)
from src.ai.exception.llm_exception import (
    LLMCircuitOpenError,
    LLMException,
    LLMRetryExhaustedError,
    ModelNotSupportedException,
)
from src.ai.exception.mcp_config_exception import MCPConfigError
from src.ai.exception.mcp_exception import (
    MCPConnectionError,
    MCPError,
    MCPProtocolError,
    MCPToolCallError,
    MCPToolDiscoveryError,
)
from src.ai.exception.media_exception import (
    ImageGenerationException,
    MediaGenerationException,
    MediaNotFoundError,
    TTSException,
)
from src.ai.exception.memory_exception import (
    MemoryException,
    MemoryNotFoundError,
    MemoryPathError,
    MemoryScanError,
)
from src.ai.exception.prompt_exception import (
    PromptError,
    PromptNotFoundError,
    PromptRenderError,
)
from src.ai.exception.rag_exception import RagEmbeddingError, RagError, SplitterError
from src.ai.exception.scheduler_exception import SchedulerError, SchedulerNotFoundError
from src.ai.exception.skill_exception import (
    SkillError,
    SkillLoadError,
    SkillNotFoundError,
    SkillRenderError,
)
from src.ai.exception.pool_exception import (
    ThreadPoolError,
    ThreadPoolShutdownError,
    ThreadPoolTimeoutError,
)
from src.ai.exception.tool_exception import (
    ToolDisabledError,
    ToolError,
    ToolExecutionError,
    ToolNotFoundError,
    ToolPermissionError,
)

__all__ = [
    # 基础
    "BaseExceptions",
    # LLM
    "LLMCircuitOpenError",
    "LLMException",
    "LLMRetryExhaustedError",
    "ModelNotSupportedException",
    # Tool
    "ToolDisabledError",
    "ToolError",
    "ToolExecutionError",
    "ToolNotFoundError",
    "ToolPermissionError",
    # MCP
    "MCPConfigError",
    "MCPConnectionError",
    "MCPError",
    "MCPProtocolError",
    "MCPToolCallError",
    "MCPToolDiscoveryError",
    # Media
    "ImageGenerationException",
    "MediaGenerationException",
    "MediaNotFoundError",
    "TTSException",
    # Loader
    "LoadPermissionError",
    "LoaderError",
    "UnsupportedFileTypeError",
    # Prompt
    "PromptError",
    "PromptNotFoundError",
    "PromptRenderError",
    # Skill
    "SkillError",
    "SkillLoadError",
    "SkillNotFoundError",
    "SkillRenderError",
    # Memory
    "MemoryException",
    "MemoryNotFoundError",
    "MemoryPathError",
    "MemoryScanError",
    # RAG
    "RagEmbeddingError",
    "RagError",
    "SplitterError",
    # Scheduler
    "SchedulerError",
    "SchedulerNotFoundError",
    # ThreadPool
    "ThreadPoolError",
    "ThreadPoolShutdownError",
    "ThreadPoolTimeoutError",
    # HTTP
    "ConverterError",
    "HttpError",
]

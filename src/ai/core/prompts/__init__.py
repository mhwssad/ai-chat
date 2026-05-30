"""提示词核心能力。"""

from src.ai.exception.prompt_exception import (
    PromptError,
    PromptNotFoundError,
    PromptRenderError,
)
from src.ai.core.prompts.renderer import PromptRenderer
from src.ai.core.prompts.service import PromptService
from src.ai.core.prompts.types import PromptRenderRequest, PromptRenderResult


# 惰性导入：DI 容器单例
def __getattr__(name: str):
    if name == "prompt_service":
        from src.ai.core.container import container

        return container.prompt_container.prompt_service()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "PromptError",
    "PromptNotFoundError",
    "PromptRenderError",
    "PromptRenderRequest",
    "PromptRenderResult",
    "PromptRenderer",
    "PromptService",
    "prompt_service",
]

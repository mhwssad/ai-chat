"""提示词领域类型。"""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class PromptData:
    """提示词模板数据，替代直接依赖 ORM PromptTemplate。"""

    prompt_key: str
    template: str
    version: int = 1
    display_name: str | None = None
    description: str | None = None
    category: str = "general"
    enabled: bool = True
    extra: str = "{}"


@dataclass(frozen=True)
class PromptVersionData:
    """提示词版本历史数据，替代直接依赖 ORM PromptVersion。"""

    id: int
    prompt_id: int
    version: int
    template: str
    change_note: str | None = None


@dataclass(frozen=True)
class PromptRenderRequest:
    """提示词渲染请求。"""

    prompt_key: str
    variables: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PromptRenderResult:
    """提示词渲染结果。"""

    prompt_key: str
    content: str
    version: int
    metadata: dict[str, Any] = field(default_factory=dict)

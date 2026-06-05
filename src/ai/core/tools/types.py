"""工具层通用类型。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, AsyncIterator, Literal, Protocol

if TYPE_CHECKING:
    from langchain_core.tools import BaseTool

    from src.ai.core.tools.registry import ToolRegistry

ToolSourceType = Literal["builtin", "mcp", "skill"]


@dataclass(slots=True)
class ToolMeta:
    """统一工具元数据。"""

    source_type: ToolSourceType = "builtin"
    source_id: str | None = None
    display_name: str | None = None
    permissions: list[str] = field(default_factory=list)
    output_description: str | None = None
    essential: bool = False
    enabled: bool = True


@dataclass(frozen=True)
class ToolDescriptor:
    """统一工具描述对象。"""

    name: str
    display_name: str
    description: str
    source_type: ToolSourceType
    source_id: str | None = None
    permissions: list[str] = field(default_factory=list)
    output_description: str | None = None
    essential: bool = False
    enabled: bool = True

    @classmethod
    def from_tool(cls, tool: "BaseTool", meta: ToolMeta) -> "ToolDescriptor":
        """从工具实例和元数据构建统一描述对象。"""
        return cls(
            name=tool.name,
            display_name=meta.display_name or tool.name,
            description=getattr(tool, "description", "") or "",
            source_type=meta.source_type,
            source_id=meta.source_id,
            permissions=list(meta.permissions),
            output_description=meta.output_description,
            essential=meta.essential,
            enabled=meta.enabled,
        )


@dataclass(frozen=True)
class ToolExecutionDiagnostic:
    """工具执行诊断结果。"""

    tool_name: str
    source_type: ToolSourceType
    source_id: str | None = None
    status: str = "success"
    duration_ms: int = 0
    permission_decision: str | None = None
    input_summary: str | None = None
    output_summary: str | None = None
    error_type: str | None = None
    error_message: str | None = None
    result: Any | None = None


class ToolPlugin(ABC):
    """工具插件接口。

    实现此接口的模块可以向 ToolRegistry 注册自己的工具。
    ToolManager 在加载内置工具时会调用所有已注册插件的 register_tools 方法。
    """

    @abstractmethod
    def register_tools(self, registry: ToolRegistry) -> None:
        """将插件的工具注册到工具注册表。

        Args:
            registry: 工具注册表实例。
        """


@dataclass
class ToolProgress:
    """工具执行进度事件。

    用于流式返回工具执行的中间状态。

    Attributes:
        tool_name: 工具名称。
        stage: 执行阶段（如 "loading", "processing", "generating"）。
        message: 进度描述消息。
        progress: 进度百分比（0.0 ~ 1.0），None 表示不确定。
        partial_result: 部分结果（如流式输出的文本片段）。
    """

    tool_name: str
    stage: str = ""
    message: str = ""
    progress: float | None = None
    partial_result: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class StreamableTool(Protocol):
    """支持流式输出的工具协议。

    实现此协议的工具可以通过 ToolManager.execute_stream() 流式返回进度。
    """

    async def ainvoke_stream(
        self, arguments: dict[str, Any], **kwargs: Any
    ) -> AsyncIterator[ToolProgress]:
        """流式执行工具。

        Args:
            arguments: 工具参数。

        Yields:
            ToolProgress 进度事件。
        """


@dataclass
class MultimodalToolResult:
    """多模态工具结果。

    支持返回文本 + 图像等多模态内容。

    Attributes:
        text: 文本结果。
        images: 图像数据列表（base64 编码或 URL）。
        mime_types: 对应图像的 MIME 类型。
    """

    text: str = ""
    images: list[str] = field(default_factory=list)
    mime_types: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_langchain_content(self) -> list[dict[str, Any]]:
        """转换为 LangChain 多模态消息格式。"""
        content: list[dict[str, Any]] = []
        if self.text:
            content.append({"type": "text", "text": self.text})
        for img, mime in zip(self.images, self.mime_types):
            if img.startswith(("http://", "https://")):
                content.append({"type": "image_url", "image_url": {"url": img}})
            else:
                content.append(
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": mime,
                            "data": img,
                        },
                    }
                )
        return content

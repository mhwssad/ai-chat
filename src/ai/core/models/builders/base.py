"""策略接口 + 泛型抽象工厂。

定义模型构建的两层抽象：
- **策略接口**：``ChatModelBuilder`` / ``EmbeddingModelBuilder``
- **泛型抽象工厂**：``ModelFactory[BuilderT]`` 统一注册、查询、创建
"""

from abc import ABC, abstractmethod
from typing import Any, Generic, List, Optional, TypeVar, Union

from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel

from src.ai.config.model_settings import ChatModelConfig, EmbeddingModelConfig
from src.ai.exception.llm_exception import LLMException


# ── 策略接口 ───────────────────────────────────────────

ConfigT = TypeVar("ConfigT")
ReturnT = TypeVar("ReturnT")


class ModelBuilder(ABC, Generic[ConfigT, ReturnT]):
    """模型构建策略基类。"""

    backend: List[str]

    def is_backend(self, backend: str) -> bool:
        """判断后端是否匹配。"""
        return backend in self.backend

    @abstractmethod
    def build(self, config: ConfigT, **kwargs: Any) -> ReturnT:
        """构建模型实例。"""


class ChatModelBuilder(ModelBuilder[ChatModelConfig, BaseChatModel]):
    """Chat 模型构建策略接口。"""

    @abstractmethod
    def build(
        self,
        config: ChatModelConfig,
        *,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        streaming: bool = False,
    ) -> BaseChatModel:
        """构建 Chat 模型实例。"""


class EmbeddingModelBuilder(ModelBuilder[EmbeddingModelConfig, Embeddings]):
    """Embedding 模型构建策略接口。"""

    @abstractmethod
    def build(self, config: EmbeddingModelConfig) -> Embeddings:
        """构建 Embedding 模型实例。"""


# ── 泛型抽象工厂 ───────────────────────────────────────

ModelBuilderT = TypeVar("ModelBuilderT", bound=ModelBuilder[Any, Any])


class ModelFactory(ABC, Generic[ModelBuilderT]):
    """泛型抽象工厂 — 每个后端聚合各类型模型的构建策略。

    子类只需实现 ``create_builder``，即被 ``ModelFactoryRegistry`` 统一调度。
    新增模型类型：新建 Builder ABC → 新建 Factory 子类 → 注册到 registry，
    无需修改任何已有代码（开闭原则）。
    """

    def __init__(self) -> None:
        self._registry: dict[str, ModelBuilderT] = {}

    # ── 注册（对扩展开放） ──

    def register(self, builder: Union[ModelBuilderT, type[ModelBuilderT], None] = None):
        """注册构建器 — 可作装饰器（不传参）或直接调用。"""
        if builder is None:
            def decorator(cls_or_inst: Union[ModelBuilderT, type[ModelBuilderT]]):
                inst = cls_or_inst() if isinstance(cls_or_inst, type) else cls_or_inst
                self._do_register(inst)
                return cls_or_inst
            return decorator
        inst = builder() if isinstance(builder, type) else builder
        self._do_register(inst)
        return inst

    def _do_register(self, builder: ModelBuilderT) -> None:
        for backend in builder.backend:
            self._registry[backend] = builder

    def register_all(self, builders: list[Union[ModelBuilderT, type[ModelBuilderT]]]) -> None:
        """批量注册构建器。"""
        for b in builders:
            self.register(b)

    # ── 创建（对修改关闭 — 统一入口） ──

    @abstractmethod
    def create_builder(self, backend: str) -> ModelBuilderT:
        """根据后端名获取已注册的构建器。"""

    # ── 查询 ──

    def _find_builder(self, backend: str) -> Optional[ModelBuilderT]:
        """通过 is_backend 查找匹配的构建器。"""
        for builder in set(self._registry.values()):
            if builder.is_backend(backend):
                return builder
        return None

    def list_backends(self) -> list[str]:
        """返回所有已注册后端名。"""
        return list(self._registry.keys())

    def is_registered(self, backend: str) -> bool:
        """检查后端是否已注册。"""
        return self._find_builder(backend) is not None

    def get(self, backend: str) -> Optional[ModelBuilderT]:
        """安全获取构建器，未注册返回 None。"""
        return self._find_builder(backend)

    def _resolve(self, backend: str, type_label: str) -> ModelBuilderT:
        """通用解析逻辑，子类 create_builder 可直接委托。"""
        builder = self._find_builder(backend)
        if builder is None:
            raise LLMException(f"未注册的 {type_label} 后端: {backend!r}，可用: {self.list_backends()}")
        return builder

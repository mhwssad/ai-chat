"""models.builders 模块使用示例。

演示工厂模式的三种场景：
1. 使用内置构建器创建模型
2. 扩展新后端（装饰器注册）
3. 扩展新模型类型（工厂的工厂）

运行: PYTHONPATH=. uv run python docs/examples/builder_usage.py
"""

import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


# ── 1. 使用内置构建器 ────────────────────────────────────


def demo_builtin_builders():
    """使用已注册的内置构建器。"""
    from src.ai.core.models import model_registry, ChatModelConfig, EmbeddingModelConfig

    print("=== 1. 内置构建器 ===\n")

    # 查看已注册的模型类型
    print(f"  模型类型: {model_registry.list_model_types()}")

    # 查看 Chat 工厂已注册的后端
    chat_backends = model_registry.chat.list_backends()
    print(f"  Chat 后端: {chat_backends}")

    # 查看 Embedding 工厂已注册的后端
    emb_backends = model_registry.embedding.list_backends()
    print(f"  Embedding 后端: {emb_backends}")

    # 检查后端是否已注册
    print(f"  chat/openai 已注册? {model_registry.chat.is_registered('openai')}")
    print(f"  chat/azure 已注册? {model_registry.chat.is_registered('azure')}")

    # 获取构建器（不实际调用 API）
    builder = model_registry.get_builder("chat", "openai")
    print(f"  获取到构建器: {type(builder).__name__}")

    # 构建模型（需要有效的 API key）
    # config = ChatModelConfig(model_key="gpt-4o", api_key="sk-xxx")
    # llm = builder.build(config, temperature=0.7)

    print()


# ── 2. 扩展新后端（装饰器注册） ──────────────────────────


def demo_extend_backend():
    """通过装饰器注册自定义后端。"""
    from src.ai.core.models import (
        ChatModelBuilder,
        ChatModelFactory,
        ChatModelConfig,
        chat_model_factory,
    )
    from langchain_core.language_models import BaseChatModel

    print("=== 2. 扩展新后端 ===\n")

    # 方式一：装饰器注册
    @chat_model_factory.register
    class DashScopeBuilder(ChatModelBuilder):
        """阿里云 DashScope 后端。"""

        backend = ["dashscope"]

        def build(self, config: ChatModelConfig, **kwargs) -> BaseChatModel:
            # 实际实现会调用 DashScope SDK
            print(f"    [DashScope] 构建模型: {config.model_key}")
            return None  # 示例用

    print(f"  装饰器注册后 Chat 后端: {chat_model_factory.list_backends()}")
    print(f"  dashscope 已注册? {chat_model_factory.is_registered('dashscope')}")

    # 方式二：实例注册
    class CohereBuilder(ChatModelBuilder):
        backend = ["cohere"]

        def build(self, config: ChatModelConfig, **kwargs) -> BaseChatModel:
            print(f"    [Cohere] 构建模型: {config.model_key}")
            return None

    chat_model_factory.register(CohereBuilder())
    print(f"  实例注册后 Chat 后端: {chat_model_factory.list_backends()}")

    # 方式三：类注册（工厂自动实例化）
    class MistralBuilder(ChatModelBuilder):
        backend = ["mistral"]

        def build(self, config: ChatModelConfig, **kwargs) -> BaseChatModel:
            return None

    chat_model_factory.register(MistralBuilder)  # 传类而非实例
    print(f"  类注册后 Chat 后端: {chat_model_factory.list_backends()}")

    print()


# ── 3. 扩展新模型类型（工厂的工厂） ──────────────────────


def demo_extend_model_type():
    """注册全新的模型类型。"""
    from abc import abstractmethod
    from src.ai.core.models import (
        ModelBuilder,
        ModelFactory,
        ModelFactoryRegistry,
        model_registry,
    )

    print("=== 3. 扩展新模型类型 ===\n")

    # 3a. 定义新的 Builder 接口
    class RerankBuilder(ModelBuilder[str, object]):
        """重排序模型构建策略接口。"""

        @abstractmethod
        def build(self, model_key: str, **kwargs):
            """构建 Rerank 模型实例。"""

    # 3b. 定义具体实现
    class CohereRerankBuilder(RerankBuilder):
        backend = ["cohere"]

        def build(self, model_key: str, **kwargs):
            print(f"    [Cohere Rerank] 构建模型: {model_key}")
            return f"cohere-rerank:{model_key}"

    class BGERerankBuilder(RerankBuilder):
        backend = ["bge"]

        def build(self, model_key: str, **kwargs):
            print(f"    [BGE Rerank] 构建模型: {model_key}")
            return f"bge-rerank:{model_key}"

    # 3c. 定义新工厂
    class RerankFactory(ModelFactory[RerankBuilder]):
        def create_builder(self, backend: str) -> RerankBuilder:
            return self._resolve(backend, "Rerank")

    # 3d. 注册到 registry
    rerank_factory = RerankFactory()
    rerank_factory.register_all([CohereRerankBuilder, BGERerankBuilder])
    model_registry.register_factory("rerank", rerank_factory)

    print(f"  模型类型: {model_registry.list_model_types()}")
    print(f"  Rerank 后端: {rerank_factory.list_backends()}")

    # 3e. 使用
    builder = model_registry.get_builder("rerank", "cohere")
    result = builder.build("rerank-v3.5")
    print(f"  构建结果: {result}")

    # 3f. 通过快捷属性访问
    rerank = model_registry.get_factory("rerank")
    print(f"  get_factory 访问: {type(rerank).__name__}")

    print()


# ── 4. 统一调度演示 ──────────────────────────────────────


def demo_unified_dispatch():
    """通过 model_registry 统一调度所有类型。"""
    from src.ai.core.models import model_registry

    print("=== 4. 统一调度 ===\n")

    # 所有类型走同一个入口
    for model_type in model_registry.list_model_types():
        factory = model_registry.get_factory(model_type)
        backends = factory.list_backends()
        print(f"  {model_type}: {backends}")

    # get_builder 统一接口，无需 isinstance
    chat_builder = model_registry.get_builder("chat", "openai")
    emb_builder = model_registry.get_builder("embedding", "openai")
    print(f"\n  chat/openai → {type(chat_builder).__name__}")
    print(f"  embedding/openai → {type(emb_builder).__name__}")

    print()


# ── 主入口 ──────────────────────────────────────────────


if __name__ == "__main__":
    print(">>> Builders 模块示例 <<<\n")

    demo_builtin_builders()
    demo_extend_backend()
    demo_extend_model_type()
    demo_unified_dispatch()

    print(">>> 示例结束 <<<")

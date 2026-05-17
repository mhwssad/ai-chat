"""嵌入模型提供商策略接口。"""

from abc import abstractmethod

from src.ai_chat.config.logging_setup import get_logger
from src.ai_chat.llm.base import ModelProvider

logger = get_logger(__name__)


class EmbeddingProvider(ModelProvider):
    """嵌入模型提供商策略。

    与 ChatProvider 职责分离，专门处理文本向量化。
    每个具体实现对应一个底层嵌入 API（OpenAI Embeddings、本地模型 …）。

    子类必须实现 embed 抽象方法。embed_batch 有默认实现（逐条调用 embed），
    子类可覆盖以使用原生批量 API 获得更好性能。
    """

    @property
    def provider_type(self) -> str:
        return "embedding"

    @abstractmethod
    def embed(self, text: str, model_name: str) -> list[float]:
        """使用指定的嵌入模型对单段文本进行向量化。

        Args:
            text: 待向量化的文本字符串
            model_name: 嵌入模型名称

        Returns:
            浮点数向量列表（维度取决于模型）
        """

    def embed_batch(self, texts: list[str], model_name: str) -> list[list[float]]:
        """批量嵌入多段文本。默认实现逐条调用 embed()。

        子类可覆盖此方法以使用原生批量 API 获得更好性能。

        Args:
            texts: 待向量化的文本字符串列表
            model_name: 嵌入模型名称

        Returns:
            嵌入向量列表的列表，与输入 texts 一一对应
        """
        logger.debug("使用默认批量实现: 数量=%d, model=%s", len(texts), model_name)
        return [self.embed(text, model_name) for text in texts]

"""模型配置（纯数据）。

每种模型类型有独立的 BaseSettingsConfig 配置类，仅持有连接数据。
构建逻辑在 builders.py 中，配置类不依赖 LangChain。
"""

from typing import Optional

from pydantic_settings import SettingsConfigDict

from src.ai.config.base_config import BaseSettingsConfig


class ChatModelConfig(BaseSettingsConfig):
    """Chat 模型配置，支持环境变量 CHAT_MODEL_* 覆盖。"""

    model_config = SettingsConfigDict(env_prefix="CHAT_MODEL_")

    model_key: str = ""
    backend: str = "openai"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    context_window: int = 128000
    max_output_tokens: int = 4096


class EmbeddingModelConfig(BaseSettingsConfig):
    """Embedding 模型配置，支持环境变量 EMBEDDING_MODEL_* 覆盖。"""

    model_config = SettingsConfigDict(env_prefix="EMBEDDING_MODEL_")

    model_key: str = ""
    backend: str = "openai"
    api_key: Optional[str] = None
    base_url: Optional[str] = None

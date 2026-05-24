"""文档加载器相关配置。"""

from pydantic import Field

from src.ai.config.base_config import BaseSettingsConfig


class UnstructuredSettings(BaseSettingsConfig):
    """Unstructured 解析服务配置。

    从 .env 文件自动加载，支持云端 API 和本地两种模式。
    """

    api_key: str = Field(
        default="",
        description="Unstructured API Key（云端模式必需）",
    )
    api_url: str = Field(
        default="https://api.unstructured.io/general/v0/general",
        description="Unstructured API URL",
    )
    mode: str = Field(
        default="auto",
        description="解析模式：'local' | 'api' | 'auto'",
    )
    max_file_size: int = Field(
        default=100 * 1024 * 1024,  # 100MB
        description="最大文件大小，超过则跳过解析",
    )
    enabled: bool = Field(
        default=True,
        description="是否启用 Unstructured 解析",
    )

    @property
    def use_api(self) -> bool:
        """是否使用 API 模式。"""
        if self.mode == "api":
            return True
        if self.mode == "auto":
            return bool(self.api_key)
        return False


unstructured_settings = UnstructuredSettings()
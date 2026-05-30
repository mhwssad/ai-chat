"""文档加载器相关配置。

提供各加载器的独立配置类和统一聚合配置 LoaderSettings。
通过环境变量驱动，如 LOADER_TEXT_ENCODINGS、LOADER_OCR_IMAGE_EXTENSIONS、UNSTRUCTURED_STRATEGY 等。
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import SettingsConfigDict

from src.ai.config.base_config import BaseSettingsConfig


class PlainTextSettings(BaseSettingsConfig):
    """纯文本加载器配置。

    环境变量前缀 LOADER_TEXT_，如 LOADER_TEXT_ENCODINGS='["utf-8","gbk"]'。
    """

    model_config = SettingsConfigDict(
        env_prefix="LOADER_TEXT_",
    )

    encodings: list[str] = Field(
        default=["utf-8", "gbk", "latin-1"],
        description="尝试的编码列表，按顺序依次尝试",
    )


class OcrSettings(BaseSettingsConfig):
    """OCR 图片加载器配置。

    环境变量前缀 LOADER_OCR_，如 LOADER_OCR_IMAGE_EXTENSIONS='[".png",".jpg"]'。
    """

    model_config = SettingsConfigDict(
        env_prefix="LOADER_OCR_",
    )

    image_extensions: list[str] = Field(
        default=[".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp", ".gif"],
        description="支持的图片文件扩展名列表",
    )

    @property
    def image_extensions_set(self) -> set[str]:
        """返回扩展名集合，用于快速查找。"""
        return set(self.image_extensions)


class UnstructuredSettings(BaseSettingsConfig):
    """Unstructured 解析服务配置。

    从 .env 文件自动加载，支持云端 API 和本地两种模式。
    环境变量前缀 UNSTRUCTURED_，如 UNSTRUCTURED_STRATEGY=fast。
    """

    model_config = SettingsConfigDict(
        env_prefix="UNSTRUCTURED_",
    )

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
    strategy: str = Field(
        default="fast",
        description="解析策略：'fast'（纯文本提取，通用）、'hi_res'（布局检测+OCR，需额外依赖）、'ocr_only'",
    )
    max_characters: int = Field(
        default=1_000_000,
        description="单个文档最大字符数",
    )
    chunking_strategy: str = Field(
        default="",
        description="分块策略，空字符串表示不分块（留给上层处理）",
    )
    max_file_size: int = Field(
        default=100 * 1024 * 1024,
        description="最大文件大小，超过则跳过解析",
    )
    languages: list[str] = Field(
        default=["chi_sim", "eng"],
        description="OCR 语言列表，对应 Tesseract 语言包名称",
    )

    @property
    def use_api(self) -> bool:
        """是否使用 API 模式。"""
        if self.mode == "api":
            return True
        if self.mode == "auto":
            return bool(self.api_key)
        return False

    @property
    def effective_chunking_strategy(self) -> str | None:
        """获取有效的分块策略，空字符串转为 None。"""
        return self.chunking_strategy or None


class LoaderSettings(BaseSettingsConfig):
    """加载器统一配置聚合。

    将各加载器的独立配置聚合为一个入口，通过 DI 容器注入到各加载器。
    """

    plain_text: PlainTextSettings = Field(
        default_factory=PlainTextSettings,
        description="纯文本加载器配置",
    )
    ocr: OcrSettings = Field(
        default_factory=OcrSettings,
        description="OCR 图片加载器配置",
    )
    unstructured: UnstructuredSettings = Field(
        default_factory=UnstructuredSettings,
        description="Unstructured 解析服务配置",
    )

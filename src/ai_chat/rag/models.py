"""RAG 模块 — 基类、数据类与异常定义。"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


# ======================================================================
# 异常
# ======================================================================

class StoreNotFoundException(Exception):
    """请求的向量存储后端未注册。"""

    def __init__(self, name: str, supported: list[str]) -> None:
        self.name = name
        self.supported = supported
        super().__init__(f"向量存储 '{name}' 未注册。已注册：{supported}")


class LoaderNotFoundException(Exception):
    """请求的文件类型没有对应的加载器。"""

    def __init__(self, extension: str, supported: list[str]) -> None:
        self.extension = extension
        self.supported = supported
        super().__init__(f"文件扩展名 '{extension}' 无对应加载器。已注册：{supported}")


# ======================================================================
# 数据类
# ======================================================================

@dataclass
class VectorStoreConfig:
    """向量存储配置。"""
    persist_path: Optional[str] = None       # 持久化路径
    embedding_model: str = "bge-m3"          # 默认嵌入模型
    chunk_size: int = 500
    chunk_overlap: int = 50


# ======================================================================
# 向量存储策略接口
# ======================================================================

class VectorStoreProvider(ABC):
    """向量存储后端策略接口。"""

    @abstractmethod
    def add_texts(self, texts: list[str], metadatas: Optional[list[dict]] = None) -> None:
        """添加文本到向量存储。"""

    @abstractmethod
    def similarity_search(self, query: str, k: int = 4) -> list[dict]:
        """相似度检索，返回 [{"content": ..., "metadata": ...}]。"""

    @abstractmethod
    def save(self, path: str) -> None:
        """持久化到磁盘。"""

    @abstractmethod
    def load(self, path: str) -> None:
        """从磁盘加载。"""


# ======================================================================
# 文档加载器策略接口
# ======================================================================

class DocumentLoader(ABC):
    """文档加载器策略接口。"""

    SUPPORTED_EXTENSIONS: list[str] = []

    @abstractmethod
    def load(self, file_path: str) -> list[dict]:
        """加载文件，返回 [{"content": ..., "metadata": {"source": ...}}]。"""


# ======================================================================
# 文本分割器策略接口
# ======================================================================

class TextSplitter(ABC):
    """文本分割器策略接口。"""

    @abstractmethod
    def split(self, documents: list[dict]) -> list[dict]:
        """分割文档列表，返回 [{"content": ..., "metadata": ...}]。"""


class SplitterNotFoundException(Exception):
    """请求的文本分割器未注册。"""

    def __init__(self, name: str, supported: list[str]) -> None:
        self.name = name
        self.supported = supported
        super().__init__(f"分割器 '{name}' 未注册。已注册：{supported}")

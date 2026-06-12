"""BM25 关键词检索器 — 配合向量检索实现混合检索。"""

from __future__ import annotations

from src.ai.config.logging_setup import get_logger
import re
from dataclasses import dataclass

logger = get_logger(__name__)


@dataclass
class BM25Result:
    """BM25 检索结果。"""

    doc_id: str
    content: str
    metadata: dict
    score: float


class BM25Retriever:
    """基于 rank_bm25 的关键词检索器。

    使用 jieba 进行中文分词，BM25 算法进行关键词匹配。

    Args:
        k1: BM25 参数 k1（默认 1.5）。
        b: BM25 参数 b（默认 0.75）。
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self._k1 = k1
        self._b = b
        self._bm25 = None
        self._doc_ids: list[str] = []
        self._doc_contents: list[str] = []
        self._doc_metadata: list[dict] = []
        self._tokenized_corpus: list[list[str]] = []

    @property
    def is_built(self) -> bool:
        """索引是否已构建。"""
        return self._bm25 is not None

    def build_index(
        self,
        doc_ids: list[str],
        contents: list[str],
        metadata_list: list[dict],
    ) -> None:
        """构建 BM25 索引。

        Args:
            doc_ids: 文档 ID 列表。
            contents: 文档内容列表。
            metadata_list: 文档元数据列表。
        """
        from rank_bm25 import BM25Okapi

        self._doc_ids = list(doc_ids)
        self._doc_contents = list(contents)
        self._doc_metadata = list(metadata_list)

        # jieba 分词
        self._tokenized_corpus = [self._tokenize(c) for c in contents]
        self._bm25 = BM25Okapi(self._tokenized_corpus, k1=self._k1, b=self._b)
        logger.debug("BM25 索引已构建: %d 个文档", len(doc_ids))

    def search(self, query: str, top_k: int = 10) -> list[BM25Result]:
        """BM25 关键词检索。

        Args:
            query: 查询文本。
            top_k: 返回结果数量。

        Returns:
            BM25 检索结果列表。
        """
        if self._bm25 is None or not self._doc_ids:
            return []

        tokenized_query = self._tokenize(query)
        scores = self._bm25.get_scores(tokenized_query)

        # 按分数排序取 top_k
        indexed_scores = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)[
            :top_k
        ]

        results: list[BM25Result] = []
        for idx, score in indexed_scores:
            if score <= 0:
                continue
            results.append(
                BM25Result(
                    doc_id=self._doc_ids[idx],
                    content=self._doc_contents[idx],
                    metadata=self._doc_metadata[idx],
                    score=float(score),
                )
            )
        return results

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """中文分词。使用 jieba 精确模式，不可用时回退到正则提取。"""
        try:
            import jieba

            return list(jieba.cut(text))
        except ImportError:
            # jieba 不可用时按正则提取中文词组和英文单词
            return re.findall(r"[\u4e00-\u9fff]+|[a-zA-Z]+", text)

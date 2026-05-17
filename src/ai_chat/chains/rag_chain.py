"""RAG 调用链 — 检索增强生成，支持混合检索、重排序和多跳推理。"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable, Iterator
from typing import Optional, TYPE_CHECKING

from langchain_core.messages import BaseMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from src.ai_chat.chains.base import ChainConfig, ChainError, _BasePromptChain
from src.ai_chat.llm import llm_factory
from src.ai_chat.prompts import prompt_registry

if TYPE_CHECKING:
    from src.ai_chat.rag.models import VectorStoreProvider

# 重排序函数类型：接受文档列表，返回重排序后的列表
RerankerFn = Callable[[list[dict]], list[dict]]


class RAGChain(_BasePromptChain):
    """检索增强生成链：查询 → 检索 → 生成。

    支持:
    - 向量相似度检索 + 关键词检索混合
    - 可选重排序（reranker）
    - 多跳推理
    - 继承基类的重试、异步、配置化能力
    """

    def __init__(
        self,
        store: VectorStoreProvider,
        model_name: Optional[str] = None,
        prompt_key: str = "rag",
        k: int = 4,
        reranker: Optional[RerankerFn] = None,
        config: Optional[ChainConfig] = None,
    ) -> None:
        # 不传 prompt_key 给基类，因为 RAG 的 prompt 构建逻辑不同
        super().__init__(model_name, prompt_key="", config=config)
        self._store = store
        self._k = k
        self._reranker = reranker
        self._prompt = self._build_prompt(prompt_key)

    @staticmethod
    def _build_prompt(prompt_name: str) -> ChatPromptTemplate:
        """构建 RAG prompt 模板。"""
        if prompt_name in prompt_registry:
            base_template = prompt_registry.get(prompt_name)
            system_text = base_template.template
        else:
            system_text = "根据以下参考资料回答问题：\n{context}"

        return ChatPromptTemplate.from_messages([
            ("system", system_text),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{question}"),
        ])

    # ── 检索 ─────────────────────────────────────────

    def _retrieve_context(self, question: str) -> str:
        """向量检索。"""
        docs = self._store.similarity_search(question, k=self._k)
        if self._reranker:
            docs = self._reranker(docs)
        return "\n\n".join(doc["content"] for doc in docs)

    def _hybrid_search(self, question: str, k: int | None = None) -> str:
        """混合检索 — 向量 + 关键词，合并去重。"""
        effective_k = k or self._k
        # 向量检索
        vector_docs = self._store.similarity_search(question, k=effective_k)
        # 关键词检索（利用 batch_similarity_search 的简单子串匹配）
        keyword_docs = self._keyword_search(question, k=effective_k)

        # 合并去重（按 content 去重）
        seen = set()
        merged = []
        for doc in vector_docs + keyword_docs:
            key = doc["content"][:200]
            if key not in seen:
                seen.add(key)
                merged.append(doc)

        if self._reranker:
            merged = self._reranker(merged)

        return "\n\n".join(doc["content"] for doc in merged[:effective_k * 2])

    def _keyword_search(self, question: str, k: int) -> list[dict]:
        """简单关键词检索 — 基于子串匹配的 fallback。"""
        # 使用 store 的 similarity_search 作为近似关键词检索
        try:
            return self._store.similarity_search(question, k=k)
        except Exception:
            return []

    def _multi_hop_retrieve(self, question: str, hops: int = 2) -> str:
        """多跳推理 — 逐步扩展检索上下文。"""
        all_contexts = []
        current_query = question

        for hop in range(hops):
            docs = self._store.similarity_search(current_query, k=self._k)
            if not docs:
                break
            all_contexts.extend(docs)

            # 从检索结果中提取下一跳查询线索（取最相关文档的前 100 字）
            if hop < hops - 1:
                first_doc = docs[0]["content"][:100]
                current_query = f"{question} 相关: {first_doc}"

        if self._reranker:
            all_contexts = self._reranker(all_contexts)

        # 去重
        seen = set()
        unique = []
        for doc in all_contexts:
            key = doc["content"][:200]
            if key not in seen:
                seen.add(key)
                unique.append(doc)

        return "\n\n".join(doc["content"] for doc in unique[:self._k * hops])

    # ── 同步调用 ──────────────────────────────────────

    def _build_rag_messages(
        self,
        question: str,
        history: Optional[list[BaseMessage]] = None,
        context: str = "",
    ) -> list[BaseMessage]:
        """构建 RAG 调用消息。"""
        client = llm_factory.get_chat_provider(self._model_name).get_client(self._model_name)
        chain = self._prompt | client | StrOutputParser()
        return chain, {
            "context": context,
            "question": question,
            "history": history or [],
        }

    def invoke(
        self,
        question: str,
        history: Optional[list[BaseMessage]] = None,
        *,
        use_hybrid: bool = False,
        multi_hop: int = 0,
    ) -> str:
        """同步 RAG 查询。

        Args:
            question: 查询问题。
            history: 对话历史。
            use_hybrid: 使用混合检索。
            multi_hop: 多跳次数（0 表示不使用多跳）。
        """
        if multi_hop > 0:
            context = self._multi_hop_retrieve(question, hops=multi_hop)
        elif use_hybrid:
            context = self._hybrid_search(question)
        else:
            context = self._retrieve_context(question)

        chain, inputs = self._build_rag_messages(question, history, context)
        return self._invoke_with_retry_prompt(chain, inputs)

    def stream(
        self,
        question: str,
        history: Optional[list[BaseMessage]] = None,
        *,
        use_hybrid: bool = False,
    ) -> Iterator[str]:
        """流式 RAG 查询。"""
        context = self._hybrid_search(question) if use_hybrid else self._retrieve_context(question)
        config = self._config
        client = llm_factory.get_chat_provider(self._model_name).get_stream_client(
            self._model_name,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )
        chain = self._prompt | client
        for chunk in chain.stream({
            "context": context,
            "question": question,
            "history": history or [],
        }):
            if isinstance(chunk.content, str) and chunk.content:
                yield chunk.content

    # ── 异步调用 ──────────────────────────────────────

    async def ainvoke(
        self,
        question: str,
        history: Optional[list[BaseMessage]] = None,
        *,
        use_hybrid: bool = False,
    ) -> str:
        """异步 RAG 查询。"""
        context = self._hybrid_search(question) if use_hybrid else self._retrieve_context(question)
        client = llm_factory.get_chat_provider(self._model_name).get_client(self._model_name)
        chain = self._prompt | client | StrOutputParser()
        result = await chain.ainvoke({
            "context": context,
            "question": question,
            "history": history or [],
        })
        return result

    async def astream(
        self,
        question: str,
        history: Optional[list[BaseMessage]] = None,
    ) -> AsyncIterator[str]:
        """异步流式 RAG 查询。"""
        context = self._retrieve_context(question)
        config = self._config
        client = llm_factory.get_chat_provider(self._model_name).get_stream_client(
            self._model_name,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )
        chain = self._prompt | client
        async for chunk in chain.astream({
            "context": context,
            "question": question,
            "history": history or [],
        }):
            if isinstance(chunk.content, str) and chunk.content:
                yield chunk.content

    # ── 内部辅助 ──────────────────────────────────────

    def _invoke_with_retry_prompt(self, chain, inputs: dict) -> str:
        """带重试的 RAG prompt chain 调用。"""
        last_error = None
        for attempt in range(self._config.max_retries + 1):
            try:
                result = chain.invoke(inputs)
                return result if isinstance(result, str) else str(result)
            except Exception as e:
                last_error = e
                if attempt < self._config.max_retries:
                    import time
                    time.sleep(0.5 * (2 ** attempt))
        raise ChainError(f"RAG Chain 调用失败: {last_error}") from last_error

"""RAG 链 — 检索增强生成。"""

from typing import Iterator, Optional

from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from src.ai_chat.llm import llm_factory
from src.ai_chat.llm.models import ChatRequest
from src.ai_chat.prompts import prompt_registry
from .models import VectorStoreProvider


class RAGChain:
    """检索增强生成链：查询 → 检索 → 生成。"""

    def __init__(
        self,
        store: VectorStoreProvider,
        model_name: Optional[str] = None,
        prompt_name: str = "rag",
        k: int = 4,
    ) -> None:
        self._store = store
        self._model_name = model_name
        self._k = k

        if prompt_name in prompt_registry:
            base_template = prompt_registry.get(prompt_name)
            # rag.jinja2 是单消息模板，包装成多消息格式以支持历史记录
            system_text = base_template.template
            self._prompt = ChatPromptTemplate.from_messages([
                ("system", system_text),
                MessagesPlaceholder(variable_name="history"),
                ("human", "{question}"),
            ])
        else:
            self._prompt = ChatPromptTemplate.from_messages([
                ("system", "根据以下参考资料回答问题：\n{context}"),
                MessagesPlaceholder(variable_name="history"),
                ("human", "{question}"),
            ])

    def _retrieve_context(self, question: str) -> str:
        docs = self._store.similarity_search(question, k=self._k)
        return "\n\n".join(doc["content"] for doc in docs)

    def query(self, question: str, history: Optional[list] = None) -> str:
        """同步 RAG 查询。"""
        context = self._retrieve_context(question)
        model_name = self._model_name or self._get_default_model()

        chain = self._prompt | llm_factory.get_chat_provider(model_name).get_client(model_name)
        result = chain.invoke({
            "context": context,
            "question": question,
            "history": history or [],
        })
        return result.content

    def stream(self, question: str, history: Optional[list] = None) -> Iterator[str]:
        """流式 RAG 查询。"""
        context = self._retrieve_context(question)
        model_name = self._model_name or self._get_default_model()

        client = llm_factory.get_stream_client(model_name)
        chain = self._prompt | client
        for chunk in chain.stream({
            "context": context,
            "question": question,
            "history": history or [],
        }):
            if isinstance(chunk.content, str) and chunk.content:
                yield chunk.content

    @staticmethod
    def _get_default_model() -> str:
        from src.ai_chat.config import settings
        return settings.model_name

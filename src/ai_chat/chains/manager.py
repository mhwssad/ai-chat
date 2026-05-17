"""Chain 管理器 — 持久化配置与运行时实例的桥梁。"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Optional

from src.ai_chat.chains.base import ChainConfig, _BasePromptChain
from src.ai_chat.chains.factory import chain_factory
from src.ai_chat.chains.models import ChainCreateRequest, ChainRecord
from src.ai_chat.chains.store import ChainStore
from src.ai_chat.config.logging_setup import get_logger

logger = get_logger(__name__)


class ChainManager:
    """链配置管理器 — CRUD + 运行时实例化。

    持久化配置（ChainStore）与运行时工厂（chain_factory）的桥梁：
    - create/update/delete 操作持久化层
    - instantiate 从持久化配置重建运行时链实例
    - invoke/stream 通过 instantiate 执行链
    """

    def __init__(self, store: Optional[ChainStore] = None) -> None:
        self._store = store or ChainStore()

    # ── CRUD ──────────────────────────────────────────

    def create_chain(
        self,
        name: str,
        chain_type: str,
        model_name: str = "",
        config: Optional[dict] = None,
        prompt_context: Optional[dict] = None,
        description: str = "",
        tags: str = "",
    ) -> ChainRecord:
        """创建链配置。"""
        request = ChainCreateRequest(
            name=name,
            chain_type=chain_type,
            model_name=model_name,
            config=config or {},
            prompt_context=prompt_context or {},
            description=description,
            tags=tags,
        )
        record = self._store.create(request)
        logger.info("创建链配置: %s (type=%s)", name, chain_type)
        return record

    def get_chain(self, name: str) -> ChainRecord:
        return self._store.get(name)

    def update_chain(self, name: str, **fields) -> ChainRecord:
        return self._store.update(name, **fields)

    def delete_chain(self, name: str) -> None:
        self._store.delete(name)
        logger.info("删除链配置: %s", name)

    def list_chains(self, limit: int = 50, offset: int = 0) -> list[ChainRecord]:
        return self._store.list(limit=limit, offset=offset)

    def search_chains(self, keyword: str, limit: int = 50) -> list[ChainRecord]:
        return self._store.search(keyword, limit=limit)

    def chain_exists(self, name: str) -> bool:
        return self._store.exists(name)

    def count_chains(self) -> int:
        return self._store.count()

    # ── 实例化 ──────────────────────────────────────

    def instantiate(self, name: str) -> _BasePromptChain:
        """从持久化配置创建运行时链实例。"""
        record = self.get_chain(name)
        config = self._build_config(record)
        return chain_factory.create(
            record.chain_type,
            model_name=record.model_name or None,
            config=config,
            prompt_context=record.prompt_context,
        )

    @staticmethod
    def _build_config(record: ChainRecord) -> ChainConfig:
        """从持久化记录构建 ChainConfig。"""
        cfg = record.config or {}
        return ChainConfig(
            temperature=cfg.get("temperature", 0.7),
            max_tokens=cfg.get("max_tokens"),
            stop=cfg.get("stop"),
            max_retries=cfg.get("max_retries", 2),
            timeout=cfg.get("timeout", 60),
        )

    # ── 执行 ────────────────────────────────────────

    def invoke(self, name: str, **inputs) -> str:
        """执行链。"""
        chain = self.instantiate(name)
        record = self.get_chain(name)

        # RAGChain 特殊处理
        if record.chain_type == "rag":
            return chain.invoke(
                inputs.get("question", inputs.get("input", "")),
                use_hybrid=inputs.get("use_hybrid", False),
                multi_hop=inputs.get("multi_hop", 0),
            )

        # 通用链
        input_text = inputs.get("input", "")
        return chain.invoke(input_text)

    def stream(self, name: str, **inputs) -> Iterator[str]:
        """流式执行链。"""
        chain = self.instantiate(name)
        record = self.get_chain(name)

        if record.chain_type == "rag":
            yield from chain.stream(
                inputs.get("question", inputs.get("input", "")),
                use_hybrid=inputs.get("use_hybrid", False),
            )
        else:
            input_text = inputs.get("input", "")
            yield from chain.stream(input_text)


# 全局单例
chain_manager = ChainManager()

"""系统服务 — 为 TUI 提供运行状态、配置摘要和系统动作。"""

from __future__ import annotations

from typing import Any

from src.ai.security.crypto import generate_key


class SystemService:
    """系统服务。

    负责：
    1. 聚合运行状态摘要
    2. 聚合配置摘要
    3. 提供系统级动作
    """

    def __init__(
        self,
        *,
        model_service: Any,
        scheduler_service: Any,
        memory_service: Any,
        tool_service: Any,
        settings: Any,
        thread_pool: Any,
    ) -> None:
        self._model_service = model_service
        self._scheduler_service = scheduler_service
        self._memory_service = memory_service
        self._tool_service = tool_service
        self._settings = settings
        self._thread_pool = thread_pool

    def get_runtime_status(self) -> dict[str, Any]:
        """获取运行状态摘要。"""
        model_cfg = self._model_service.chat_config
        model_key = model_cfg.model_key or ""
        memory_stats, memory_ok = self._safe_call(
            self._memory_service.get_stats,
            default={},
        )
        tools, tools_ok = self._safe_call(
            lambda: self._tool_service.list_tools(enabled_only=False),
            default=[],
        )
        enabled_tools = [tool for tool in tools if tool.get("enabled")]
        scheduler_enabled = bool(self._settings.scheduler.scheduler_enabled)
        scheduler_running = bool(self._scheduler_service.is_running)

        return {
            "model_key": model_key or "未配置",
            "model_backend": model_cfg.backend,
            "model_status": "configured" if model_key else "not_configured",
            "scheduler_running": scheduler_running,
            "scheduler_status": self._status_label(
                configured=True,
                enabled=scheduler_enabled,
                healthy=scheduler_running,
                disabled_label="disabled",
            ),
            "memory_count": memory_stats.get("total", 0),
            "memory_status": "available" if memory_ok else "error",
            "tool_count": len(tools),
            "enabled_tool_count": len(enabled_tools),
            "tool_status": "available" if tools_ok else "error",
            "thread_pool_started": self._thread_pool.started,
            "thread_pool_status": "available"
            if self._thread_pool.started
            else "not_started",
        }

    def get_config_summary(self) -> dict[str, Any]:
        """获取关键配置摘要。"""
        rag = self._settings.rag
        scheduler = self._settings.scheduler
        thread_pool = self._settings.thread_pool
        image_cfg = self._model_service.image_config
        tts_cfg = self._model_service.tts_config

        return {
            "rag_persist_dir": rag.rag_persist_dir,
            "rag_collection_name": rag.rag_collection_name,
            "rag_top_k": rag.rag_top_k,
            "scheduler_enabled": scheduler.scheduler_enabled,
            "scheduler_check_interval": scheduler.scheduler_check_interval,
            "thread_pool_io": thread_pool.io_size,
            "thread_pool_cpu": thread_pool.cpu_size,
            "thread_pool_bg": thread_pool.bg_size,
            "image_output_dir": image_cfg.output_dir if image_cfg else "",
            "tts_output_dir": tts_cfg.output_dir if tts_cfg else "",
        }

    def generate_encryption_key(self) -> str:
        """生成新的加密密钥。"""
        return generate_key()

    @staticmethod
    def _safe_call(func: Any, *, default: Any) -> tuple[Any, bool]:
        """安全调用状态收集函数。"""
        try:
            return func(), True
        except Exception:
            return default, False

    @staticmethod
    def _status_label(
        *,
        configured: bool,
        enabled: bool,
        healthy: bool,
        disabled_label: str = "disabled",
    ) -> str:
        """生成统一服务状态标签。"""
        if not configured:
            return "not_configured"
        if not enabled:
            return disabled_label
        return "available" if healthy else "stopped"

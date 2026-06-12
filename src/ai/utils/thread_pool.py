"""统一线程池管理器。

提供分类线程池用于不同类型的阻塞任务，支持优雅启动和关闭生命周期。

架构:
    ThreadPoolManager (单例)
      ├── io_pool:  ThreadPoolExecutor  — 文件 IO、数据库查询、Chroma 查询
      ├── cpu_pool: ProcessPoolExecutor — CPU 密集型任务（预留）
      └── bg_pool:  ThreadPoolExecutor  — 后台任务、TUI 数据加载、状态刷新

用法:
    # 异步上下文（FastAPI 路由、async def 函数）
    pool = get_thread_pool()
    result = await pool.run_io(sync_func, arg1, arg2)

    # 同步上下文（TUI 主线程、fire-and-forget）
    pool = get_thread_pool()
    pool.run_bg(heavy_func, arg1)  # 不阻塞，返回 Future
"""

from __future__ import annotations

import asyncio
import functools
from src.ai.config.logging_setup import get_logger
from collections.abc import Awaitable, Callable
from concurrent.futures import Future, ProcessPoolExecutor, ThreadPoolExecutor
from typing import Any, TypeVar

from src.ai.exception.pool_exception import ThreadPoolShutdownError

logger = get_logger(__name__)

T = TypeVar("T")


class ThreadPoolManager:
    """统一线程池管理器。

    提供三个分类线程池：
    - io_pool:  IO 密集型（文件读写、数据库、Chroma 查询）
    - cpu_pool: CPU 密集型（embedding 计算、文本切分）
    - bg_pool:  后台任务（TUI 数据加载、状态刷新、索引维护）

    Attributes:
        _io_pool:  IO 密集型线程池。
        _cpu_pool: CPU 密集型进程池。
        _bg_pool:  后台任务线程池。
        _started:  是否已启动。
    """

    def __init__(
        self,
        io_size: int = 16,
        cpu_size: int = 4,
        bg_size: int = 4,
        shutdown_timeout: float = 30.0,
    ) -> None:
        self._io_size = io_size
        self._cpu_size = cpu_size
        self._bg_size = bg_size
        self._shutdown_timeout = shutdown_timeout

        self._io_pool: ThreadPoolExecutor | None = None
        self._cpu_pool: ProcessPoolExecutor | None = None
        self._bg_pool: ThreadPoolExecutor | None = None
        self._started: bool = False

    # ── 生命周期 ─────────────────────────────────────────────

    def start(self) -> None:
        """启动所有线程池。

        幂等操作，重复调用无副作用。
        """
        if self._started:
            return

        self._io_pool = ThreadPoolExecutor(
            max_workers=self._io_size,
            thread_name_prefix="io-pool",
        )
        self._cpu_pool = ProcessPoolExecutor(
            max_workers=self._cpu_size,
        )
        self._bg_pool = ThreadPoolExecutor(
            max_workers=self._bg_size,
            thread_name_prefix="bg-pool",
        )
        self._started = True
        logger.info(
            "线程池已启动: io=%d, cpu=%d, bg=%d",
            self._io_size,
            self._cpu_size,
            self._bg_size,
        )

    async def shutdown(self, timeout: float | None = None) -> None:
        """优雅关闭所有线程池。

        停止接受新任务，等待已提交任务完成。

        Args:
            timeout: 等待超时（秒），None 使用默认值。
        """
        if not self._started:
            return

        wait_timeout = timeout or self._shutdown_timeout

        for name, pool in [
            ("io", self._io_pool),
            ("cpu", self._cpu_pool),
            ("bg", self._bg_pool),
        ]:
            if pool is None:
                continue
            pool.shutdown(wait=False)

        # 在事件循环中等待关闭完成
        loop = asyncio.get_running_loop()
        for name, pool in [
            ("io", self._io_pool),
            ("cpu", self._cpu_pool),
            ("bg", self._bg_pool),
        ]:
            if pool is None:
                continue
            done = await loop.run_in_executor(
                None,
                self._wait_shutdown,
                pool,
                name,
                wait_timeout,
            )
            if not done:
                logger.warning("线程池 %s 关闭超时 (%.1fs)", name, wait_timeout)

        self._io_pool = None
        self._cpu_pool = None
        self._bg_pool = None
        self._started = False
        logger.info("线程池已关闭")

    @staticmethod
    def _wait_shutdown(
        pool: ThreadPoolExecutor | ProcessPoolExecutor,
        name: str,
        timeout: float,
    ) -> bool:
        """同步等待线程池关闭（在线程中执行）。

        Args:
            pool: 线程池实例。
            name: 线程池名称（用于日志）。
            timeout: 等待超时。

        Returns:
            True 表示正常关闭，False 表示超时。
        """
        try:
            pool.shutdown(wait=True)
            return True
        except Exception:
            return False

    # ── 检查 ─────────────────────────────────────────────────

    @property
    def started(self) -> bool:
        """线程池是否已启动。"""
        return self._started

    def _ensure_started(self) -> None:
        """确保线程池已启动。"""
        if not self._started:
            raise ThreadPoolShutdownError("线程池未启动或已关闭")

    # ── 异步上下文提交 ───────────────────────────────────────

    async def run_io(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """在 IO 线程池中执行同步函数（异步等待结果）。

        用于 async def 函数中将同步阻塞调用移至线程池。

        Args:
            func: 要执行的同步函数。
            *args: 位置参数。
            **kwargs: 关键字参数。

        Returns:
            函数执行结果。

        Raises:
            ThreadPoolShutdownError: 线程池未启动或已关闭。
        """
        self._ensure_started()
        assert self._io_pool is not None
        loop = asyncio.get_running_loop()
        if kwargs:
            partial_func = functools.partial(func, *args, **kwargs)
            return await loop.run_in_executor(self._io_pool, partial_func)
        return await loop.run_in_executor(self._io_pool, func, *args)

    async def run_cpu(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """在 CPU 进程池中执行函数（异步等待结果）。

        用于 async def 函数中将 CPU 密集型任务移至进程池。

        Args:
            func: 要执行的函数（必须可 pickle）。
            *args: 位置参数。
            **kwargs: 关键字参数。

        Returns:
            函数执行结果。

        Raises:
            ThreadPoolShutdownError: 线程池未启动或已关闭。
        """
        self._ensure_started()
        assert self._cpu_pool is not None
        loop = asyncio.get_running_loop()
        if kwargs:
            partial_func = functools.partial(func, *args, **kwargs)
            return await loop.run_in_executor(self._cpu_pool, partial_func)
        return await loop.run_in_executor(self._cpu_pool, func, *args)

    # ── 同步上下文提交 ───────────────────────────────────────

    def run_bg(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> Future[T]:
        """在后台线程池中执行函数（fire-and-forget）。

        用于同步上下文（TUI 主线程），提交任务后立即返回不阻塞。

        Args:
            func: 要执行的函数。
            *args: 位置参数。
            **kwargs: 关键字参数。

        Returns:
            concurrent.futures.Future 对象，可选等待结果。

        Raises:
            ThreadPoolShutdownError: 线程池未启动或已关闭。
        """
        self._ensure_started()
        assert self._bg_pool is not None
        if kwargs:
            return self._bg_pool.submit(functools.partial(func, *args, **kwargs))
        return self._bg_pool.submit(func, *args)

    def run_io_sync(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """在 IO 线程池中执行同步函数（阻塞等待结果）。

        用于同步上下文但需要等待结果的场景。
        注意：不能在 asyncio 事件循环中调用，否则会死锁。

        Args:
            func: 要执行的同步函数。
            *args: 位置参数。
            **kwargs: 关键字参数。

        Returns:
            函数执行结果。

        Raises:
            ThreadPoolShutdownError: 线程池未启动或已关闭。
        """
        self._ensure_started()
        assert self._io_pool is not None
        if kwargs:
            return self._io_pool.submit(
                functools.partial(func, *args, **kwargs)
            ).result()
        return self._io_pool.submit(func, *args).result()


# ── 模块级单例 ──────────────────────────────────────────────

_instance: ThreadPoolManager | None = None


def get_thread_pool() -> ThreadPoolManager:
    """获取线程池管理器单例。

    首次调用时自动从配置初始化并启动。

    Returns:
        ThreadPoolManager 实例。
    """
    global _instance
    if _instance is None:
        from src.ai.config.container import config

        tp_settings = config.settings.thread_pool
        _instance = ThreadPoolManager(
            io_size=tp_settings.io_size,
            cpu_size=tp_settings.cpu_size,
            bg_size=tp_settings.bg_size,
            shutdown_timeout=tp_settings.shutdown_timeout,
        )
        _instance.start()
    return _instance


async def shutdown_thread_pool(timeout: float | None = None) -> None:
    """关闭线程池管理器。

    Args:
        timeout: 等待超时（秒）。
    """
    global _instance
    if _instance is not None:
        await _instance.shutdown(timeout=timeout)
        _instance = None


# ── 装饰器 ──────────────────────────────────────────────────


def io_bound(
    func: Callable[..., T],
) -> Callable[..., Awaitable[T]]:
    """装饰器：将同步函数包装为异步，在 IO 线程池中执行。

    用法::

        @io_bound
        def read_config(path: str) -> dict: ...

        # 在 async 函数中调用
        config = await read_config("/path/to/config")
    """

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> T:
        return await get_thread_pool().run_io(func, *args, **kwargs)

    return wrapper


def cpu_bound(
    func: Callable[..., T],
) -> Callable[..., Awaitable[T]]:
    """装饰器：将同步函数包装为异步，在 CPU 进程池中执行。

    用法::

        @cpu_bound
        def compute_hash(data: bytes) -> str: ...

        result = await compute_hash(b"some data")
    """

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> T:
        return await get_thread_pool().run_cpu(func, *args, **kwargs)

    return wrapper

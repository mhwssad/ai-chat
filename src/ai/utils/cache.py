"""通用 LRU 缓存 — 线程安全，支持 TTL 过期。

供 prompts、memory、llm 等模块复用。

Usage::

    from src.ai.utils.cache import LRUCache

    cache = LRUCache[str, ChatPromptTemplate](maxsize=64)
    cache.put("key", value)
    result = cache.get("key")
    cache.invalidate("key")
"""


import threading
import time
from collections import OrderedDict
from typing import Generic, Optional, TypeVar, cast

K = TypeVar("K")
V = TypeVar("V")


class LRUCache(Generic[K, V]):
    """线程安全 LRU 缓存，支持可选 TTL 过期。

    Args:
        maxsize: 最大缓存条目数，超出时淘汰最久未访问的
        ttl: 生存时间（秒），None 表示永不过期
    """

    def __init__(self, maxsize: int = 128, ttl: Optional[float] = None) -> None:
        self._maxsize = maxsize
        self._ttl = ttl
        self._cache: OrderedDict[K, tuple[V, float]] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: K) -> Optional[V]:
        """获取缓存值，不存在或已过期返回 None。"""
        with self._lock:
            if key not in self._cache:
                return None
            value, ts = self._cache[key]
            if self._ttl and time.monotonic() - ts > self._ttl:
                del self._cache[key]
                return None
            self._cache.move_to_end(key)
            return value

    def put(self, key: K, value: V) -> None:
        """写入缓存，key 已存在时更新值并移到最新位置。"""
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = (value, time.monotonic())
            while len(self._cache) > self._maxsize:
                self._cache.popitem(last=False)

    def invalidate(self, key: K) -> None:
        """移除指定 key 的缓存。"""
        with self._lock:
            self._cache.pop(key, None)

    def clear(self) -> None:
        """清空所有缓存。"""
        with self._lock:
            self._cache.clear()

    def __contains__(self, key: object) -> bool:
        with self._lock:
            k = cast(K, key)
            if k not in self._cache:
                return False
            _, ts = self._cache[k]
            if self._ttl and time.monotonic() - ts > self._ttl:
                del self._cache[k]
                return False
            return True

    def __len__(self) -> int:
        with self._lock:
            return len(self._cache)

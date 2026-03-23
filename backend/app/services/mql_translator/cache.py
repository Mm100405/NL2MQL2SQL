"""
cache.py - MQL 查询结果缓存

LRU + TTL 缓存机制，用于缓存 MQL -> SQL 转换结果和查询结果。

使用方式：
    cache = MQLQueryCache(max_size=256, ttl=300)
    key = cache.make_key(mql, dialect)
    result = cache.get(key)
    if result is None:
        result = do_translate(mql)
        cache.set(key, result)
"""

import hashlib
import json
import time
import logging
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from collections import OrderedDict
import threading

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """缓存条目"""
    result: Any
    timestamp: float
    hit_count: int = 0

    def is_expired(self, ttl: float) -> bool:
        """检查是否过期"""
        return time.time() - self.timestamp > ttl


class MQLQueryCache:
    """
    MQL 查询缓存

    特性：
    - LRU（最近最少使用）淘汰策略
    - TTL（Time To Live）过期机制
    - 线程安全
    - 命中率统计
    """

    def __init__(self, max_size: int = 256, ttl: float = 300):
        """
        初始化缓存

        Args:
            max_size: 最大缓存条目数
            ttl: 过期时间（秒），默认 5 分钟
        """
        self.max_size = max_size
        self.ttl = ttl
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()

        # 统计
        self._hits = 0
        self._misses = 0

    def make_key(self, mql: Dict[str, Any], dialect: str = "mysql") -> str:
        """
        生成缓存键

        Args:
            mql: MQL 对象
            dialect: SQL 方言

        Returns:
            缓存键字符串
        """
        # 序列化为 JSON（确保键一致）
        # 使用 sort_keys=True 确保顺序一致
        mql_json = json.dumps(mql, sort_keys=True, ensure_ascii=False, default=str)

        # 添加方言
        content = f"{mql_json}|{dialect}"

        # 计算 SHA256 哈希
        return hashlib.sha256(content.encode()).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存

        Args:
            key: 缓存键

        Returns:
            缓存结果或 None
        """
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None

            entry = self._cache[key]

            # 检查过期
            if entry.is_expired(self.ttl):
                del self._cache[key]
                self._misses += 1
                return None

            # 更新访问顺序（移到末尾）
            self._cache.move_to_end(key)

            # 增加命中计数
            entry.hit_count += 1
            self._hits += 1

            return entry.result

    def set(self, key: str, result: Any):
        """
        设置缓存

        Args:
            key: 缓存键
            result: 缓存结果
        """
        with self._lock:
            # 如果已存在，更新
            if key in self._cache:
                self._cache[key] = CacheEntry(result=result, timestamp=time.time())
                self._cache.move_to_end(key)
                return

            # 如果达到最大容量，淘汰最旧的
            while len(self._cache) >= self.max_size:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]

            # 添加新条目
            self._cache[key] = CacheEntry(result=result, timestamp=time.time())

    def invalidate(self, key: str):
        """删除指定缓存"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]

    def clear(self):
        """清空所有缓存"""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self._lock:
            total = self._hits + self._misses
            hit_rate = self._hits / total if total > 0 else 0

            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "ttl": self.ttl,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": hit_rate,
            }

    def cleanup_expired(self):
        """清理过期条目"""
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired(self.ttl)
            ]
            for key in expired_keys:
                del self._cache[key]

            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")


class TranslationCache:
    """
    MQL -> SQL 转换结果缓存

    使用全局 MQLQueryCache 实例。
    """

    _instance: Optional["TranslationCache"] = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, max_size: int = 256, ttl: float = 300):
        if TranslationCache._initialized:
            return

        self._cache = MQLQueryCache(max_size=max_size, ttl=ttl)
        TranslationCache._initialized = True

    def get_translation(
        self, mql: Dict[str, Any], dialect: str
    ) -> Optional[Dict[str, Any]]:
        """获取翻译结果缓存"""
        key = self._cache.make_key({"mql": mql, "dialect": dialect}, dialect)
        return self._cache.get(key)

    def set_translation(
        self, mql: Dict[str, Any], dialect: str, result: Dict[str, Any]
    ):
        """设置翻译结果缓存"""
        key = self._cache.make_key({"mql": mql, "dialect": dialect}, dialect)
        self._cache.set(key, result)

    def invalidate(self, mql: Dict[str, Any], dialect: str):
        """使缓存失效"""
        key = self._cache.make_key({"mql": mql, "dialect": dialect}, dialect)
        self._cache.invalidate(key)

    def clear(self):
        """清空缓存"""
        self._cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self._cache.get_stats()


# 全局缓存实例
_translation_cache: Optional[TranslationCache] = None


def get_translation_cache() -> TranslationCache:
    """获取全局翻译缓存实例"""
    global _translation_cache
    if _translation_cache is None:
        from app.config import settings
        _translation_cache = TranslationCache(
            max_size=settings.MQL_CACHE_MAX_SIZE,
            ttl=settings.MQL_CACHE_TTL,
        )
    return _translation_cache

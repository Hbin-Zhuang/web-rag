"""
核心缓存服务实现
提供多级缓存管理、自动清理和性能优化功能
"""

import time
import threading
import hashlib
import pickle
import os
import json
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union, Callable
from enum import Enum
from collections import OrderedDict

from ..logging.logging_service import get_logging_service, ILoggingService
from ..monitoring.metrics_service import get_metrics_service


class CacheStrategy(Enum):
    """缓存策略枚举"""
    LRU = "lru"           # 最近最少使用
    LFU = "lfu"           # 最少使用频率
    FIFO = "fifo"         # 先进先出
    TTL = "ttl"           # 基于生存时间


@dataclass
class CacheEntry:
    """缓存条目数据类"""
    key: str
    value: Any
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    ttl: Optional[int] = None  # 秒
    size: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.ttl is None:
            return False

        return (datetime.now() - self.created_at).total_seconds() > self.ttl

    def access(self):
        """记录访问"""
        self.last_accessed = datetime.now()
        self.access_count += 1

    def get_age(self) -> float:
        """获取条目年龄（秒）"""
        return (datetime.now() - self.created_at).total_seconds()


@dataclass
class CacheStats:
    """缓存统计信息"""
    total_size: int = 0
    entry_count: int = 0
    hit_count: int = 0
    miss_count: int = 0
    eviction_count: int = 0
    total_requests: int = 0

    @property
    def hit_rate(self) -> float:
        """命中率"""
        if self.total_requests == 0:
            return 0.0
        return self.hit_count / self.total_requests

    @property
    def miss_rate(self) -> float:
        """未命中率"""
        return 1.0 - self.hit_rate


class CacheService:
    """核心缓存服务"""

    def __init__(self,
                 max_size: int = 1000,
                 max_memory_mb: int = 100,
                 strategy: CacheStrategy = CacheStrategy.LRU,
                 default_ttl: Optional[int] = None,
                 persistence_path: Optional[str] = None,
                 logger_service: Optional[ILoggingService] = None):
        """初始化缓存服务

        Args:
            max_size: 最大条目数
            max_memory_mb: 最大内存使用（MB）
            strategy: 缓存策略
            default_ttl: 默认TTL（秒）
            persistence_path: 持久化文件路径
            logger_service: 日志服务
        """
        self._max_size = max_size
        self._max_memory = max_memory_mb * 1024 * 1024  # 转换为字节
        self._strategy = strategy
        self._default_ttl = default_ttl
        self._persistence_path = persistence_path
        self._logger = logger_service or get_logging_service()
        self._metrics = get_metrics_service()

        # 缓存存储
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()

        # 统计信息
        self._stats = CacheStats()

        # 自动清理线程
        self._cleanup_thread = None
        self._cleanup_interval = 60  # 60秒清理一次
        self._stop_cleanup = threading.Event()

        # 启动自动清理
        self._start_cleanup_thread()

        # 加载持久化数据
        if self._persistence_path:
            self._load_cache()

        self._logger.info(f"缓存服务初始化完成: {strategy.value}, 最大{max_size}项, {max_memory_mb}MB")

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值

        Args:
            key: 缓存键

        Returns:
            缓存值或None
        """
        with self._lock:
            self._stats.total_requests += 1

            if key not in self._cache:
                self._stats.miss_count += 1
                self._metrics.increment_counter('cache_miss_total', {'key_prefix': self._get_key_prefix(key)})
                return None

            entry = self._cache[key]

            # 检查是否过期
            if entry.is_expired():
                del self._cache[key]
                self._stats.miss_count += 1
                self._stats.entry_count -= 1
                self._metrics.increment_counter('cache_expired_total', {'key_prefix': self._get_key_prefix(key)})
                return None

            # 记录访问
            entry.access()
            self._stats.hit_count += 1

            # 根据策略更新位置
            if self._strategy == CacheStrategy.LRU:
                # 移到末尾（最近使用）
                self._cache.move_to_end(key)

            self._metrics.increment_counter('cache_hit_total', {'key_prefix': self._get_key_prefix(key)})
            self._logger.debug(f"缓存命中: {key}")

            return entry.value

    def put(self, key: str, value: Any, ttl: Optional[int] = None, metadata: Optional[Dict] = None) -> bool:
        """设置缓存值

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 生存时间（秒）
            metadata: 元数据

        Returns:
            是否成功
        """
        with self._lock:
            try:
                # 计算大小
                size = self._calculate_size(value)

                # 检查是否超过内存限制
                if size > self._max_memory:
                    self._logger.warning(f"缓存项过大: {key}, 大小: {size / (1024*1024):.2f}MB")
                    return False

                # 如果键已存在，先删除
                if key in self._cache:
                    old_entry = self._cache[key]
                    self._stats.total_size -= old_entry.size
                    del self._cache[key]
                    self._stats.entry_count -= 1

                # 创建新条目
                entry = CacheEntry(
                    key=key,
                    value=value,
                    created_at=datetime.now(),
                    last_accessed=datetime.now(),
                    ttl=ttl or self._default_ttl,
                    size=size,
                    metadata=metadata or {}
                )

                # 确保有足够空间
                self._ensure_capacity(size)

                # 添加到缓存
                self._cache[key] = entry
                self._stats.entry_count += 1
                self._stats.total_size += size

                self._metrics.increment_counter('cache_put_total', {'key_prefix': self._get_key_prefix(key)})
                self._metrics.record_metric('cache_entry_size', size, {'key_prefix': self._get_key_prefix(key)})

                self._logger.debug(f"缓存设置: {key}, 大小: {size}")

                return True

            except Exception as e:
                self._logger.error(f"缓存设置失败: {key}", exception=e)
                return False

    def delete(self, key: str) -> bool:
        """删除缓存项

        Args:
            key: 缓存键

        Returns:
            是否成功删除
        """
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                self._stats.total_size -= entry.size
                self._stats.entry_count -= 1
                del self._cache[key]

                self._metrics.increment_counter('cache_delete_total', {'key_prefix': self._get_key_prefix(key)})
                self._logger.debug(f"缓存删除: {key}")

                return True

            return False

    def clear(self):
        """清空缓存"""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._stats.entry_count = 0
            self._stats.total_size = 0

            self._metrics.increment_counter('cache_clear_total')
            self._logger.info(f"缓存清空: 删除了 {count} 个条目")

    def get_stats(self) -> CacheStats:
        """获取缓存统计信息"""
        with self._lock:
            return CacheStats(
                total_size=self._stats.total_size,
                entry_count=self._stats.entry_count,
                hit_count=self._stats.hit_count,
                miss_count=self._stats.miss_count,
                eviction_count=self._stats.eviction_count,
                total_requests=self._stats.total_requests
            )

    def get_memory_usage(self) -> Dict[str, Any]:
        """获取内存使用情况"""
        with self._lock:
            return {
                'total_size_bytes': self._stats.total_size,
                'total_size_mb': self._stats.total_size / (1024 * 1024),
                'max_memory_mb': self._max_memory / (1024 * 1024),
                'usage_percentage': (self._stats.total_size / self._max_memory) * 100 if self._max_memory > 0 else 0,
                'entry_count': self._stats.entry_count,
                'max_entries': self._max_size
            }

    def _ensure_capacity(self, new_size: int):
        """确保有足够的容量"""
        # 检查条目数量限制
        while len(self._cache) >= self._max_size:
            self._evict_one()

        # 检查内存限制
        while self._stats.total_size + new_size > self._max_memory and self._cache:
            self._evict_one()

    def _evict_one(self):
        """驱逐一个条目"""
        if not self._cache:
            return

        if self._strategy == CacheStrategy.LRU:
            # 删除最久未使用的（第一个）
            key, entry = self._cache.popitem(last=False)
        elif self._strategy == CacheStrategy.LFU:
            # 删除使用频率最低的
            min_key = min(self._cache.keys(), key=lambda k: self._cache[k].access_count)
            entry = self._cache.pop(min_key)
            key = min_key
        elif self._strategy == CacheStrategy.FIFO:
            # 删除最早添加的（第一个）
            key, entry = self._cache.popitem(last=False)
        else:  # TTL
            # 优先删除过期的，然后是最早的
            expired_keys = [k for k, v in self._cache.items() if v.is_expired()]
            if expired_keys:
                key = expired_keys[0]
                entry = self._cache.pop(key)
            else:
                key, entry = self._cache.popitem(last=False)

        self._stats.total_size -= entry.size
        self._stats.entry_count -= 1
        self._stats.eviction_count += 1

        self._metrics.increment_counter('cache_eviction_total', {'strategy': self._strategy.value})
        self._logger.debug(f"缓存驱逐: {key}, 策略: {self._strategy.value}")

    def _calculate_size(self, value: Any) -> int:
        """计算值的大小"""
        try:
            # 尝试使用pickle序列化来估算大小
            return len(pickle.dumps(value))
        except:
            # 如果无法序列化，使用简单估算
            if isinstance(value, str):
                return len(value.encode('utf-8'))
            elif isinstance(value, (int, float)):
                return 8
            elif isinstance(value, (list, tuple)):
                return sum(self._calculate_size(item) for item in value)
            elif isinstance(value, dict):
                return sum(self._calculate_size(k) + self._calculate_size(v) for k, v in value.items())
            else:
                return 1024  # 默认1KB

    def _get_key_prefix(self, key: str) -> str:
        """获取键前缀用于分类统计"""
        parts = key.split(':', 1)
        return parts[0] if len(parts) > 1 else 'default'

    def _cleanup_expired(self):
        """清理过期条目"""
        with self._lock:
            expired_keys = []

            for key, entry in self._cache.items():
                if entry.is_expired():
                    expired_keys.append(key)

            for key in expired_keys:
                entry = self._cache.pop(key)
                self._stats.total_size -= entry.size
                self._stats.entry_count -= 1
                self._stats.eviction_count += 1

                self._metrics.increment_counter('cache_cleanup_expired_total')

            if expired_keys:
                self._logger.debug(f"清理过期缓存: {len(expired_keys)} 个条目")

    def _start_cleanup_thread(self):
        """启动清理线程"""
        def cleanup_worker():
            while not self._stop_cleanup.wait(self._cleanup_interval):
                try:
                    self._cleanup_expired()

                    # 定期保存缓存
                    if self._persistence_path:
                        self._save_cache()

                except Exception as e:
                    self._logger.error("缓存清理失败", exception=e)

        self._cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        self._cleanup_thread.start()

    def _save_cache(self):
        """保存缓存到文件"""
        if not self._persistence_path:
            return

        try:
            os.makedirs(os.path.dirname(self._persistence_path), exist_ok=True)

            cache_data = {
                'entries': {},
                'stats': {
                    'hit_count': self._stats.hit_count,
                    'miss_count': self._stats.miss_count,
                    'eviction_count': self._stats.eviction_count,
                    'total_requests': self._stats.total_requests
                },
                'timestamp': datetime.now().isoformat()
            }

            # 只保存非过期的条目
            for key, entry in self._cache.items():
                if not entry.is_expired():
                    cache_data['entries'][key] = {
                        'value': entry.value,
                        'created_at': entry.created_at.isoformat(),
                        'last_accessed': entry.last_accessed.isoformat(),
                        'access_count': entry.access_count,
                        'ttl': entry.ttl,
                        'metadata': entry.metadata
                    }

            with open(self._persistence_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)

            self._logger.debug(f"缓存已保存到: {self._persistence_path}")

        except Exception as e:
            self._logger.error(f"保存缓存失败: {self._persistence_path}", exception=e)

    def _load_cache(self):
        """从文件加载缓存"""
        if not self._persistence_path or not os.path.exists(self._persistence_path):
            return

        try:
            with open(self._persistence_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)

            # 恢复统计信息
            if 'stats' in cache_data:
                stats = cache_data['stats']
                self._stats.hit_count = stats.get('hit_count', 0)
                self._stats.miss_count = stats.get('miss_count', 0)
                self._stats.eviction_count = stats.get('eviction_count', 0)
                self._stats.total_requests = stats.get('total_requests', 0)

            # 恢复缓存条目
            if 'entries' in cache_data:
                for key, entry_data in cache_data['entries'].items():
                    try:
                        entry = CacheEntry(
                            key=key,
                            value=entry_data['value'],
                            created_at=datetime.fromisoformat(entry_data['created_at']),
                            last_accessed=datetime.fromisoformat(entry_data['last_accessed']),
                            access_count=entry_data.get('access_count', 0),
                            ttl=entry_data.get('ttl'),
                            size=self._calculate_size(entry_data['value']),
                            metadata=entry_data.get('metadata', {})
                        )

                        # 跳过过期条目
                        if not entry.is_expired():
                            self._cache[key] = entry
                            self._stats.entry_count += 1
                            self._stats.total_size += entry.size

                    except Exception as e:
                        self._logger.warning(f"跳过无效缓存条目: {key}", exception=e)

            self._logger.info(f"缓存已从文件恢复: {len(self._cache)} 个条目")

        except Exception as e:
            self._logger.error(f"加载缓存失败: {self._persistence_path}", exception=e)

    def shutdown(self):
        """关闭缓存服务"""
        self._stop_cleanup.set()

        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=5)

        # 最后保存缓存
        if self._persistence_path:
            self._save_cache()

        self._logger.info("缓存服务已关闭")


# 全局缓存服务实例
_cache_service_instance: Optional[CacheService] = None
_cache_service_lock = threading.Lock()


def get_cache_service() -> CacheService:
    """获取缓存服务单例实例"""
    global _cache_service_instance

    if _cache_service_instance is None:
        with _cache_service_lock:
            if _cache_service_instance is None:
                _cache_service_instance = CacheService(
                    max_size=1000,
                    max_memory_mb=100,
                    strategy=CacheStrategy.LRU,
                    default_ttl=3600,  # 1小时
                    persistence_path="logs/cache_data.json"
                )

    return _cache_service_instance


def create_cache_service(**kwargs) -> CacheService:
    """创建新的缓存服务实例"""
    return CacheService(**kwargs)
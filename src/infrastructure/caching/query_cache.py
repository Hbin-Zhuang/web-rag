"""
查询缓存实现
专门用于缓存RAG查询结果、对话上下文和检索结果
"""

import hashlib
import threading
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from .cache_service import CacheService, get_cache_service
from ..logging.logging_service import get_logging_service, ILoggingService
from ..monitoring.metrics_service import get_metrics_service


@dataclass
class QueryCacheEntry:
    """查询缓存条目"""
    query_hash: str
    original_query: str
    response: str
    retrieved_chunks: List[Dict[str, Any]]
    context_used: str
    model_name: str
    response_time: float
    cached_at: datetime
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'query_hash': self.query_hash,
            'original_query': self.original_query,
            'response': self.response,
            'retrieved_chunks': self.retrieved_chunks,
            'context_used': self.context_used,
            'model_name': self.model_name,
            'response_time': self.response_time,
            'cached_at': self.cached_at.isoformat(),
            'metadata': self.metadata
        }


class QueryCache:
    """查询缓存管理器"""

    def __init__(self,
                 cache_service: Optional[CacheService] = None,
                 logger_service: Optional[ILoggingService] = None):
        """初始化查询缓存

        Args:
            cache_service: 底层缓存服务
            logger_service: 日志服务
        """
        self._cache = cache_service or get_cache_service()
        self._logger = logger_service or get_logging_service()
        self._metrics = get_metrics_service()
        self._lock = threading.RLock()

        # 缓存前缀
        self._query_prefix = "query:"
        self._retrieval_prefix = "retrieval:"
        self._context_prefix = "context:"

        self._logger.info("查询缓存初始化完成")

    def get_query_hash(self,
                      query: str,
                      model_name: str = "",
                      context: str = "",
                      extra_params: Optional[Dict] = None) -> str:
        """计算查询哈希值

        Args:
            query: 查询文本
            model_name: 模型名称
            context: 上下文
            extra_params: 额外参数

        Returns:
            查询哈希值
        """
        hasher = hashlib.sha256()

        # 规范化查询文本
        normalized_query = query.strip().lower()
        hasher.update(normalized_query.encode('utf-8'))

        # 添加模型名称
        hasher.update(model_name.encode('utf-8'))

        # 添加上下文哈希（避免上下文过长）
        if context:
            context_hash = hashlib.md5(context.encode('utf-8')).hexdigest()
            hasher.update(context_hash.encode('utf-8'))

        # 添加额外参数
        if extra_params:
            import json
            params_str = json.dumps(extra_params, sort_keys=True)
            hasher.update(params_str.encode('utf-8'))

        return hasher.hexdigest()

    def cache_query_result(self,
                          query: str,
                          response: str,
                          retrieved_chunks: List[Dict[str, Any]],
                          context_used: str,
                          model_name: str,
                          response_time: float,
                          metadata: Optional[Dict[str, Any]] = None,
                          ttl: Optional[int] = None) -> bool:
        """缓存查询结果

        Args:
            query: 原始查询
            response: 模型响应
            retrieved_chunks: 检索到的文档块
            context_used: 使用的上下文
            model_name: 模型名称
            response_time: 响应时间
            metadata: 元数据
            ttl: 缓存生存时间

        Returns:
            是否成功缓存
        """
        with self._lock:
            try:
                # 计算查询哈希
                query_hash = self.get_query_hash(query, model_name, context_used)

                # 创建缓存条目
                cache_entry = QueryCacheEntry(
                    query_hash=query_hash,
                    original_query=query,
                    response=response,
                    retrieved_chunks=retrieved_chunks,
                    context_used=context_used,
                    model_name=model_name,
                    response_time=response_time,
                    cached_at=datetime.now(),
                    metadata=metadata or {}
                )

                # 缓存查询结果
                query_key = f"{self._query_prefix}{query_hash}"
                success = self._cache.put(
                    query_key,
                    cache_entry.to_dict(),
                    ttl=ttl or 1800  # 默认30分钟
                )

                if success:
                    # 单独缓存检索结果（用于相似查询的快速检索）
                    retrieval_key = f"{self._retrieval_prefix}{query_hash}"
                    self._cache.put(
                        retrieval_key,
                        {
                            'chunks': retrieved_chunks,
                            'context': context_used,
                            'query': query
                        },
                        ttl=ttl or 1800
                    )

                    # 记录指标
                    self._metrics.increment_counter('query_cache_put_total', {
                        'model': model_name,
                        'query_length_bucket': self._get_length_bucket(len(query)),
                        'chunks_count': str(len(retrieved_chunks))
                    })

                    self._metrics.record_metric('query_cache_response_length', len(response))
                    self._metrics.record_metric('query_cache_chunks_count', len(retrieved_chunks))
                    self._metrics.record_histogram('query_cache_response_time', response_time)

                    self._logger.debug(f"查询结果缓存成功: 哈希 {query_hash[:8]}, "
                                     f"响应长度: {len(response)}, 检索块: {len(retrieved_chunks)}")

                return success

            except Exception as e:
                self._logger.error(f"缓存查询结果失败: {query[:50]}...", exception=e)
                return False

    def get_query_result(self,
                        query: str,
                        model_name: str = "",
                        context: str = "",
                        extra_params: Optional[Dict] = None) -> Optional[QueryCacheEntry]:
        """获取缓存的查询结果

        Args:
            query: 查询文本
            model_name: 模型名称
            context: 上下文
            extra_params: 额外参数

        Returns:
            查询缓存条目或None
        """
        with self._lock:
            try:
                # 计算查询哈希
                query_hash = self.get_query_hash(query, model_name, context, extra_params)

                # 获取缓存数据
                query_key = f"{self._query_prefix}{query_hash}"
                cached_data = self._cache.get(query_key)

                if cached_data:
                    # 记录缓存命中
                    self._metrics.increment_counter('query_cache_hit_total', {
                        'model': model_name,
                        'query_length_bucket': self._get_length_bucket(len(query))
                    })

                    # 重构缓存条目
                    entry = QueryCacheEntry(
                        query_hash=cached_data['query_hash'],
                        original_query=cached_data['original_query'],
                        response=cached_data['response'],
                        retrieved_chunks=cached_data['retrieved_chunks'],
                        context_used=cached_data['context_used'],
                        model_name=cached_data['model_name'],
                        response_time=cached_data['response_time'],
                        cached_at=datetime.fromisoformat(cached_data['cached_at']),
                        metadata=cached_data.get('metadata', {})
                    )

                    self._logger.debug(f"查询缓存命中: {query[:50]}..., 哈希: {query_hash[:8]}")
                    return entry
                else:
                    # 记录缓存未命中
                    self._metrics.increment_counter('query_cache_miss_total', {
                        'model': model_name,
                        'query_length_bucket': self._get_length_bucket(len(query))
                    })

                    self._logger.debug(f"查询缓存未命中: {query[:50]}...")
                    return None

            except Exception as e:
                self._logger.error(f"获取查询缓存失败: {query[:50]}...", exception=e)
                return None

    def get_similar_queries(self,
                           query: str,
                           limit: int = 5) -> List[Dict[str, Any]]:
        """获取相似的查询（简单实现）

        Args:
            query: 当前查询
            limit: 返回数量限制

        Returns:
            相似查询列表
        """
        # 这是一个简化实现，实际应用中可能需要更复杂的相似度计算
        try:
            # 获取缓存统计以了解有哪些查询
            # 这里返回空列表，实际实现需要更复杂的逻辑
            return []

        except Exception as e:
            self._logger.error(f"获取相似查询失败: {query[:50]}...", exception=e)
            return []

    def cache_retrieval_result(self,
                              query: str,
                              retrieved_chunks: List[Dict[str, Any]],
                              retrieval_time: float,
                              ttl: Optional[int] = None) -> bool:
        """缓存检索结果

        Args:
            query: 查询文本
            retrieved_chunks: 检索到的文档块
            retrieval_time: 检索时间
            ttl: 缓存生存时间

        Returns:
            是否成功缓存
        """
        with self._lock:
            try:
                # 使用简化的哈希（只基于查询）
                query_hash = hashlib.sha256(query.strip().lower().encode('utf-8')).hexdigest()

                retrieval_key = f"{self._retrieval_prefix}{query_hash}"

                retrieval_data = {
                    'query': query,
                    'chunks': retrieved_chunks,
                    'retrieval_time': retrieval_time,
                    'cached_at': datetime.now().isoformat()
                }

                success = self._cache.put(
                    retrieval_key,
                    retrieval_data,
                    ttl=ttl or 3600  # 默认1小时
                )

                if success:
                    self._metrics.increment_counter('retrieval_cache_put_total')
                    self._metrics.record_metric('retrieval_cache_chunks_count', len(retrieved_chunks))
                    self._metrics.record_histogram('retrieval_cache_time', retrieval_time)

                return success

            except Exception as e:
                self._logger.error(f"缓存检索结果失败: {query[:50]}...", exception=e)
                return False

    def get_retrieval_result(self, query: str) -> Optional[Dict[str, Any]]:
        """获取缓存的检索结果

        Args:
            query: 查询文本

        Returns:
            检索结果或None
        """
        with self._lock:
            try:
                query_hash = hashlib.sha256(query.strip().lower().encode('utf-8')).hexdigest()
                retrieval_key = f"{self._retrieval_prefix}{query_hash}"

                cached_data = self._cache.get(retrieval_key)

                if cached_data:
                    self._metrics.increment_counter('retrieval_cache_hit_total')
                    self._logger.debug(f"检索缓存命中: {query[:50]}...")
                else:
                    self._metrics.increment_counter('retrieval_cache_miss_total')

                return cached_data

            except Exception as e:
                self._logger.error(f"获取检索缓存失败: {query[:50]}...", exception=e)
                return None

    def invalidate_query(self, query: str, model_name: str = "") -> bool:
        """使查询缓存失效

        Args:
            query: 查询文本
            model_name: 模型名称

        Returns:
            是否成功
        """
        with self._lock:
            try:
                query_hash = self.get_query_hash(query, model_name)

                query_key = f"{self._query_prefix}{query_hash}"
                retrieval_key = f"{self._retrieval_prefix}{query_hash}"

                query_deleted = self._cache.delete(query_key)
                retrieval_deleted = self._cache.delete(retrieval_key)

                if query_deleted or retrieval_deleted:
                    self._metrics.increment_counter('query_cache_invalidate_total')
                    self._logger.info(f"查询缓存已失效: {query[:50]}...")
                    return True

                return False

            except Exception as e:
                self._logger.error(f"使查询缓存失效失败: {query[:50]}...", exception=e)
                return False

    def get_cache_info(self) -> Dict[str, Any]:
        """获取查询缓存信息

        Returns:
            缓存信息字典
        """
        stats = self._cache.get_stats()

        return {
            'total_entries': stats.entry_count,
            'cache_size_mb': stats.total_size / (1024 * 1024),
            'hit_rate': stats.hit_rate,
            'total_requests': stats.total_requests,
            'cache_type': 'query_cache'
        }

    def _get_length_bucket(self, length: int) -> str:
        """获取长度分桶"""
        if length <= 50:
            return 'short'
        elif length <= 200:
            return 'medium'
        elif length <= 500:
            return 'long'
        else:
            return 'very_long'


# 全局查询缓存实例
_query_cache_instance: Optional[QueryCache] = None
_query_cache_lock = threading.Lock()


def get_query_cache() -> QueryCache:
    """获取查询缓存单例实例"""
    global _query_cache_instance

    if _query_cache_instance is None:
        with _query_cache_lock:
            if _query_cache_instance is None:
                _query_cache_instance = QueryCache()

    return _query_cache_instance
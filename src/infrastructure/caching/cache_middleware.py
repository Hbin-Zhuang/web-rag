"""
缓存中间件
提供装饰器和自动化缓存功能
"""

import functools
import time
import threading
from typing import Callable, Any, Dict, Optional, Union

from .cache_service import get_cache_service, CacheService
from .document_cache import get_document_cache, DocumentCache
from .query_cache import get_query_cache, QueryCache
from ..logging.logging_service import get_logging_service, ILoggingService
from ..monitoring.metrics_service import get_metrics_service


class CacheMiddleware:
    """缓存中间件类"""

    def __init__(self,
                 cache_service: Optional[CacheService] = None,
                 document_cache: Optional[DocumentCache] = None,
                 query_cache: Optional[QueryCache] = None,
                 logger_service: Optional[ILoggingService] = None):
        """初始化缓存中间件"""
        self._cache_service = cache_service or get_cache_service()
        self._document_cache = document_cache or get_document_cache()
        self._query_cache = query_cache or get_query_cache()
        self._logger = logger_service or get_logging_service()
        self._metrics = get_metrics_service()

        self._logger.info("缓存中间件初始化完成")


def cache_result(
    ttl: Optional[int] = None,
    key_func: Optional[Callable] = None,
    cache_type: str = "general"
):
    """通用结果缓存装饰器

    Args:
        ttl: 缓存生存时间（秒）
        key_func: 自定义键生成函数
        cache_type: 缓存类型标识
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            cache_service = get_cache_service()
            logger = get_logging_service()
            metrics = get_metrics_service()

            # 生成缓存键
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # 默认键生成策略
                import hashlib
                key_parts = [func.__name__]
                key_parts.extend(str(arg) for arg in args)
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))

                key_str = "|".join(key_parts)
                cache_key = f"{cache_type}:{hashlib.md5(key_str.encode()).hexdigest()}"

            # 尝试从缓存获取
            start_time = time.time()
            cached_result = cache_service.get(cache_key)

            if cached_result is not None:
                # 缓存命中
                cache_time = time.time() - start_time

                metrics.increment_counter('cache_middleware_hit_total', {
                    'function': func.__name__,
                    'cache_type': cache_type
                })
                metrics.record_histogram('cache_middleware_retrieval_time', cache_time)

                logger.debug(f"缓存命中: {func.__name__}, 键: {cache_key[:16]}...")
                return cached_result

            # 缓存未命中，执行函数
            metrics.increment_counter('cache_middleware_miss_total', {
                'function': func.__name__,
                'cache_type': cache_type
            })

            try:
                # 执行原函数
                execution_start = time.time()
                result = func(*args, **kwargs)
                execution_time = time.time() - execution_start

                # 缓存结果
                cache_success = cache_service.put(cache_key, result, ttl=ttl)

                if cache_success:
                    metrics.increment_counter('cache_middleware_store_success_total', {
                        'function': func.__name__,
                        'cache_type': cache_type
                    })
                else:
                    metrics.increment_counter('cache_middleware_store_failure_total', {
                        'function': func.__name__,
                        'cache_type': cache_type
                    })

                metrics.record_histogram('cache_middleware_execution_time', execution_time)

                logger.debug(f"函数执行并缓存: {func.__name__}, 执行时间: {execution_time:.3f}s")

                return result

            except Exception as e:
                logger.error(f"缓存装饰器执行失败: {func.__name__}", exception=e)
                raise

        return wrapper
    return decorator


def cache_embedding(ttl: int = 3600):
    """嵌入向量缓存装饰器

    Args:
        ttl: 缓存生存时间，默认1小时
    """
    def key_generator(*args, **kwargs):
        """为嵌入生成特殊的键"""
        import hashlib

        # 通常第一个参数是文本
        text = str(args[0]) if args else ""
        model = kwargs.get('model', 'default')

        key_str = f"embedding:{model}:{text}"
        return f"emb:{hashlib.sha256(key_str.encode()).hexdigest()}"

    return cache_result(ttl=ttl, key_func=key_generator, cache_type="embedding")


def cache_with_ttl(ttl: int):
    """简化的TTL缓存装饰器

    Args:
        ttl: 缓存生存时间（秒）
    """
    return cache_result(ttl=ttl, cache_type="ttl")


def cache_rag_query(ttl: int = 3600, key_prefix: str = "rag_query"):
    """RAG查询缓存装饰器

    Args:
        ttl: 缓存过期时间（秒）
        key_prefix: 缓存键前缀
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            cache_service = get_cache_service()

            # 生成缓存键
            query_text = kwargs.get('query', args[0] if args else '')
            cache_key = f"{key_prefix}:{hash(str(query_text))}"

            # 尝试从缓存获取
            cached_result = cache_service.get(cache_key)
            if cached_result is not None:
                return cached_result

            # 执行函数并缓存结果
            result = func(*args, **kwargs)
            cache_service.set(cache_key, result, ttl)

            return result
        return wrapper
    return decorator


def cache_document_processing(ttl: int = 7200, key_prefix: str = "doc_process"):
    """文档处理缓存装饰器

    Args:
        ttl: 缓存过期时间（秒）
        key_prefix: 缓存键前缀
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            cache_service = get_cache_service()

            # 生成缓存键
            doc_id = kwargs.get('document_id', args[0] if args else '')
            cache_key = f"{key_prefix}:{doc_id}"

            # 尝试从缓存获取
            cached_result = cache_service.get(cache_key)
            if cached_result is not None:
                return cached_result

            # 执行函数并缓存结果
            result = func(*args, **kwargs)
            cache_service.set(cache_key, result, ttl)

            return result
        return wrapper
    return decorator


# 全局缓存中间件实例
_cache_middleware_instance: Optional[CacheMiddleware] = None
_cache_middleware_lock = threading.Lock()


def get_cache_middleware() -> CacheMiddleware:
    """获取缓存中间件单例实例"""
    global _cache_middleware_instance

    if _cache_middleware_instance is None:
        with _cache_middleware_lock:
            if _cache_middleware_instance is None:
                _cache_middleware_instance = CacheMiddleware()

    return _cache_middleware_instance
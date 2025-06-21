"""
缓存模块
提供多级缓存管理和优化功能
"""

from .cache_service import (
    CacheService,
    CacheStrategy,
    CacheEntry,
    CacheStats,
    get_cache_service
)

from .document_cache import (
    DocumentCache,
    DocumentCacheEntry,
    get_document_cache
)

from .query_cache import (
    QueryCache,
    QueryCacheEntry,
    get_query_cache
)

from .cache_middleware import (
    cache_result,
    cache_embedding,
    cache_with_ttl,
    cache_rag_query,
    cache_document_processing,
    CacheMiddleware,
    get_cache_middleware
)

__all__ = [
    # 核心缓存服务
    'CacheService',
    'CacheStrategy',
    'CacheEntry',
    'CacheStats',
    'get_cache_service',

    # 文档缓存
    'DocumentCache',
    'DocumentCacheEntry',
    'get_document_cache',

    # 查询缓存
    'QueryCache',
    'QueryCacheEntry',
    'get_query_cache',

    # 缓存中间件
    'cache_result',
    'cache_embedding',
    'cache_with_ttl',
    'cache_rag_query',
    'cache_document_processing',
    'CacheMiddleware',
    'get_cache_middleware'
]
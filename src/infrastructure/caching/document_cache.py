"""
文档缓存实现
"""

import threading
from typing import Dict, Any, Optional

from .cache_service import get_cache_service


class DocumentCacheEntry:
    """文档缓存条目"""
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class DocumentCache:
    """文档缓存管理器"""

    def __init__(self, cache_service=None):
        self._cache = cache_service or get_cache_service()

    def get_document(self, file_path: str) -> Optional[DocumentCacheEntry]:
        """获取缓存的文档"""
        return self._cache.get(f"doc:{file_path}")

    def cache_document(self, file_path: str, **kwargs) -> bool:
        """缓存文档"""
        entry = DocumentCacheEntry(**kwargs)
        return self._cache.put(f"doc:{file_path}", entry)


_document_cache_instance: Optional[DocumentCache] = None
_document_cache_lock = threading.Lock()


def get_document_cache() -> DocumentCache:
    """获取文档缓存单例实例"""
    global _document_cache_instance

    if _document_cache_instance is None:
        with _document_cache_lock:
            if _document_cache_instance is None:
                _document_cache_instance = DocumentCache()

    return _document_cache_instance

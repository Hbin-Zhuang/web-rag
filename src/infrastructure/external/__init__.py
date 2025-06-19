"""外部服务抽象模块"""

from .interfaces import (
    # 模型相关
    ModelStatus,
    ModelInfo,
    ChatMessage,
    ChatResponse,
    EmbeddingResult,
    DocumentChunk,
    SearchResult,

    # 服务接口
    ILLMService,
    IEmbeddingService,
    IVectorStoreService,
    IDocumentProcessorService,
    IMemoryService,
    IRateLimiterService,
    IHealthCheckService,
    IMetricsService,

    # 异常类
    ExternalServiceException,
    LLMServiceException,
    EmbeddingServiceException,
    VectorStoreException,
    RateLimitException,
    HealthCheckException
)

__all__ = [
    'ModelStatus',
    'ModelInfo',
    'ChatMessage',
    'ChatResponse',
    'EmbeddingResult',
    'DocumentChunk',
    'SearchResult',
    'ILLMService',
    'IEmbeddingService',
    'IVectorStoreService',
    'IDocumentProcessorService',
    'IMemoryService',
    'IRateLimiterService',
    'IHealthCheckService',
    'IMetricsService',
    'ExternalServiceException',
    'LLMServiceException',
    'EmbeddingServiceException',
    'VectorStoreException',
    'RateLimitException',
    'HealthCheckException'
]
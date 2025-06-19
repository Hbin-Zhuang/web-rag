"""
基础设施层
提供统一的配置管理、日志服务、依赖注入和外部服务抽象
"""

# 配置服务
from .config.configuration_service import (
    IConfigurationService,
    ConfigurationService,
    Environment,
    ConfigurationValidationResult,
    get_config_service,
    create_config_service
)

# 日志服务
from .logging.logging_service import (
    ILoggingService,
    LoggingService,
    LogLevel,
    PerformanceLogger,
    performance_monitor,
    get_logging_service,
    create_logging_service
)

# 依赖注入
from .di.container import (
    IDependencyContainer,
    DependencyContainer,
    ServiceLifetime,
    ServiceDescriptor,
    ServiceScope,
    autowired,
    get_container,
    register_singleton,
    register_transient,
    register_scoped,
    register_instance,
    resolve,
    try_resolve
)

# 外部服务接口
from .external.interfaces import (
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

# 基础设施工厂
from .factories.infrastructure_factory import (
    InfrastructureFactory,
    get_infrastructure_factory,
    create_infrastructure_factory,
    initialize_infrastructure,
    get_service,
    get_config,
    get_logger,
    get_container as get_di_container
)

__all__ = [
    # 配置服务
    'IConfigurationService',
    'ConfigurationService',
    'Environment',
    'ConfigurationValidationResult',
    'get_config_service',
    'create_config_service',

    # 日志服务
    'ILoggingService',
    'LoggingService',
    'LogLevel',
    'PerformanceLogger',
    'performance_monitor',
    'get_logging_service',
    'create_logging_service',

    # 依赖注入
    'IDependencyContainer',
    'DependencyContainer',
    'ServiceLifetime',
    'ServiceDescriptor',
    'ServiceScope',
    'autowired',
    'get_container',
    'register_singleton',
    'register_transient',
    'register_scoped',
    'register_instance',
    'resolve',
    'try_resolve',

    # 外部服务接口
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
    'HealthCheckException',

    # 基础设施工厂
    'InfrastructureFactory',
    'get_infrastructure_factory',
    'create_infrastructure_factory',
    'initialize_infrastructure',
    'get_service',
    'get_config',
    'get_logger',
    'get_di_container'
]
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

# 配置迁移适配器
from .config.config_migration_adapter import (
    ConfigMigrationAdapter,
    get_legacy_config
)

# 日志服务
from .logging.logging_service import (
    ILoggingService,
    LoggingService,
    LogLevel,
    PerformanceLogger,
    performance_monitor,
    get_logging_service,
    create_logging_service,
    get_logger,
    setup_logging
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

# 工具服务
from .utilities import (
    IUtilityService,
    UtilityService,
    ProgressTracker,
    get_utility_service
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

# 便捷函数
def get_legacy_config_instance():
    """获取兼容性配置实例"""
    return get_legacy_config()

def get_utility():
    """获取工具服务实例"""
    return get_utility_service()

__all__ = [
    # 配置服务
    'IConfigurationService',
    'ConfigurationService',
    'Environment',
    'ConfigurationValidationResult',
    'get_config_service',
    'create_config_service',
    'get_config',

    # 配置迁移适配器
    'ConfigMigrationAdapter',
    'get_legacy_config',
    'get_legacy_config_instance',

    # 日志服务
    'ILoggingService',
    'LoggingService',
    'LogLevel',
    'PerformanceLogger',
    'performance_monitor',
    'get_logging_service',
    'create_logging_service',
    'get_logger',
    'setup_logging',

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

    # 工具服务
    'IUtilityService',
    'UtilityService',
    'ProgressTracker',
    'get_utility_service',
    'get_utility',

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
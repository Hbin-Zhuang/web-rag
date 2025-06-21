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

# 监控服务
from .monitoring import (
    MetricsService,
    MetricType,
    MetricValue,
    TimeSeriesData,
    get_metrics_service,
    HealthCheckService,
    HealthStatus,
    ComponentHealth,
    SystemHealth,
    get_health_check_service,
    PerformanceDashboard,
    create_performance_dashboard,
    MonitoringMiddleware,
    monitor_performance,
    track_metrics,
    RAGMetricsTracker,
    get_rag_metrics_tracker
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

# 缓存服务
from .caching import (
    CacheService,
    CacheStrategy,
    CacheEntry,
    CacheStats,
    get_cache_service,
    DocumentCache,
    DocumentCacheEntry,
    get_document_cache,
    QueryCache,
    QueryCacheEntry,
    get_query_cache,
    cache_result,
    cache_embedding,
    cache_with_ttl,
    cache_rag_query,
    cache_document_processing,
    CacheMiddleware,
    get_cache_middleware
)

# 扩展模块 (阶段7新增)
from .extensions import (
    PluginManager,
    ExtensionPointRegistry,
    RAGExtensionPoints,
    AutoScaler,
    get_plugin_manager,
    get_extension_registry,
    get_rag_extensions,
    get_auto_scaler
)

# 生产配置 (阶段7新增)
from .config.production_config import (
    ProductionConfigManager,
    SecurityConfig,
    PerformanceConfig,
    MonitoringConfig,
    get_production_config
)

# 预定义__all__
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

    # 监控服务
    'MetricsService',
    'MetricType',
    'MetricValue',
    'TimeSeriesData',
    'get_metrics_service',
    'HealthCheckService',
    'HealthStatus',
    'ComponentHealth',
    'SystemHealth',
    'get_health_check_service',
    'PerformanceDashboard',
    'create_performance_dashboard',
    'MonitoringMiddleware',
    'monitor_performance',
    'track_metrics',
    'RAGMetricsTracker',
    'get_rag_metrics_tracker',

    # 基础设施工厂
    'InfrastructureFactory',
    'get_infrastructure_factory',
    'create_infrastructure_factory',
    'initialize_infrastructure',
    'get_service',
    'get_config',
    'get_logger',
    'get_di_container',

    # 快速访问函数
    'get_memory_service',
    'get_conversation_manager',

    # 缓存服务
    'CacheService',
    'CacheStrategy',
    'CacheEntry',
    'CacheStats',
    'get_cache_service',
    'DocumentCache',
    'DocumentCacheEntry',
    'get_document_cache',
    'QueryCache',
    'QueryCacheEntry',
    'get_query_cache',
    'cache_result',
    'cache_embedding',
    'cache_with_ttl',
    'cache_rag_query',
    'cache_document_processing',
    'CacheMiddleware',
    'get_cache_middleware',

    # 扩展模块
    'PluginManager',
    'ExtensionPointRegistry',
    'RAGExtensionPoints',
    'AutoScaler',
    'get_plugin_manager',
    'get_extension_registry',
    'get_rag_extensions',
    'get_auto_scaler',

    # 生产配置
    'ProductionConfigManager',
    'SecurityConfig',
    'PerformanceConfig',
    'MonitoringConfig',
    'get_production_config'
]

# 应用服务层导出
_services_imported = False
MemoryService = None
ConversationManager = None
ChatService = None
DocumentService = None

try:
    from ..application.services.memory_service import MemoryService
    from ..application.services.legacy_memory_adapter import ConversationManager
    from ..application.services.chat_service import ChatService
    from ..application.services.document_service import DocumentService

    # 添加到__all__
    __all__.extend([
        'MemoryService',
        'ConversationManager',
        'ChatService',
        'DocumentService'
    ])

    _services_imported = True

except ImportError as e:
    # 延迟获取logger，避免循环导入
    try:
        logger = get_logger()
        logger.warning("部分应用服务导入失败", extra={"error": str(e)})
    except:
        print(f"部分应用服务导入失败: {e}")

    _services_imported = False

# 便捷函数
def get_legacy_config_instance():
    """获取兼容性配置实例"""
    return get_legacy_config()

def get_utility():
    """获取工具服务实例"""
    return get_utility_service()

# 快速访问函数
def get_memory_service(**kwargs):
    """获取内存服务实例"""
    if _services_imported and MemoryService:
        return MemoryService(**kwargs)
    else:
        raise ImportError("MemoryService not available")

def get_conversation_manager(**kwargs):
    """获取对话管理器实例（兼容旧接口）"""
    if _services_imported and ConversationManager:
        return ConversationManager(**kwargs)
    else:
        raise ImportError("ConversationManager not available")
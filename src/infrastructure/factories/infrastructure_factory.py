"""
基础设施工厂
负责统一创建和配置所有基础设施组件
"""

from typing import Optional, Type, TypeVar, Dict, Any
from ..config.configuration_service import (
    IConfigurationService,
    ConfigurationService,
    Environment
)
from ..logging.logging_service import (
    ILoggingService,
    LoggingService,
    create_logging_service
)
from ..di.container import (
    IDependencyContainer,
    DependencyContainer,
    ServiceLifetime
)
from ..external.interfaces import (
    ILLMService,
    IEmbeddingService,
    IVectorStoreService,
    IDocumentProcessorService,
    IMemoryService,
    IRateLimiterService,
    IHealthCheckService,
    IMetricsService
)

T = TypeVar('T')


class InfrastructureFactory:
    """基础设施工厂类"""

    def __init__(self):
        """初始化基础设施工厂"""
        self._container: Optional[DependencyContainer] = None
        self._config_service: Optional[IConfigurationService] = None
        self._logging_service: Optional[ILoggingService] = None
        self._is_initialized = False

    def initialize(self, environment: Optional[Environment] = None) -> None:
        """初始化基础设施

        Args:
            environment: 运行环境，如果不指定则自动检测
        """
        if self._is_initialized:
            return

        # 1. 创建配置服务
        self._config_service = ConfigurationService(environment)

        # 2. 创建日志服务
        self._logging_service = create_logging_service(self._config_service)

        # 3. 创建依赖注入容器
        self._container = DependencyContainer()

        # 4. 注册核心服务
        self._register_core_services()

        # 5. 验证配置
        self._validate_configuration()

        self._is_initialized = True
        self._logging_service.info("基础设施初始化完成")

    def _register_core_services(self) -> None:
        """注册核心服务"""
        # 注册配置服务
        self._container.register_instance(
            IConfigurationService,
            self._config_service
        )

        # 注册日志服务
        self._container.register_instance(
            ILoggingService,
            self._logging_service
        )

        # 注册容器自身
        self._container.register_instance(
            IDependencyContainer,
            self._container
        )

    def _validate_configuration(self) -> None:
        """验证配置"""
        validation_result = self._config_service.validate_configuration()

        if not validation_result.is_valid:
            error_msg = "配置验证失败:\n" + "\n".join(validation_result.errors)
            self._logging_service.error(error_msg)
            raise ValueError(error_msg)

        if validation_result.warnings:
            warning_msg = "配置警告:\n" + "\n".join(validation_result.warnings)
            self._logging_service.warning(warning_msg)

    def get_container(self) -> IDependencyContainer:
        """获取依赖注入容器"""
        if not self._is_initialized:
            self.initialize()
        return self._container

    def get_config_service(self) -> IConfigurationService:
        """获取配置服务"""
        if not self._is_initialized:
            self.initialize()
        return self._config_service

    def get_logging_service(self) -> ILoggingService:
        """获取日志服务"""
        if not self._is_initialized:
            self.initialize()
        return self._logging_service

    def register_llm_service(self,
                            service_type: Type[ILLMService],
                            implementation_type: Type[ILLMService],
                            lifetime: ServiceLifetime = ServiceLifetime.SINGLETON) -> None:
        """注册LLM服务"""
        if not self._is_initialized:
            self.initialize()

        if lifetime == ServiceLifetime.SINGLETON:
            self._container.register_singleton(service_type, implementation_type)
        elif lifetime == ServiceLifetime.TRANSIENT:
            self._container.register_transient(service_type, implementation_type)
        else:
            self._container.register_scoped(service_type, implementation_type)

        self._logging_service.info(
            f"已注册LLM服务: {service_type.__name__} -> {implementation_type.__name__} ({lifetime.value})"
        )

    def register_embedding_service(self,
                                  service_type: Type[IEmbeddingService],
                                  implementation_type: Type[IEmbeddingService],
                                  lifetime: ServiceLifetime = ServiceLifetime.SINGLETON) -> None:
        """注册嵌入服务"""
        if not self._is_initialized:
            self.initialize()

        if lifetime == ServiceLifetime.SINGLETON:
            self._container.register_singleton(service_type, implementation_type)
        elif lifetime == ServiceLifetime.TRANSIENT:
            self._container.register_transient(service_type, implementation_type)
        else:
            self._container.register_scoped(service_type, implementation_type)

        self._logging_service.info(
            f"已注册嵌入服务: {service_type.__name__} -> {implementation_type.__name__} ({lifetime.value})"
        )

    def register_vector_store_service(self,
                                     service_type: Type[IVectorStoreService],
                                     implementation_type: Type[IVectorStoreService],
                                     lifetime: ServiceLifetime = ServiceLifetime.SINGLETON) -> None:
        """注册向量存储服务"""
        if not self._is_initialized:
            self.initialize()

        if lifetime == ServiceLifetime.SINGLETON:
            self._container.register_singleton(service_type, implementation_type)
        elif lifetime == ServiceLifetime.TRANSIENT:
            self._container.register_transient(service_type, implementation_type)
        else:
            self._container.register_scoped(service_type, implementation_type)

        self._logging_service.info(
            f"已注册向量存储服务: {service_type.__name__} -> {implementation_type.__name__} ({lifetime.value})"
        )

    def register_document_processor_service(self,
                                           service_type: Type[IDocumentProcessorService],
                                           implementation_type: Type[IDocumentProcessorService],
                                           lifetime: ServiceLifetime = ServiceLifetime.SINGLETON) -> None:
        """注册文档处理服务"""
        if not self._is_initialized:
            self.initialize()

        if lifetime == ServiceLifetime.SINGLETON:
            self._container.register_singleton(service_type, implementation_type)
        elif lifetime == ServiceLifetime.TRANSIENT:
            self._container.register_transient(service_type, implementation_type)
        else:
            self._container.register_scoped(service_type, implementation_type)

        self._logging_service.info(
            f"已注册文档处理服务: {service_type.__name__} -> {implementation_type.__name__} ({lifetime.value})"
        )

    def register_memory_service(self,
                               service_type: Type[IMemoryService],
                               implementation_type: Type[IMemoryService],
                               lifetime: ServiceLifetime = ServiceLifetime.SINGLETON) -> None:
        """注册内存服务"""
        if not self._is_initialized:
            self.initialize()

        if lifetime == ServiceLifetime.SINGLETON:
            self._container.register_singleton(service_type, implementation_type)
        elif lifetime == ServiceLifetime.TRANSIENT:
            self._container.register_transient(service_type, implementation_type)
        else:
            self._container.register_scoped(service_type, implementation_type)

        self._logging_service.info(
            f"已注册内存服务: {service_type.__name__} -> {implementation_type.__name__} ({lifetime.value})"
        )

    def register_rate_limiter_service(self,
                                     service_type: Type[IRateLimiterService],
                                     implementation_type: Type[IRateLimiterService],
                                     lifetime: ServiceLifetime = ServiceLifetime.SINGLETON) -> None:
        """注册限流服务"""
        if not self._is_initialized:
            self.initialize()

        if lifetime == ServiceLifetime.SINGLETON:
            self._container.register_singleton(service_type, implementation_type)
        elif lifetime == ServiceLifetime.TRANSIENT:
            self._container.register_transient(service_type, implementation_type)
        else:
            self._container.register_scoped(service_type, implementation_type)

        self._logging_service.info(
            f"已注册限流服务: {service_type.__name__} -> {implementation_type.__name__} ({lifetime.value})"
        )

    def register_health_check_service(self,
                                     service_type: Type[IHealthCheckService],
                                     implementation_type: Type[IHealthCheckService],
                                     lifetime: ServiceLifetime = ServiceLifetime.SINGLETON) -> None:
        """注册健康检查服务"""
        if not self._is_initialized:
            self.initialize()

        if lifetime == ServiceLifetime.SINGLETON:
            self._container.register_singleton(service_type, implementation_type)
        elif lifetime == ServiceLifetime.TRANSIENT:
            self._container.register_transient(service_type, implementation_type)
        else:
            self._container.register_scoped(service_type, implementation_type)

        self._logging_service.info(
            f"已注册健康检查服务: {service_type.__name__} -> {implementation_type.__name__} ({lifetime.value})"
        )

    def register_metrics_service(self,
                                service_type: Type[IMetricsService],
                                implementation_type: Type[IMetricsService],
                                lifetime: ServiceLifetime = ServiceLifetime.SINGLETON) -> None:
        """注册指标服务"""
        if not self._is_initialized:
            self.initialize()

        if lifetime == ServiceLifetime.SINGLETON:
            self._container.register_singleton(service_type, implementation_type)
        elif lifetime == ServiceLifetime.TRANSIENT:
            self._container.register_transient(service_type, implementation_type)
        else:
            self._container.register_scoped(service_type, implementation_type)

        self._logging_service.info(
            f"已注册指标服务: {service_type.__name__} -> {implementation_type.__name__} ({lifetime.value})"
        )

    def register_custom_service(self,
                               service_type: Type[T],
                               implementation_type: Type[T],
                               lifetime: ServiceLifetime = ServiceLifetime.TRANSIENT) -> None:
        """注册自定义服务"""
        if not self._is_initialized:
            self.initialize()

        if lifetime == ServiceLifetime.SINGLETON:
            self._container.register_singleton(service_type, implementation_type)
        elif lifetime == ServiceLifetime.TRANSIENT:
            self._container.register_transient(service_type, implementation_type)
        else:
            self._container.register_scoped(service_type, implementation_type)

        self._logging_service.info(
            f"已注册自定义服务: {service_type.__name__} -> {implementation_type.__name__} ({lifetime.value})"
        )

    def get_service_info(self) -> Dict[str, Any]:
        """获取服务注册信息"""
        if not self._is_initialized:
            self.initialize()

        return {
            "environment": self._config_service.get_environment().value,
            "config_validation": self._config_service.validate_configuration(),
            "services": self._container.get_service_info(),
            "is_initialized": self._is_initialized
        }

    def reset(self) -> None:
        """重置工厂（主要用于测试）"""
        self._container = None
        self._config_service = None
        self._logging_service = None
        self._is_initialized = False


# 创建全局基础设施工厂单例
_infrastructure_factory: Optional[InfrastructureFactory] = None


def get_infrastructure_factory() -> InfrastructureFactory:
    """获取基础设施工厂单例"""
    global _infrastructure_factory
    if _infrastructure_factory is None:
        _infrastructure_factory = InfrastructureFactory()
    return _infrastructure_factory


def create_infrastructure_factory() -> InfrastructureFactory:
    """创建新的基础设施工厂（主要用于测试）"""
    return InfrastructureFactory()


# 快捷方法
def initialize_infrastructure(environment: Optional[Environment] = None) -> None:
    """初始化基础设施"""
    get_infrastructure_factory().initialize(environment)


def get_service(service_type: Type[T]) -> T:
    """从基础设施工厂获取服务"""
    factory = get_infrastructure_factory()
    return factory.get_container().resolve(service_type)


def get_config() -> IConfigurationService:
    """获取配置服务"""
    return get_infrastructure_factory().get_config_service()


def get_logger() -> ILoggingService:
    """获取日志服务"""
    return get_infrastructure_factory().get_logging_service()


def get_container() -> IDependencyContainer:
    """获取依赖注入容器"""
    return get_infrastructure_factory().get_container()
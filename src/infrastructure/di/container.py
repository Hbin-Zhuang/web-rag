"""
依赖注入容器
提供统一的依赖管理和对象生命周期控制
"""

import inspect
from abc import ABC, abstractmethod
from typing import Any, Dict, Type, TypeVar, Callable, Optional, List, Union
from dataclasses import dataclass
from enum import Enum
import threading


T = TypeVar('T')


class ServiceLifetime(Enum):
    """服务生命周期枚举"""
    SINGLETON = "singleton"    # 单例模式
    TRANSIENT = "transient"   # 每次创建新实例
    SCOPED = "scoped"         # 作用域内单例


@dataclass
class ServiceDescriptor:
    """服务描述符"""
    service_type: Type
    implementation_type: Optional[Type] = None
    factory: Optional[Callable] = None
    instance: Optional[Any] = None
    lifetime: ServiceLifetime = ServiceLifetime.TRANSIENT
    dependencies: Optional[List[Type]] = None


class IDependencyContainer(ABC):
    """依赖注入容器抽象接口"""

    @abstractmethod
    def register_singleton(self, service_type: Type[T], implementation_type: Type[T] = None, factory: Callable[[], T] = None) -> None:
        """注册单例服务"""
        pass

    @abstractmethod
    def register_transient(self, service_type: Type[T], implementation_type: Type[T] = None, factory: Callable[[], T] = None) -> None:
        """注册瞬态服务"""
        pass

    @abstractmethod
    def register_scoped(self, service_type: Type[T], implementation_type: Type[T] = None, factory: Callable[[], T] = None) -> None:
        """注册作用域服务"""
        pass

    @abstractmethod
    def register_instance(self, service_type: Type[T], instance: T) -> None:
        """注册实例"""
        pass

    @abstractmethod
    def resolve(self, service_type: Type[T]) -> T:
        """解析服务"""
        pass

    @abstractmethod
    def try_resolve(self, service_type: Type[T]) -> Optional[T]:
        """尝试解析服务，失败返回None"""
        pass


class DependencyContainer(IDependencyContainer):
    """依赖注入容器实现类"""

    def __init__(self):
        """初始化依赖注入容器"""
        self._services: Dict[Type, ServiceDescriptor] = {}
        self._singletons: Dict[Type, Any] = {}
        self._scoped_instances: Dict[Type, Any] = {}
        self._lock = threading.RLock()
        self._resolving_stack: List[Type] = []  # 用于检测循环依赖

    def register_singleton(self, service_type: Type[T], implementation_type: Type[T] = None, factory: Callable[[], T] = None) -> None:
        """注册单例服务"""
        with self._lock:
            descriptor = ServiceDescriptor(
                service_type=service_type,
                implementation_type=implementation_type or service_type,
                factory=factory,
                lifetime=ServiceLifetime.SINGLETON
            )
            self._services[service_type] = descriptor

    def register_transient(self, service_type: Type[T], implementation_type: Type[T] = None, factory: Callable[[], T] = None) -> None:
        """注册瞬态服务"""
        with self._lock:
            descriptor = ServiceDescriptor(
                service_type=service_type,
                implementation_type=implementation_type or service_type,
                factory=factory,
                lifetime=ServiceLifetime.TRANSIENT
            )
            self._services[service_type] = descriptor

    def register_scoped(self, service_type: Type[T], implementation_type: Type[T] = None, factory: Callable[[], T] = None) -> None:
        """注册作用域服务"""
        with self._lock:
            descriptor = ServiceDescriptor(
                service_type=service_type,
                implementation_type=implementation_type or service_type,
                factory=factory,
                lifetime=ServiceLifetime.SCOPED
            )
            self._services[service_type] = descriptor

    def register_instance(self, service_type: Type[T], instance: T) -> None:
        """注册实例"""
        with self._lock:
            descriptor = ServiceDescriptor(
                service_type=service_type,
                instance=instance,
                lifetime=ServiceLifetime.SINGLETON
            )
            self._services[service_type] = descriptor
            self._singletons[service_type] = instance

    def resolve(self, service_type: Type[T]) -> T:
        """解析服务"""
        instance = self.try_resolve(service_type)
        if instance is None:
            raise ValueError(f"服务类型 {service_type.__name__} 未注册")
        return instance

    def try_resolve(self, service_type: Type[T]) -> Optional[T]:
        """尝试解析服务，失败返回None"""
        with self._lock:
            # 检查循环依赖
            if service_type in self._resolving_stack:
                cycle_path = " -> ".join([t.__name__ for t in self._resolving_stack])
                raise ValueError(f"检测到循环依赖: {cycle_path} -> {service_type.__name__}")

            if service_type not in self._services:
                return None

            descriptor = self._services[service_type]

            # 检查是否已有实例
            if descriptor.lifetime == ServiceLifetime.SINGLETON:
                if service_type in self._singletons:
                    return self._singletons[service_type]
            elif descriptor.lifetime == ServiceLifetime.SCOPED:
                if service_type in self._scoped_instances:
                    return self._scoped_instances[service_type]

            # 创建新实例
            self._resolving_stack.append(service_type)
            try:
                instance = self._create_instance(descriptor)

                # 缓存实例
                if descriptor.lifetime == ServiceLifetime.SINGLETON:
                    self._singletons[service_type] = instance
                elif descriptor.lifetime == ServiceLifetime.SCOPED:
                    self._scoped_instances[service_type] = instance

                return instance
            finally:
                self._resolving_stack.remove(service_type)

    def _create_instance(self, descriptor: ServiceDescriptor) -> Any:
        """创建实例"""
        # 如果已有实例，直接返回
        if descriptor.instance is not None:
            return descriptor.instance

        # 如果有工厂方法，使用工厂方法创建
        if descriptor.factory is not None:
            return descriptor.factory()

        # 使用构造函数创建实例
        implementation_type = descriptor.implementation_type
        if implementation_type is None:
            raise ValueError(f"服务 {descriptor.service_type.__name__} 没有实现类型或工厂方法")

        # 获取构造函数参数
        constructor = implementation_type.__init__
        signature = inspect.signature(constructor)
        parameters = list(signature.parameters.values())[1:]  # 跳过self参数

        # 解析依赖
        args = []
        for param in parameters:
            if param.annotation == inspect.Parameter.empty:
                raise ValueError(f"构造函数参数 {param.name} 缺少类型注解")

            dependency = self.try_resolve(param.annotation)
            if dependency is None:
                if param.default != inspect.Parameter.empty:
                    # 使用默认值
                    continue
                else:
                    raise ValueError(f"无法解析依赖 {param.annotation.__name__}")

            args.append(dependency)

        # 创建实例
        return implementation_type(*args)

    def clear_scoped(self) -> None:
        """清除作用域实例"""
        with self._lock:
            self._scoped_instances.clear()

    def get_service_info(self) -> Dict[str, Dict[str, Any]]:
        """获取服务注册信息"""
        with self._lock:
            service_info = {}
            for service_type, descriptor in self._services.items():
                service_info[service_type.__name__] = {
                    "implementation": descriptor.implementation_type.__name__ if descriptor.implementation_type else "Factory",
                    "lifetime": descriptor.lifetime.value,
                    "has_instance": descriptor.instance is not None,
                    "is_singleton_created": service_type in self._singletons,
                    "is_scoped_active": service_type in self._scoped_instances,
                }
            return service_info


class ServiceScope:
    """服务作用域上下文管理器"""

    def __init__(self, container: DependencyContainer):
        """初始化服务作用域

        Args:
            container: 依赖注入容器
        """
        self.container = container

    def __enter__(self):
        """进入作用域"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出作用域，清理作用域实例"""
        self.container.clear_scoped()


def autowired(container: IDependencyContainer):
    """自动装配装饰器"""
    def decorator(cls):
        # 检查构造函数
        constructor = cls.__init__
        signature = inspect.signature(constructor)
        parameters = list(signature.parameters.values())[1:]  # 跳过self参数

        original_init = cls.__init__

        def new_init(self, *args, **kwargs):
            # 如果提供了参数，直接使用
            if args or kwargs:
                original_init(self, *args, **kwargs)
                return

            # 自动解析依赖
            resolved_args = []
            for param in parameters:
                if param.annotation == inspect.Parameter.empty:
                    raise ValueError(f"构造函数参数 {param.name} 缺少类型注解")

                dependency = container.resolve(param.annotation)
                resolved_args.append(dependency)

            original_init(self, *resolved_args)

        cls.__init__ = new_init
        return cls

    return decorator


# 创建全局容器单例
_container: Optional[DependencyContainer] = None


def get_container() -> DependencyContainer:
    """获取全局依赖注入容器"""
    global _container
    if _container is None:
        _container = DependencyContainer()
    return _container


def create_container() -> DependencyContainer:
    """创建新的依赖注入容器（主要用于测试）"""
    return DependencyContainer()


# 快捷方法
def register_singleton(service_type: Type[T], implementation_type: Type[T] = None, factory: Callable[[], T] = None) -> None:
    """在全局容器中注册单例服务"""
    get_container().register_singleton(service_type, implementation_type, factory)


def register_transient(service_type: Type[T], implementation_type: Type[T] = None, factory: Callable[[], T] = None) -> None:
    """在全局容器中注册瞬态服务"""
    get_container().register_transient(service_type, implementation_type, factory)


def register_scoped(service_type: Type[T], implementation_type: Type[T] = None, factory: Callable[[], T] = None) -> None:
    """在全局容器中注册作用域服务"""
    get_container().register_scoped(service_type, implementation_type, factory)


def register_instance(service_type: Type[T], instance: T) -> None:
    """在全局容器中注册实例"""
    get_container().register_instance(service_type, instance)


def resolve(service_type: Type[T]) -> T:
    """从全局容器解析服务"""
    return get_container().resolve(service_type)


def try_resolve(service_type: Type[T]) -> Optional[T]:
    """从全局容器尝试解析服务"""
    return get_container().try_resolve(service_type)
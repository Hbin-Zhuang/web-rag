"""依赖注入模块"""

from .container import (
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

__all__ = [
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
    'try_resolve'
]
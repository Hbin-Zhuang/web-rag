"""
扩展模块
提供插件管理、扩展点和自动扩缩容功能
"""

from .plugin_manager import (
    PluginManager,
    Plugin,
    PluginInfo,
    PluginStatus,
    get_plugin_manager
)

from .extension_points import (
    ExtensionContext,
    ExtensionHook,
    DocumentProcessingHook,
    QueryProcessingHook,
    ResponseEnhancementHook,
    ExtensionPointRegistry,
    RAGExtensionPoints,
    get_extension_registry,
    get_rag_extensions
)

from .auto_scaling import (
    AutoScaler,
    ScalingAction,
    ResourceType,
    ResourceThreshold,
    ScalingEvent,
    get_auto_scaler
)

__all__ = [
    # 插件管理
    'PluginManager',
    'Plugin',
    'PluginInfo',
    'PluginStatus',
    'get_plugin_manager',

    # 扩展点系统
    'ExtensionContext',
    'ExtensionHook',
    'DocumentProcessingHook',
    'QueryProcessingHook',
    'ResponseEnhancementHook',
    'ExtensionPointRegistry',
    'RAGExtensionPoints',
    'get_extension_registry',
    'get_rag_extensions',

    # 自动扩缩容
    'AutoScaler',
    'ScalingAction',
    'ResourceType',
    'ResourceThreshold',
    'ScalingEvent',
    'get_auto_scaler'
]
"""
插件管理器实现
提供插件热加载、生命周期管理和扩展点支持
"""

import importlib
import inspect
import threading
import os
import sys
from typing import Dict, List, Any, Optional, Type, Callable
from dataclasses import dataclass
from enum import Enum
from abc import ABC, abstractmethod

from ..logging.logging_service import get_logging_service, ILoggingService
from ..monitoring.metrics_service import get_metrics_service


class PluginStatus(Enum):
    """插件状态枚举"""
    UNLOADED = "unloaded"
    LOADING = "loading"
    LOADED = "loaded"
    ACTIVE = "active"
    ERROR = "error"
    DISABLED = "disabled"


@dataclass
class PluginInfo:
    """插件信息"""
    name: str
    version: str
    description: str
    author: str = ""
    entry_point: str = ""
    dependencies: List[str] = None
    status: PluginStatus = PluginStatus.UNLOADED
    error_message: str = ""

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


class Plugin(ABC):
    """插件基础类"""

    def __init__(self):
        self._info: Optional[PluginInfo] = None
        self._manager: Optional['PluginManager'] = None

    @abstractmethod
    def get_info(self) -> PluginInfo:
        """获取插件信息"""
        pass

    @abstractmethod
    def initialize(self) -> bool:
        """初始化插件"""
        pass

    @abstractmethod
    def start(self) -> bool:
        """启动插件"""
        pass

    @abstractmethod
    def stop(self) -> bool:
        """停止插件"""
        pass

    @abstractmethod
    def cleanup(self) -> bool:
        """清理插件"""
        pass

    def set_manager(self, manager: 'PluginManager'):
        """设置插件管理器"""
        self._manager = manager


class PluginManager:
    """插件管理器"""

    def __init__(self,
                 plugin_dirs: List[str] = None,
                 logger_service: Optional[ILoggingService] = None):
        """初始化插件管理器

        Args:
            plugin_dirs: 插件目录列表
            logger_service: 日志服务
        """
        self._logger = logger_service or get_logging_service()
        self._metrics = get_metrics_service()

        self._plugin_dirs = plugin_dirs or ["plugins", "extensions"]
        self._plugins: Dict[str, Plugin] = {}
        self._plugin_infos: Dict[str, PluginInfo] = {}
        self._extension_points: Dict[str, List[Callable]] = {}
        self._lock = threading.RLock()

        self._logger.info("插件管理器初始化完成")

    def discover_plugins(self) -> List[PluginInfo]:
        """发现可用插件

        Returns:
            插件信息列表
        """
        discovered = []

        with self._lock:
            for plugin_dir in self._plugin_dirs:
                if not os.path.exists(plugin_dir):
                    continue

                try:
                    for item in os.listdir(plugin_dir):
                        item_path = os.path.join(plugin_dir, item)

                        # 检查Python包
                        if os.path.isdir(item_path) and os.path.exists(os.path.join(item_path, "__init__.py")):
                            plugin_info = self._load_plugin_info(item_path, item)
                            if plugin_info:
                                discovered.append(plugin_info)
                                self._plugin_infos[plugin_info.name] = plugin_info

                        # 检查单文件插件
                        elif item.endswith(".py") and not item.startswith("__"):
                            plugin_name = item[:-3]  # 移除.py扩展名
                            plugin_info = self._load_plugin_info(item_path, plugin_name)
                            if plugin_info:
                                discovered.append(plugin_info)
                                self._plugin_infos[plugin_info.name] = plugin_info

                except Exception as e:
                    self._logger.error(f"发现插件失败: {plugin_dir}", exception=e)

        self._logger.info(f"发现 {len(discovered)} 个插件")
        return discovered

    def load_plugin(self, plugin_name: str) -> bool:
        """加载插件

        Args:
            plugin_name: 插件名称

        Returns:
            是否成功加载
        """
        with self._lock:
            try:
                if plugin_name in self._plugins:
                    self._logger.warning(f"插件已加载: {plugin_name}")
                    return True

                plugin_info = self._plugin_infos.get(plugin_name)
                if not plugin_info:
                    self._logger.error(f"未找到插件信息: {plugin_name}")
                    return False

                # 更新状态
                plugin_info.status = PluginStatus.LOADING

                # 检查依赖
                if not self._check_dependencies(plugin_info):
                    plugin_info.status = PluginStatus.ERROR
                    plugin_info.error_message = "依赖检查失败"
                    return False

                # 动态导入插件模块
                plugin_module = self._import_plugin_module(plugin_name, plugin_info)
                if not plugin_module:
                    plugin_info.status = PluginStatus.ERROR
                    plugin_info.error_message = "模块导入失败"
                    return False

                # 创建插件实例
                plugin_class = getattr(plugin_module, 'Plugin', None)
                if not plugin_class or not issubclass(plugin_class, Plugin):
                    plugin_info.status = PluginStatus.ERROR
                    plugin_info.error_message = "无效的插件类"
                    return False

                plugin_instance = plugin_class()
                plugin_instance.set_manager(self)

                # 初始化插件
                if not plugin_instance.initialize():
                    plugin_info.status = PluginStatus.ERROR
                    plugin_info.error_message = "插件初始化失败"
                    return False

                # 存储插件实例
                self._plugins[plugin_name] = plugin_instance
                plugin_info.status = PluginStatus.LOADED

                # 记录指标
                self._metrics.increment_counter('plugin_load_success_total', {
                    'plugin': plugin_name
                })

                self._logger.info(f"插件加载成功: {plugin_name}")
                return True

            except Exception as e:
                # 更新错误状态
                if plugin_name in self._plugin_infos:
                    self._plugin_infos[plugin_name].status = PluginStatus.ERROR
                    self._plugin_infos[plugin_name].error_message = str(e)

                self._metrics.increment_counter('plugin_load_failure_total', {
                    'plugin': plugin_name
                })

                self._logger.error(f"加载插件失败: {plugin_name}", exception=e)
                return False

    def start_plugin(self, plugin_name: str) -> bool:
        """启动插件

        Args:
            plugin_name: 插件名称

        Returns:
            是否成功启动
        """
        with self._lock:
            try:
                plugin = self._plugins.get(plugin_name)
                if not plugin:
                    self._logger.error(f"插件未加载: {plugin_name}")
                    return False

                plugin_info = self._plugin_infos[plugin_name]

                if plugin_info.status == PluginStatus.ACTIVE:
                    self._logger.warning(f"插件已启动: {plugin_name}")
                    return True

                # 启动插件
                if plugin.start():
                    plugin_info.status = PluginStatus.ACTIVE

                    self._metrics.increment_counter('plugin_start_success_total', {
                        'plugin': plugin_name
                    })

                    self._logger.info(f"插件启动成功: {plugin_name}")
                    return True
                else:
                    plugin_info.status = PluginStatus.ERROR
                    plugin_info.error_message = "插件启动失败"

                    self._metrics.increment_counter('plugin_start_failure_total', {
                        'plugin': plugin_name
                    })

                    return False

            except Exception as e:
                self._logger.error(f"启动插件失败: {plugin_name}", exception=e)
                return False

    def stop_plugin(self, plugin_name: str) -> bool:
        """停止插件

        Args:
            plugin_name: 插件名称

        Returns:
            是否成功停止
        """
        with self._lock:
            try:
                plugin = self._plugins.get(plugin_name)
                if not plugin:
                    return True  # 已经停止

                plugin_info = self._plugin_infos[plugin_name]

                # 停止插件
                if plugin.stop():
                    plugin_info.status = PluginStatus.LOADED

                    self._metrics.increment_counter('plugin_stop_success_total', {
                        'plugin': plugin_name
                    })

                    self._logger.info(f"插件停止成功: {plugin_name}")
                    return True
                else:
                    self._logger.error(f"插件停止失败: {plugin_name}")
                    return False

            except Exception as e:
                self._logger.error(f"停止插件失败: {plugin_name}", exception=e)
                return False

    def unload_plugin(self, plugin_name: str) -> bool:
        """卸载插件

        Args:
            plugin_name: 插件名称

        Returns:
            是否成功卸载
        """
        with self._lock:
            try:
                plugin = self._plugins.get(plugin_name)
                if not plugin:
                    return True  # 已经卸载

                plugin_info = self._plugin_infos[plugin_name]

                # 先停止插件
                if plugin_info.status == PluginStatus.ACTIVE:
                    self.stop_plugin(plugin_name)

                # 清理插件
                plugin.cleanup()

                # 移除插件实例
                del self._plugins[plugin_name]
                plugin_info.status = PluginStatus.UNLOADED

                self._metrics.increment_counter('plugin_unload_total', {
                    'plugin': plugin_name
                })

                self._logger.info(f"插件卸载成功: {plugin_name}")
                return True

            except Exception as e:
                self._logger.error(f"卸载插件失败: {plugin_name}", exception=e)
                return False

    def get_plugin_list(self) -> List[PluginInfo]:
        """获取插件列表

        Returns:
            插件信息列表
        """
        with self._lock:
            return list(self._plugin_infos.values())

    def get_plugin_info(self, plugin_name: str) -> Optional[PluginInfo]:
        """获取插件信息

        Args:
            plugin_name: 插件名称

        Returns:
            插件信息或None
        """
        return self._plugin_infos.get(plugin_name)

    def get_active_plugins(self) -> List[str]:
        """获取活跃插件列表

        Returns:
            活跃插件名称列表
        """
        with self._lock:
            return [
                name for name, info in self._plugin_infos.items()
                if info.status == PluginStatus.ACTIVE
            ]

    def register_extension_point(self, name: str, callback: Callable):
        """注册扩展点

        Args:
            name: 扩展点名称
            callback: 回调函数
        """
        with self._lock:
            if name not in self._extension_points:
                self._extension_points[name] = []

            self._extension_points[name].append(callback)
            self._logger.debug(f"注册扩展点: {name}")

    def call_extension_point(self, name: str, *args, **kwargs) -> List[Any]:
        """调用扩展点

        Args:
            name: 扩展点名称
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            回调函数返回值列表
        """
        with self._lock:
            results = []

            callbacks = self._extension_points.get(name, [])
            for callback in callbacks:
                try:
                    result = callback(*args, **kwargs)
                    results.append(result)
                except Exception as e:
                    self._logger.error(f"扩展点回调失败: {name}", exception=e)

            return results

    def _load_plugin_info(self, plugin_path: str, plugin_name: str) -> Optional[PluginInfo]:
        """加载插件信息

        Args:
            plugin_path: 插件路径
            plugin_name: 插件名称

        Returns:
            插件信息或None
        """
        try:
            # 尝试加载插件配置
            config_file = os.path.join(plugin_path, "plugin.json") if os.path.isdir(plugin_path) else None

            if config_file and os.path.exists(config_file):
                import json
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)

                return PluginInfo(
                    name=config.get('name', plugin_name),
                    version=config.get('version', '1.0.0'),
                    description=config.get('description', ''),
                    author=config.get('author', ''),
                    entry_point=config.get('entry_point', ''),
                    dependencies=config.get('dependencies', [])
                )
            else:
                # 默认插件信息
                return PluginInfo(
                    name=plugin_name,
                    version='1.0.0',
                    description=f'Plugin: {plugin_name}',
                    entry_point=plugin_path
                )

        except Exception as e:
            self._logger.error(f"加载插件信息失败: {plugin_path}", exception=e)
            return None

    def _check_dependencies(self, plugin_info: PluginInfo) -> bool:
        """检查插件依赖

        Args:
            plugin_info: 插件信息

        Returns:
            依赖是否满足
        """
        for dep in plugin_info.dependencies:
            if dep not in self._plugin_infos:
                self._logger.error(f"插件 {plugin_info.name} 缺少依赖: {dep}")
                return False

            dep_info = self._plugin_infos[dep]
            if dep_info.status not in [PluginStatus.LOADED, PluginStatus.ACTIVE]:
                self._logger.error(f"插件 {plugin_info.name} 的依赖 {dep} 未加载")
                return False

        return True

    def _import_plugin_module(self, plugin_name: str, plugin_info: PluginInfo):
        """导入插件模块

        Args:
            plugin_name: 插件名称
            plugin_info: 插件信息

        Returns:
            插件模块或None
        """
        try:
            # 添加插件目录到路径
            for plugin_dir in self._plugin_dirs:
                if plugin_dir not in sys.path:
                    sys.path.insert(0, plugin_dir)

            # 动态导入
            module_name = f"plugins.{plugin_name}" if "plugins" in self._plugin_dirs else plugin_name

            if module_name in sys.modules:
                # 重新加载模块
                importlib.reload(sys.modules[module_name])
                return sys.modules[module_name]
            else:
                return importlib.import_module(module_name)

        except Exception as e:
            self._logger.error(f"导入插件模块失败: {plugin_name}", exception=e)
            return None


# 全局插件管理器实例
_plugin_manager_instance: Optional[PluginManager] = None
_plugin_manager_lock = threading.Lock()


def get_plugin_manager() -> PluginManager:
    """获取插件管理器单例实例"""
    global _plugin_manager_instance

    if _plugin_manager_instance is None:
        with _plugin_manager_lock:
            if _plugin_manager_instance is None:
                _plugin_manager_instance = PluginManager()

    return _plugin_manager_instance

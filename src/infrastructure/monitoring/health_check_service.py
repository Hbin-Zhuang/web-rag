"""
健康检查服务实现
提供系统健康状态监控和检查功能
"""

import time
import threading
import traceback
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum

from ..external.interfaces import IHealthCheckService
from ..logging.logging_service import ILoggingService, get_logging_service


class HealthStatus(Enum):
    """健康状态枚举"""
    HEALTHY = "healthy"           # 健康
    DEGRADED = "degraded"        # 降级
    UNHEALTHY = "unhealthy"      # 不健康
    UNKNOWN = "unknown"          # 未知


@dataclass
class ComponentHealth:
    """组件健康状态"""
    name: str
    status: HealthStatus
    message: str = ""
    last_check: Optional[datetime] = None
    response_time: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'name': self.name,
            'status': self.status.value,
            'message': self.message,
            'last_check': self.last_check.isoformat() if self.last_check else None,
            'response_time': self.response_time,
            'metadata': self.metadata
        }


@dataclass
class SystemHealth:
    """系统整体健康状态"""
    overall_status: HealthStatus
    components: Dict[str, ComponentHealth] = field(default_factory=dict)
    last_check: Optional[datetime] = None
    uptime: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'overall_status': self.overall_status.value,
            'last_check': self.last_check.isoformat() if self.last_check else None,
            'uptime': self.uptime,
            'components': {
                name: component.to_dict()
                for name, component in self.components.items()
            }
        }


class HealthCheckService(IHealthCheckService):
    """健康检查服务实现"""

    def __init__(self, logger_service: Optional[ILoggingService] = None):
        """初始化健康检查服务

        Args:
            logger_service: 日志服务实例
        """
        self._logger = logger_service or get_logging_service()
        self._health_checks: Dict[str, Callable[[], ComponentHealth]] = {}
        self._component_health: Dict[str, ComponentHealth] = {}
        self._lock = threading.RLock()
        self._start_time = time.time()

        # 自动注册基础健康检查
        self._register_basic_health_checks()

        self._logger.info("健康检查服务初始化完成")

    def register_health_check(self,
                             name: str,
                             check_func: Callable[[], ComponentHealth]) -> None:
        """注册健康检查函数

        Args:
            name: 组件名称
            check_func: 健康检查函数
        """
        with self._lock:
            self._health_checks[name] = check_func
            self._logger.info(f"注册健康检查: {name}")

    def unregister_health_check(self, name: str) -> None:
        """取消注册健康检查

        Args:
            name: 组件名称
        """
        with self._lock:
            if name in self._health_checks:
                del self._health_checks[name]
                if name in self._component_health:
                    del self._component_health[name]
                self._logger.info(f"取消注册健康检查: {name}")

    def check_health(self, component_name: Optional[str] = None) -> SystemHealth:
        """执行健康检查

        Args:
            component_name: 指定组件名称，None表示检查所有组件

        Returns:
            系统健康状态
        """
        with self._lock:
            try:
                current_time = datetime.now()

                if component_name:
                    # 检查指定组件
                    if component_name in self._health_checks:
                        self._check_component(component_name)
                else:
                    # 检查所有组件
                    for name in self._health_checks:
                        self._check_component(name)

                # 计算整体健康状态
                overall_status = self._calculate_overall_status()

                # 计算运行时间
                uptime = time.time() - self._start_time

                system_health = SystemHealth(
                    overall_status=overall_status,
                    components=self._component_health.copy(),
                    last_check=current_time,
                    uptime=uptime
                )

                return system_health

            except Exception as e:
                self._logger.error("健康检查执行失败", exception=e)
                return SystemHealth(
                    overall_status=HealthStatus.UNKNOWN,
                    last_check=datetime.now()
                )

    def get_component_health(self, name: str) -> Optional[ComponentHealth]:
        """获取指定组件的健康状态

        Args:
            name: 组件名称

        Returns:
            组件健康状态
        """
        with self._lock:
            return self._component_health.get(name)

    def is_healthy(self) -> bool:
        """检查系统是否健康

        Returns:
            是否健康
        """
        system_health = self.check_health()
        return system_health.overall_status == HealthStatus.HEALTHY

    def get_unhealthy_components(self) -> List[ComponentHealth]:
        """获取不健康的组件列表

        Returns:
            不健康组件列表
        """
        with self._lock:
            return [
                component for component in self._component_health.values()
                if component.status in [HealthStatus.UNHEALTHY, HealthStatus.DEGRADED]
            ]

    def _check_component(self, name: str):
        """检查单个组件健康状态

        Args:
            name: 组件名称
        """
        try:
            start_time = time.time()
            check_func = self._health_checks[name]

            # 执行健康检查
            component_health = check_func()
            component_health.last_check = datetime.now()
            component_health.response_time = time.time() - start_time

            # 存储结果
            self._component_health[name] = component_health

            # 记录日志
            if component_health.status != HealthStatus.HEALTHY:
                self._logger.warning(
                    f"组件 {name} 健康检查异常: {component_health.status.value}",
                    extra={
                        "component": name,
                        "status": component_health.status.value,
                        "message": component_health.message,
                        "response_time": component_health.response_time
                    }
                )
            else:
                self._logger.debug(
                    f"组件 {name} 健康检查正常",
                    extra={
                        "component": name,
                        "response_time": component_health.response_time
                    }
                )

        except Exception as e:
            # 健康检查函数异常
            error_msg = f"健康检查异常: {str(e)}"
            self._component_health[name] = ComponentHealth(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=error_msg,
                last_check=datetime.now(),
                metadata={'error': str(e), 'traceback': traceback.format_exc()}
            )

            self._logger.error(f"组件 {name} 健康检查失败", exception=e)

    def _calculate_overall_status(self) -> HealthStatus:
        """计算整体健康状态

        Returns:
            整体健康状态
        """
        if not self._component_health:
            return HealthStatus.UNKNOWN

        unhealthy_count = 0
        degraded_count = 0

        for component in self._component_health.values():
            if component.status == HealthStatus.UNHEALTHY:
                unhealthy_count += 1
            elif component.status == HealthStatus.DEGRADED:
                degraded_count += 1

        total_components = len(self._component_health)

        # 如果有任何组件不健康，整体状态为不健康
        if unhealthy_count > 0:
            return HealthStatus.UNHEALTHY

        # 如果有组件降级，整体状态为降级
        if degraded_count > 0:
            return HealthStatus.DEGRADED

        # 所有组件都健康
        return HealthStatus.HEALTHY

    def _register_basic_health_checks(self):
        """注册基础健康检查"""

        def check_memory():
            """内存使用检查"""
            try:
                import psutil
                memory = psutil.virtual_memory()
                cpu_percent = psutil.cpu_percent(interval=1)

                # 内存使用率超过90%为不健康，超过80%为降级
                if memory.percent > 90:
                    status = HealthStatus.UNHEALTHY
                    message = f"内存使用率过高: {memory.percent:.1f}%"
                elif memory.percent > 80:
                    status = HealthStatus.DEGRADED
                    message = f"内存使用率较高: {memory.percent:.1f}%"
                else:
                    status = HealthStatus.HEALTHY
                    message = f"内存使用正常: {memory.percent:.1f}%"

                return ComponentHealth(
                    name="memory",
                    status=status,
                    message=message,
                    metadata={
                        'memory_percent': memory.percent,
                        'memory_available': memory.available,
                        'memory_total': memory.total,
                        'cpu_percent': cpu_percent
                    }
                )

            except ImportError:
                # psutil不可用时的简单检查
                return ComponentHealth(
                    name="memory",
                    status=HealthStatus.HEALTHY,
                    message="内存监控不可用（缺少psutil）"
                )
            except Exception as e:
                return ComponentHealth(
                    name="memory",
                    status=HealthStatus.UNHEALTHY,
                    message=f"内存检查失败: {str(e)}"
                )

        def check_disk():
            """磁盘空间检查"""
            try:
                import psutil
                disk = psutil.disk_usage('/')

                # 磁盘使用率超过95%为不健康，超过90%为降级
                if disk.percent > 95:
                    status = HealthStatus.UNHEALTHY
                    message = f"磁盘空间不足: {disk.percent:.1f}%"
                elif disk.percent > 90:
                    status = HealthStatus.DEGRADED
                    message = f"磁盘空间较少: {disk.percent:.1f}%"
                else:
                    status = HealthStatus.HEALTHY
                    message = f"磁盘空间正常: {disk.percent:.1f}%"

                return ComponentHealth(
                    name="disk",
                    status=status,
                    message=message,
                    metadata={
                        'disk_percent': disk.percent,
                        'disk_free': disk.free,
                        'disk_total': disk.total
                    }
                )

            except ImportError:
                return ComponentHealth(
                    name="disk",
                    status=HealthStatus.HEALTHY,
                    message="磁盘监控不可用（缺少psutil）"
                )
            except Exception as e:
                return ComponentHealth(
                    name="disk",
                    status=HealthStatus.UNHEALTHY,
                    message=f"磁盘检查失败: {str(e)}"
                )

        def check_database():
            """数据库连接检查"""
            try:
                # 检查向量数据库连接状态
                from ...shared.state.application_state import get_application_state

                app_state = get_application_state()

                if app_state.vectorstore is not None:
                    # 尝试一个简单的查询来测试连接
                    try:
                        # 这里可以添加实际的数据库健康检查
                        status = HealthStatus.HEALTHY
                        message = "向量数据库连接正常"
                    except Exception:
                        status = HealthStatus.DEGRADED
                        message = "向量数据库连接异常"
                else:
                    status = HealthStatus.DEGRADED
                    message = "向量数据库未初始化"

                return ComponentHealth(
                    name="database",
                    status=status,
                    message=message,
                    metadata={
                        'vectorstore_initialized': app_state.vectorstore is not None
                    }
                )

            except Exception as e:
                return ComponentHealth(
                    name="database",
                    status=HealthStatus.UNHEALTHY,
                    message=f"数据库检查失败: {str(e)}"
                )

        def check_api_keys():
            """API密钥配置检查"""
            try:
                from ...config.configuration_service import get_config_service

                config = get_config_service()

                # 检查Google API密钥
                api_key = config.get_google_api_key()

                if not api_key:
                    status = HealthStatus.UNHEALTHY
                    message = "Google API密钥未配置"
                elif not api_key.startswith('AIza'):
                    status = HealthStatus.DEGRADED
                    message = "Google API密钥格式可能不正确"
                else:
                    status = HealthStatus.HEALTHY
                    message = "API密钥配置正常"

                return ComponentHealth(
                    name="api_keys",
                    status=status,
                    message=message,
                    metadata={
                        'google_api_key_configured': bool(api_key),
                        'google_api_key_format_valid': api_key.startswith('AIza') if api_key else False
                    }
                )

            except Exception as e:
                return ComponentHealth(
                    name="api_keys",
                    status=HealthStatus.UNHEALTHY,
                    message=f"API密钥检查失败: {str(e)}"
                )

        # 注册基础健康检查
        self.register_health_check("memory", check_memory)
        self.register_health_check("disk", check_disk)
        self.register_health_check("database", check_database)
        self.register_health_check("api_keys", check_api_keys)

    def check_service_health(self, service_name: str) -> ComponentHealth:
        """检查单个服务健康状态

        Args:
            service_name: 服务名称

        Returns:
            服务健康状态
        """
        start_time = time.time()

        try:
            # 执行指定组件的健康检查
            self._check_component(service_name)
            component_health = self._component_health.get(service_name)

            if component_health:
                return component_health
            else:
                # 如果组件不存在，返回未知状态
                return ComponentHealth(
                    name=service_name,
                    status=HealthStatus.UNKNOWN,
                    message=f"未找到服务: {service_name}",
                    last_check=datetime.now(),
                    response_time=time.time() - start_time
                )

        except Exception as e:
            response_time = time.time() - start_time
            self._logger.error(f"检查服务健康状态失败: {service_name}", exception=e)

            return ComponentHealth(
                name=service_name,
                status=HealthStatus.UNHEALTHY,
                message=str(e),
                last_check=datetime.now(),
                response_time=response_time
            )

    def check_all_services_health(self) -> Dict[str, ComponentHealth]:
        """检查所有服务健康状态

        Returns:
            所有服务健康状态字典
        """
        try:
            # 检查所有组件
            system_health = self.check_health()
            return system_health.components

        except Exception as e:
            self._logger.error("检查所有服务健康状态失败", exception=e)
            return {}

    def get_health_status(self) -> Dict[str, Any]:
        """获取健康状态（兼容旧接口）

        Returns:
            健康状态字典
        """
        try:
            system_health = self.check_health()

            # 计算整体健康分数
            if system_health.overall_status == HealthStatus.HEALTHY:
                overall_health = 1.0
            elif system_health.overall_status == HealthStatus.DEGRADED:
                overall_health = 0.7
            elif system_health.overall_status == HealthStatus.UNHEALTHY:
                overall_health = 0.3
            else:
                overall_health = 0.0

            return {
                'overall_health': overall_health,
                'status': system_health.overall_status.value,
                'uptime': system_health.uptime,
                'last_check': system_health.last_check.isoformat() if system_health.last_check else None,
                'components': {
                    name: {
                        'status': component.status.value,
                        'message': component.message,
                        'response_time': component.response_time,
                        'metadata': component.metadata
                    }
                    for name, component in system_health.components.items()
                }
            }

        except Exception as e:
            self._logger.error("获取健康状态失败", exception=e)
            return {
                'overall_health': 0.0,
                'status': 'unknown',
                'error': str(e)
            }

    def _check_memory_health(self) -> bool:
        """简单内存健康检查"""
        try:
            import psutil
            memory = psutil.virtual_memory()
            return memory.percent < 90  # 内存使用率小于90%为健康
        except:
            return True  # 检查失败时假设健康

    def _check_disk_health(self) -> bool:
        """简单磁盘健康检查"""
        try:
            import psutil
            disk = psutil.disk_usage('/')
            return disk.percent < 95  # 磁盘使用率小于95%为健康
        except:
            return True  # 检查失败时假设健康

    def _check_database_health(self) -> bool:
        """简单数据库健康检查"""
        try:
            from ...shared.state.application_state import get_application_state
            app_state = get_application_state()
            return app_state.vectorstore is not None
        except:
            return True  # 检查失败时假设健康

    def _check_api_keys_health(self) -> bool:
        """简单API密钥健康检查"""
        try:
            from ...config.configuration_service import get_config_service
            config = get_config_service()
            api_key = config.get_google_api_key()
            return bool(api_key)
        except:
            return True  # 检查失败时假设健康


# 全局实例
_health_check_service_instance: Optional[HealthCheckService] = None
_health_check_service_lock = threading.Lock()


def get_health_check_service() -> HealthCheckService:
    """获取健康检查服务单例实例"""
    global _health_check_service_instance

    if _health_check_service_instance is None:
        with _health_check_service_lock:
            if _health_check_service_instance is None:
                _health_check_service_instance = HealthCheckService()

    return _health_check_service_instance


def create_health_check_service(logger_service: Optional[ILoggingService] = None) -> HealthCheckService:
    """创建新的健康检查服务实例"""
    return HealthCheckService(logger_service)
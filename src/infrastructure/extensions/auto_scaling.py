"""
自动化扩展系统实现
提供负载监控、资源调度和自动扩缩容功能
"""

import threading
import time
import psutil
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum

from ..logging.logging_service import get_logging_service
from ..monitoring.metrics_service import get_metrics_service


class ScalingAction(Enum):
    """扩缩容动作枚举"""
    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"
    MAINTAIN = "maintain"


class ResourceType(Enum):
    """资源类型枚举"""
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    CUSTOM = "custom"


@dataclass
class ResourceThreshold:
    """资源阈值配置"""
    resource_type: ResourceType
    scale_up_threshold: float       # 扩容阈值
    scale_down_threshold: float     # 缩容阈值
    min_instances: int = 1          # 最小实例数
    max_instances: int = 10         # 最大实例数
    cooldown_period: int = 300      # 冷却期（秒）


@dataclass
class ScalingEvent:
    """扩缩容事件"""
    timestamp: float
    action: ScalingAction
    resource_type: ResourceType
    current_value: float
    threshold: float
    instances_before: int
    instances_after: int
    reason: str


class AutoScaler:
    """自动扩缩容管理器（简化版）"""

    def __init__(self):
        """初始化自动扩缩容管理器"""
        self._logger = get_logging_service()
        self._metrics = get_metrics_service()

        # 资源阈值配置
        self._thresholds: Dict[str, ResourceThreshold] = {}

        # 扩缩容历史
        self._scaling_history: List[ScalingEvent] = []
        self._last_scaling: Dict[str, float] = {}

        # 锁
        self._lock = threading.RLock()

        self._logger.info("自动扩缩容管理器初始化完成")

    def add_threshold(self, threshold: ResourceThreshold):
        """添加资源阈值配置

        Args:
            threshold: 资源阈值配置
        """
        with self._lock:
            key = threshold.resource_type.value
            self._thresholds[key] = threshold
            self._logger.info(f"添加资源阈值: {key}")

    def get_scaling_history(self, limit: int = 100) -> List[ScalingEvent]:
        """获取扩缩容历史

        Args:
            limit: 返回记录数限制

        Returns:
            扩缩容事件列表
        """
        with self._lock:
            return self._scaling_history[-limit:]

    def get_current_stats(self) -> Dict[str, Any]:
        """获取当前状态统计

        Returns:
            状态统计字典
        """
        with self._lock:
            try:
                # 系统资源
                cpu_percent = psutil.cpu_percent()
                memory_percent = psutil.virtual_memory().percent

                return {
                    'system': {
                        'cpu_usage': cpu_percent,
                        'memory_usage': memory_percent,
                        'timestamp': time.time()
                    },
                    'thresholds': {
                        key: {
                            'scale_up_threshold': th.scale_up_threshold,
                            'scale_down_threshold': th.scale_down_threshold,
                            'min_instances': th.min_instances,
                            'max_instances': th.max_instances
                        }
                        for key, th in self._thresholds.items()
                    },
                    'scaling_events_count': len(self._scaling_history)
                }
            except Exception as e:
                self._logger.error("获取系统统计失败", exception=e)
                return {
                    'system': {
                        'cpu_usage': 0.0,
                        'memory_usage': 0.0,
                        'timestamp': time.time()
                    },
                    'thresholds': {},
                    'scaling_events_count': 0
                }


# 全局自动扩缩容实例
_auto_scaler_instance: Optional[AutoScaler] = None
_auto_scaler_lock = threading.Lock()


def get_auto_scaler() -> AutoScaler:
    """获取自动扩缩容管理器单例实例"""
    global _auto_scaler_instance

    if _auto_scaler_instance is None:
        with _auto_scaler_lock:
            if _auto_scaler_instance is None:
                _auto_scaler_instance = AutoScaler()

    return _auto_scaler_instance
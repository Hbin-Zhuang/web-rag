"""
指标服务实现
提供实时指标收集、存储和查询功能
"""

import time
import threading
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from collections import defaultdict, deque
import json
import os

from ..external.interfaces import IMetricsService
from ..logging.logging_service import ILoggingService, get_logging_service


class MetricType(Enum):
    """指标类型枚举"""
    COUNTER = "counter"        # 计数器
    GAUGE = "gauge"           # 测量值
    HISTOGRAM = "histogram"   # 直方图
    TIMER = "timer"          # 计时器


@dataclass
class MetricValue:
    """指标值数据类"""
    name: str
    value: float
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)
    metric_type: MetricType = MetricType.GAUGE


@dataclass
class TimeSeriesData:
    """时间序列数据"""
    metric_name: str
    values: List[MetricValue] = field(default_factory=list)
    max_size: int = 1000

    def add_value(self, value: MetricValue):
        """添加数据点"""
        self.values.append(value)
        if len(self.values) > self.max_size:
            self.values.pop(0)

    def get_latest(self, count: int = 10) -> List[MetricValue]:
        """获取最新的数据点"""
        return self.values[-count:]

    def get_range(self, start_time: datetime, end_time: datetime) -> List[MetricValue]:
        """获取时间范围内的数据"""
        return [v for v in self.values if start_time <= v.timestamp <= end_time]


class MetricsService(IMetricsService):
    """指标服务实现"""

    def __init__(self, logger_service: Optional[ILoggingService] = None):
        """初始化指标服务

        Args:
            logger_service: 日志服务实例
        """
        self._logger = logger_service or get_logging_service()
        self._metrics_data: Dict[str, TimeSeriesData] = {}
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        self._lock = threading.RLock()

        # 性能统计
        self._performance_stats = {
            'total_metrics_recorded': 0,
            'metrics_per_second': 0,
            'last_recorded_time': time.time()
        }

        self._logger.info("指标服务初始化完成")

    def record_metric(self,
                     name: str,
                     value: float,
                     tags: Optional[Dict[str, str]] = None) -> None:
        """记录指标

        Args:
            name: 指标名称
            value: 指标值
            tags: 标签字典
        """
        with self._lock:
            try:
                tags = tags or {}
                timestamp = datetime.now()

                metric_value = MetricValue(
                    name=name,
                    value=value,
                    timestamp=timestamp,
                    tags=tags,
                    metric_type=MetricType.GAUGE
                )

                # 存储到时间序列数据
                if name not in self._metrics_data:
                    self._metrics_data[name] = TimeSeriesData(metric_name=name)

                self._metrics_data[name].add_value(metric_value)

                # 更新性能统计
                self._update_performance_stats()

                self._logger.debug(f"记录指标: {name}={value}", extra={
                    "metric_name": name,
                    "metric_value": value,
                    "tags": tags
                })

            except Exception as e:
                self._logger.error(f"记录指标失败: {name}", exception=e)

    def increment_counter(self,
                         name: str,
                         tags: Optional[Dict[str, str]] = None) -> None:
        """递增计数器

        Args:
            name: 计数器名称
            tags: 标签字典
        """
        with self._lock:
            try:
                self._counters[name] += 1

                # 同时记录到时间序列
                self.record_metric(f"{name}_total", self._counters[name], tags)

                self._logger.debug(f"递增计数器: {name}={self._counters[name]}")

            except Exception as e:
                self._logger.error(f"递增计数器失败: {name}", exception=e)

    def record_histogram(self,
                        name: str,
                        value: float,
                        tags: Optional[Dict[str, str]] = None) -> None:
        """记录直方图

        Args:
            name: 直方图名称
            value: 数值
            tags: 标签字典
        """
        with self._lock:
            try:
                self._histograms[name].append(value)

                # 限制历史数据大小
                if len(self._histograms[name]) > 1000:
                    self._histograms[name].pop(0)

                # 计算统计值
                values = self._histograms[name]
                stats = {
                    'count': len(values),
                    'sum': sum(values),
                    'avg': sum(values) / len(values),
                    'min': min(values),
                    'max': max(values)
                }

                # 记录统计指标
                for stat_name, stat_value in stats.items():
                    self.record_metric(f"{name}_{stat_name}", stat_value, tags)

                self._logger.debug(f"记录直方图: {name}={value}")

            except Exception as e:
                self._logger.error(f"记录直方图失败: {name}", exception=e)

    def get_metrics(self,
                   name_pattern: Optional[str] = None) -> Dict[str, Any]:
        """获取指标数据

        Args:
            name_pattern: 指标名称模式（支持通配符）

        Returns:
            指标数据字典
        """
        with self._lock:
            try:
                result = {
                    'timestamp': datetime.now().isoformat(),
                    'counters': dict(self._counters),
                    'gauges': dict(self._gauges),
                    'performance_stats': self._performance_stats.copy()
                }

                # 时间序列数据
                if name_pattern:
                    # 简单的模式匹配
                    filtered_metrics = {
                        k: v for k, v in self._metrics_data.items()
                        if name_pattern in k
                    }
                else:
                    filtered_metrics = self._metrics_data

                # 转换时间序列数据为可序列化格式
                time_series = {}
                for name, ts_data in filtered_metrics.items():
                    latest_values = ts_data.get_latest(100)  # 最近100个点
                    time_series[name] = [
                        {
                            'value': v.value,
                            'timestamp': v.timestamp.isoformat(),
                            'tags': v.tags
                        }
                        for v in latest_values
                    ]

                result['time_series'] = time_series

                # 直方图统计
                histogram_stats = {}
                for name, values in self._histograms.items():
                    if values:
                        histogram_stats[name] = {
                            'count': len(values),
                            'sum': sum(values),
                            'avg': sum(values) / len(values),
                            'min': min(values),
                            'max': max(values)
                        }

                result['histograms'] = histogram_stats

                return result

            except Exception as e:
                self._logger.error("获取指标数据失败", exception=e)
                return {}

    def get_metric_history(self,
                          name: str,
                          hours: int = 1) -> List[MetricValue]:
        """获取指标历史数据

        Args:
            name: 指标名称
            hours: 历史小时数

        Returns:
            指标值列表
        """
        with self._lock:
            if name not in self._metrics_data:
                return []

            start_time = datetime.now() - timedelta(hours=hours)
            end_time = datetime.now()

            return self._metrics_data[name].get_range(start_time, end_time)

    def record_api_request(self,
                          method: str,
                          endpoint: str,
                          response_time: float,
                          status_code: int,
                          **kwargs):
        """记录API请求指标

        Args:
            method: HTTP方法
            endpoint: 端点路径
            response_time: 响应时间
            status_code: 状态码
            **kwargs: 额外标签
        """
        tags = {
            'method': method,
            'endpoint': endpoint,
            'status_code': str(status_code),
            **kwargs
        }

        # 记录响应时间
        self.record_histogram('api_response_time', response_time, tags)

        # 记录请求计数
        self.increment_counter('api_requests_total', tags)

        # 记录错误率
        if status_code >= 400:
            self.increment_counter('api_errors_total', tags)

    def record_rag_metrics(self,
                          query: str,
                          response_time: float,
                          retrieval_count: int,
                          context_length: int,
                          **kwargs):
        """记录RAG特定指标

        Args:
            query: 查询内容
            response_time: 响应时间
            retrieval_count: 检索文档数量
            context_length: 上下文长度
            **kwargs: 额外标签
        """
        tags = {
            'query_length': str(len(query)),
            **kwargs
        }

        # RAG响应时间
        self.record_histogram('rag_response_time', response_time, tags)

        # 检索文档数量
        self.record_metric('rag_retrieval_count', retrieval_count, tags)

        # 上下文长度
        self.record_metric('rag_context_length', context_length, tags)

        # RAG查询计数
        self.increment_counter('rag_queries_total', tags)

    def _update_performance_stats(self):
        """更新性能统计"""
        current_time = time.time()
        self._performance_stats['total_metrics_recorded'] += 1

        # 计算每秒指标数
        time_diff = current_time - self._performance_stats['last_recorded_time']
        if time_diff >= 1.0:  # 每秒更新一次
            self._performance_stats['metrics_per_second'] = 1.0 / time_diff
            self._performance_stats['last_recorded_time'] = current_time

    def export_metrics(self, file_path: str) -> bool:
        """导出指标数据到文件

        Args:
            file_path: 文件路径

        Returns:
            是否成功
        """
        try:
            metrics_data = self.get_metrics()

            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(metrics_data, f, indent=2, ensure_ascii=False)

            self._logger.info(f"指标数据已导出到: {file_path}")
            return True

        except Exception as e:
            self._logger.error(f"导出指标数据失败: {file_path}", exception=e)
            return False

    def clear_metrics(self, older_than_hours: int = 24):
        """清理旧指标数据

        Args:
            older_than_hours: 清理多少小时前的数据
        """
        with self._lock:
            try:
                cutoff_time = datetime.now() - timedelta(hours=older_than_hours)

                for name, ts_data in self._metrics_data.items():
                    old_count = len(ts_data.values)
                    ts_data.values = [
                        v for v in ts_data.values
                        if v.timestamp > cutoff_time
                    ]
                    new_count = len(ts_data.values)

                    if old_count > new_count:
                        self._logger.debug(
                            f"清理指标数据: {name}, 删除 {old_count - new_count} 个数据点"
                        )

                self._logger.info(f"清理了 {older_than_hours} 小时前的指标数据")

            except Exception as e:
                self._logger.error("清理指标数据失败", exception=e)


# 全局实例
_metrics_service_instance: Optional[MetricsService] = None
_metrics_service_lock = threading.Lock()


def get_metrics_service() -> MetricsService:
    """获取指标服务单例实例"""
    global _metrics_service_instance

    if _metrics_service_instance is None:
        with _metrics_service_lock:
            if _metrics_service_instance is None:
                _metrics_service_instance = MetricsService()

    return _metrics_service_instance


def create_metrics_service(logger_service: Optional[ILoggingService] = None) -> MetricsService:
    """创建新的指标服务实例"""
    return MetricsService(logger_service)
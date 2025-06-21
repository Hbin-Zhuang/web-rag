"""
监控中间件
提供自动化的性能监控装饰器和工具
"""

import time
import functools
import threading
from typing import Callable, Any, Dict, Optional
from datetime import datetime

from .metrics_service import get_metrics_service, MetricsService
from ..logging.logging_service import get_logging_service, ILoggingService


class MonitoringMiddleware:
    """监控中间件类"""

    def __init__(self,
                 metrics_service: Optional[MetricsService] = None,
                 logger_service: Optional[ILoggingService] = None):
        """初始化监控中间件

        Args:
            metrics_service: 指标服务实例
            logger_service: 日志服务实例
        """
        self._metrics_service = metrics_service or get_metrics_service()
        self._logger = logger_service or get_logging_service()

        # 线程本地存储，用于跟踪请求上下文
        self._local = threading.local()

        self._logger.info("监控中间件初始化完成")

    def set_request_context(self, **context):
        """设置请求上下文

        Args:
            **context: 上下文键值对
        """
        if not hasattr(self._local, 'context'):
            self._local.context = {}

        self._local.context.update(context)

    def get_request_context(self) -> Dict[str, Any]:
        """获取当前请求上下文

        Returns:
            上下文字典
        """
        if hasattr(self._local, 'context'):
            return self._local.context.copy()
        return {}

    def clear_request_context(self):
        """清除请求上下文"""
        if hasattr(self._local, 'context'):
            self._local.context.clear()


# 全局中间件实例
_middleware_instance: Optional[MonitoringMiddleware] = None
_middleware_lock = threading.Lock()


def get_monitoring_middleware() -> MonitoringMiddleware:
    """获取监控中间件单例实例"""
    global _middleware_instance

    if _middleware_instance is None:
        with _middleware_lock:
            if _middleware_instance is None:
                _middleware_instance = MonitoringMiddleware()

    return _middleware_instance


def monitor_performance(
    metric_name: Optional[str] = None,
    include_args: bool = False,
    include_result: bool = False,
    tags: Optional[Dict[str, str]] = None
):
    """性能监控装饰器

    Args:
        metric_name: 自定义指标名称，默认使用函数名
        include_args: 是否在日志中包含参数
        include_result: 是否在日志中包含返回值
        tags: 额外的标签
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            middleware = get_monitoring_middleware()
            metrics_service = middleware._metrics_service
            logger = middleware._logger

            # 生成指标名称
            name = metric_name or f"{func.__module__}.{func.__name__}"

            # 获取上下文
            context = middleware.get_request_context()

            # 合并标签
            all_tags = {
                'function': func.__name__,
                'module': func.__module__,
                **context,
                **(tags or {})
            }

            start_time = time.time()

            try:
                # 记录函数开始
                logger.debug(f"开始执行函数: {name}", extra={
                    'function_name': name,
                    'args': args if include_args else '<隐藏>',
                    'kwargs': kwargs if include_args else '<隐藏>',
                    'tags': all_tags
                })

                # 执行函数
                result = func(*args, **kwargs)

                # 计算执行时间
                execution_time = time.time() - start_time

                # 记录性能指标
                metrics_service.record_histogram(
                    f"{name}_duration",
                    execution_time,
                    all_tags
                )

                # 记录成功计数
                metrics_service.increment_counter(
                    f"{name}_success_total",
                    all_tags
                )

                # 记录函数完成
                logger.debug(f"函数执行完成: {name}", extra={
                    'function_name': name,
                    'execution_time': execution_time,
                    'result': result if include_result else '<隐藏>',
                    'success': True,
                    'tags': all_tags
                })

                return result

            except Exception as e:
                # 计算执行时间（即使失败）
                execution_time = time.time() - start_time

                # 记录错误指标
                error_tags = {**all_tags, 'error_type': type(e).__name__}

                metrics_service.record_histogram(
                    f"{name}_duration",
                    execution_time,
                    error_tags
                )

                metrics_service.increment_counter(
                    f"{name}_error_total",
                    error_tags
                )

                # 记录错误日志
                logger.error(f"函数执行失败: {name}", exception=e, extra={
                    'function_name': name,
                    'execution_time': execution_time,
                    'error_type': type(e).__name__,
                    'success': False,
                    'tags': all_tags
                })

                raise

        return wrapper
    return decorator


def track_metrics(
    counter_name: Optional[str] = None,
    gauge_name: Optional[str] = None,
    histogram_name: Optional[str] = None,
    tags: Optional[Dict[str, str]] = None
):
    """指标跟踪装饰器

    Args:
        counter_name: 计数器名称
        gauge_name: 测量值名称
        histogram_name: 直方图名称
        tags: 标签
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            middleware = get_monitoring_middleware()
            metrics_service = middleware._metrics_service

            # 获取上下文
            context = middleware.get_request_context()
            all_tags = {**context, **(tags or {})}

            try:
                # 记录计数器
                if counter_name:
                    metrics_service.increment_counter(counter_name, all_tags)

                # 执行函数
                result = func(*args, **kwargs)

                # 记录测量值（如果结果是数字）
                if gauge_name and isinstance(result, (int, float)):
                    metrics_service.record_metric(gauge_name, result, all_tags)

                # 记录直方图（如果结果是数字）
                if histogram_name and isinstance(result, (int, float)):
                    metrics_service.record_histogram(histogram_name, result, all_tags)

                return result

            except Exception:
                # 记录错误计数
                if counter_name:
                    error_tags = {**all_tags, 'status': 'error'}
                    metrics_service.increment_counter(f"{counter_name}_error", error_tags)

                raise

        return wrapper
    return decorator


class RAGMetricsTracker:
    """RAG特定指标跟踪器"""

    def __init__(self, metrics_service: Optional[MetricsService] = None):
        """初始化RAG指标跟踪器

        Args:
            metrics_service: 指标服务实例
        """
        self._metrics_service = metrics_service or get_metrics_service()

    def track_document_processing(self,
                                document_count: int,
                                processing_time: float,
                                **tags):
        """跟踪文档处理指标

        Args:
            document_count: 处理的文档数量
            processing_time: 处理时间
            **tags: 额外标签
        """
        base_tags = {'operation': 'document_processing', **tags}

        self._metrics_service.record_metric(
            'rag_documents_processed',
            document_count,
            base_tags
        )

        self._metrics_service.record_histogram(
            'rag_document_processing_time',
            processing_time,
            base_tags
        )

        self._metrics_service.increment_counter(
            'rag_document_processing_total',
            base_tags
        )

    def track_query_processing(self,
                             query: str,
                             response_time: float,
                             retrieval_count: int,
                             context_length: int,
                             **tags):
        """跟踪查询处理指标

        Args:
            query: 查询内容
            response_time: 响应时间
            retrieval_count: 检索文档数量
            context_length: 上下文长度
            **tags: 额外标签
        """
        base_tags = {
            'operation': 'query_processing',
            'query_length_bucket': self._get_length_bucket(len(query)),
            **tags
        }

        # 使用现有的record_rag_metrics方法
        self._metrics_service.record_rag_metrics(
            query=query,
            response_time=response_time,
            retrieval_count=retrieval_count,
            context_length=context_length,
            **base_tags
        )

    def track_vector_operation(self,
                             operation: str,
                             vector_count: int,
                             operation_time: float,
                             **tags):
        """跟踪向量操作指标

        Args:
            operation: 操作类型 (index, search, etc.)
            vector_count: 向量数量
            operation_time: 操作时间
            **tags: 额外标签
        """
        base_tags = {
            'operation': f'vector_{operation}',
            'vector_count_bucket': self._get_count_bucket(vector_count),
            **tags
        }

        self._metrics_service.record_metric(
            f'rag_vector_{operation}_count',
            vector_count,
            base_tags
        )

        self._metrics_service.record_histogram(
            f'rag_vector_{operation}_time',
            operation_time,
            base_tags
        )

        self._metrics_service.increment_counter(
            f'rag_vector_{operation}_total',
            base_tags
        )

    def _get_length_bucket(self, length: int) -> str:
        """获取长度分桶

        Args:
            length: 长度值

        Returns:
            分桶名称
        """
        if length <= 50:
            return 'short'
        elif length <= 200:
            return 'medium'
        elif length <= 500:
            return 'long'
        else:
            return 'very_long'

    def _get_count_bucket(self, count: int) -> str:
        """获取计数分桶

        Args:
            count: 计数值

        Returns:
            分桶名称
        """
        if count <= 5:
            return 'small'
        elif count <= 20:
            return 'medium'
        elif count <= 100:
            return 'large'
        else:
            return 'very_large'


# RAG指标跟踪器实例
_rag_tracker_instance: Optional[RAGMetricsTracker] = None
_rag_tracker_lock = threading.Lock()


def get_rag_metrics_tracker() -> RAGMetricsTracker:
    """获取RAG指标跟踪器单例实例"""
    global _rag_tracker_instance

    if _rag_tracker_instance is None:
        with _rag_tracker_lock:
            if _rag_tracker_instance is None:
                _rag_tracker_instance = RAGMetricsTracker()

    return _rag_tracker_instance
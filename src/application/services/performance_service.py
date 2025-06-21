"""
性能服务
集成监控、缓存、扩展和优化功能的核心服务
"""

import threading
import time
from typing import Dict, Any, Optional, List
from concurrent.futures import ThreadPoolExecutor, Future

from src.infrastructure import (
    get_metrics_service,
    get_health_check_service,
    get_cache_service,
    get_extension_registry,
    get_auto_scaler,
    get_production_config,
    cache_rag_query,
    cache_document_processing
)
from src.infrastructure.logging.logging_service import get_logging_service


class PerformanceService:
    """性能服务

    统一管理系统性能相关功能:
    - 性能监控和指标收集
    - 智能缓存管理
    - 自动扩缩容
    - 生产环境优化
    """

    def __init__(self):
        """初始化性能服务"""
        self._logger = get_logging_service()

        # 基础设施服务
        self._metrics = get_metrics_service()
        self._health_check = get_health_check_service()
        self._cache = get_cache_service()
        self._extensions = get_extension_registry()
        self._auto_scaler = get_auto_scaler()
        self._production_config = get_production_config()

        # 性能统计
        self._performance_stats = {
            'service_start_time': time.time(),
            'total_requests': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'errors': 0,
            'average_response_time': 0.0
        }

        # 线程池
        self._thread_pool = ThreadPoolExecutor(
            max_workers=self._production_config.performance.thread_pool_size,
            thread_name_prefix="performance_service"
        )

        # 锁
        self._stats_lock = threading.RLock()

        # 优化配置
        self._optimize_for_production()

        self._logger.info("性能服务初始化完成")

    def _optimize_for_production(self):
        """针对生产环境优化"""
        try:
            # 应用生产配置优化
            self._production_config.optimize_for_production()

            # 记录配置摘要
            config_summary = self._production_config.get_config_summary()
            self._logger.info(f"生产环境配置已优化:\n{config_summary}")

        except Exception as e:
            self._logger.error("生产环境优化失败", exception=e)

    @cache_rag_query(ttl=3600)
    def process_rag_query(self, query: str, **kwargs) -> Dict[str, Any]:
        """处理RAG查询（带缓存优化）

        Args:
            query: 查询文本
            **kwargs: 其他参数

        Returns:
            查询结果
        """
        start_time = time.time()

        try:
            with self._stats_lock:
                self._performance_stats['total_requests'] += 1

            # 记录请求指标
            self._metrics.increment_counter('rag_query_requests_total')

            # 扩展点: 查询处理前
            self._extensions.execute_extension_point(
                'query.before_processing',
                {'query': query, 'kwargs': kwargs}
            )

            # 这里应该调用实际的RAG处理逻辑
            # 暂时返回模拟结果
            result = {
                'response': f"处理查询: {query}",
                'sources': [],
                'processing_time': time.time() - start_time,
                'cached': False
            }

            # 扩展点: 查询处理后
            self._extensions.execute_extension_point(
                'query.after_processing',
                {'query': query, 'result': result}
            )

            # 更新性能统计
            processing_time = time.time() - start_time
            self._update_performance_stats(processing_time, success=True)

            # 记录性能指标
            self._metrics.record_histogram('rag_query_duration', processing_time)

            return result

        except Exception as e:
            # 更新错误统计
            self._update_performance_stats(0, success=False)

            # 记录错误指标
            self._metrics.increment_counter('rag_query_errors_total')

            self._logger.error(f"RAG查询处理失败: {query}", exception=e)
            raise

    @cache_document_processing(ttl=7200)
    def process_document(self, document_id: str, **kwargs) -> Dict[str, Any]:
        """处理文档（带缓存优化）

        Args:
            document_id: 文档ID
            **kwargs: 其他参数

        Returns:
            处理结果
        """
        start_time = time.time()

        try:
            # 记录请求指标
            self._metrics.increment_counter('document_processing_requests_total')

            # 扩展点: 文档处理前
            self._extensions.execute_extension_point(
                'document.before_processing',
                {'document_id': document_id, 'kwargs': kwargs}
            )

            # 这里应该调用实际的文档处理逻辑
            # 暂时返回模拟结果
            result = {
                'document_id': document_id,
                'chunks': [],
                'embeddings': [],
                'processing_time': time.time() - start_time,
                'cached': False
            }

            # 扩展点: 文档处理后
            self._extensions.execute_extension_point(
                'document.after_processing',
                {'document_id': document_id, 'result': result}
            )

            # 记录性能指标
            processing_time = time.time() - start_time
            self._metrics.record_histogram('document_processing_duration', processing_time)

            return result

        except Exception as e:
            # 记录错误指标
            self._metrics.increment_counter('document_processing_errors_total')

            self._logger.error(f"文档处理失败: {document_id}", exception=e)
            raise

    def submit_async_task(self, func, *args, **kwargs) -> Future:
        """提交异步任务

        Args:
            func: 任务函数
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            Future对象
        """
        return self._thread_pool.submit(func, *args, **kwargs)

    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计

        Returns:
            性能统计字典
        """
        with self._stats_lock:
            uptime = time.time() - self._performance_stats['service_start_time']

            # 获取系统健康状态
            health_status = self._health_check.get_health_status()

            # 获取缓存统计
            cache_stats = self._cache.get_stats()

            # 获取自动扩缩容统计
            scaling_stats = self._auto_scaler.get_current_stats()

            return {
                'service_uptime': uptime,
                'total_requests': self._performance_stats['total_requests'],
                'cache_hits': self._performance_stats['cache_hits'],
                'cache_misses': self._performance_stats['cache_misses'],
                'cache_hit_rate': (
                    self._performance_stats['cache_hits'] /
                    max(1, self._performance_stats['cache_hits'] + self._performance_stats['cache_misses'])
                ),
                'errors': self._performance_stats['errors'],
                'error_rate': (
                    self._performance_stats['errors'] /
                    max(1, self._performance_stats['total_requests'])
                ),
                'average_response_time': self._performance_stats['average_response_time'],
                'health_status': health_status,
                'cache_stats': cache_stats,
                'scaling_stats': scaling_stats,
                'thread_pool_active': self._thread_pool._threads,
                'production_config': self._production_config.get_all_config()
            }

    def _update_performance_stats(self, response_time: float, success: bool = True):
        """更新性能统计

        Args:
            response_time: 响应时间
            success: 是否成功
        """
        with self._stats_lock:
            if not success:
                self._performance_stats['errors'] += 1
                return

            # 更新平均响应时间
            total_requests = self._performance_stats['total_requests']
            current_avg = self._performance_stats['average_response_time']

            new_avg = ((current_avg * (total_requests - 1)) + response_time) / total_requests
            self._performance_stats['average_response_time'] = new_avg

    def optimize_cache_performance(self):
        """优化缓存性能"""
        try:
            # 获取缓存统计
            cache_stats = self._cache.get_stats()

            # 如果命中率过低，调整缓存策略
            if cache_stats.hit_rate < 0.7:  # 命中率低于70%
                self._logger.warning(f"缓存命中率过低: {cache_stats.hit_rate:.2%}")

                # 增加缓存大小
                current_size = self._production_config.cache.max_cache_size_mb
                new_size = min(current_size * 1.2, 1024)  # 最大1GB
                self._production_config.cache.max_cache_size_mb = int(new_size)

                self._logger.info(f"调整缓存大小: {current_size}MB -> {new_size}MB")

        except Exception as e:
            self._logger.error("缓存性能优化失败", exception=e)

    def get_system_metrics(self) -> Dict[str, Any]:
        """获取系统指标

        Returns:
            系统指标字典
        """
        try:
            # 获取所有指标
            metrics = self._metrics.get_all_metrics()

            # 获取健康检查结果
            health = self._health_check.get_health_status()

            # 获取扩缩容状态
            scaling = self._auto_scaler.get_current_stats()

            return {
                'timestamp': time.time(),
                'metrics': metrics,
                'health': health,
                'scaling': scaling,
                'performance': self.get_performance_stats()
            }

        except Exception as e:
            self._logger.error("获取系统指标失败", exception=e)
            return {'error': str(e)}

    def validate_system_health(self) -> bool:
        """验证系统健康状态

        Returns:
            系统是否健康
        """
        try:
            health_status = self._health_check.get_health_status()
            return health_status.get('overall_health', 0) > 0.8

        except Exception as e:
            self._logger.error("系统健康检查失败", exception=e)
            return False

    def shutdown(self):
        """关闭性能服务"""
        try:
            # 关闭线程池
            self._thread_pool.shutdown(wait=True)

            # 保存配置
            self._production_config.save_to_files()

            self._logger.info("性能服务已关闭")

        except Exception as e:
            self._logger.error("性能服务关闭失败", exception=e)


# 全局性能服务实例
_performance_service_instance: Optional[PerformanceService] = None
_performance_service_lock = threading.Lock()


def get_performance_service() -> PerformanceService:
    """获取性能服务单例实例"""
    global _performance_service_instance

    if _performance_service_instance is None:
        with _performance_service_lock:
            if _performance_service_instance is None:
                _performance_service_instance = PerformanceService()

    return _performance_service_instance
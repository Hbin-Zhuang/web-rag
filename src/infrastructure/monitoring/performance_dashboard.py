"""
性能监控仪表板组件
提供实时性能监控的Web UI界面
"""

import json
import gradio as gr
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple

from .metrics_service import get_metrics_service, MetricsService
from .health_check_service import get_health_check_service, HealthCheckService, HealthStatus
from ..logging.logging_service import get_logging_service, ILoggingService


class PerformanceDashboard:
    """性能监控仪表板"""

    def __init__(self,
                 metrics_service: Optional[MetricsService] = None,
                 health_service: Optional[HealthCheckService] = None,
                 logger_service: Optional[ILoggingService] = None):
        """初始化性能仪表板

        Args:
            metrics_service: 指标服务实例
            health_service: 健康检查服务实例
            logger_service: 日志服务实例
        """
        self._metrics_service = metrics_service or get_metrics_service()
        self._health_service = health_service or get_health_check_service()
        self._logger = logger_service or get_logging_service()

        # UI组件
        self._components = {}

        self._logger.info("性能监控仪表板初始化完成")

    def create_dashboard(self) -> gr.Blocks:
        """创建仪表板UI

        Returns:
            Gradio Blocks组件
        """
        with gr.Blocks(title="性能监控仪表板", theme=gr.themes.Soft()) as dashboard:
            gr.Markdown("# 🚀 系统性能监控仪表板")

            with gr.Tabs():
                # 系统健康状态页
                with gr.TabItem("🩺 系统健康", id="health"):
                    self._create_health_tab()

                # 性能指标页
                with gr.TabItem("📊 性能指标", id="metrics"):
                    self._create_metrics_tab()

                # RAG特定指标页
                with gr.TabItem("🤖 RAG指标", id="rag"):
                    self._create_rag_metrics_tab()

                # 系统资源页
                with gr.TabItem("💻 系统资源", id="resources"):
                    self._create_resources_tab()

        return dashboard

    def _create_health_tab(self):
        """创建健康状态标签页"""
        with gr.Row():
            with gr.Column(scale=2):
                gr.Markdown("## 整体健康状态")

                # 整体状态显示
                self._components['overall_status'] = gr.Markdown(
                    "🔄 正在检查系统健康状态...",
                    elem_id="overall-status"
                )

                # 系统运行时间
                self._components['uptime'] = gr.Markdown(
                    "⏱️ 系统运行时间: 计算中...",
                    elem_id="system-uptime"
                )

            with gr.Column(scale=1):
                # 健康检查按钮
                refresh_health_btn = gr.Button("🔄 刷新健康状态", variant="primary")

        # 组件健康详情
        gr.Markdown("## 组件健康详情")
        self._components['component_health'] = gr.JSON(
            label="组件状态详情",
            show_label=True
        )

        # 绑定事件
        refresh_health_btn.click(
            fn=self._refresh_health_status,
            outputs=[
                self._components['overall_status'],
                self._components['uptime'],
                self._components['component_health']
            ]
        )

        # 自动刷新（每30秒）
        dashboard_refresh = gr.Timer(30)
        dashboard_refresh.tick(
            fn=self._refresh_health_status,
            outputs=[
                self._components['overall_status'],
                self._components['uptime'],
                self._components['component_health']
            ]
        )

    def _create_metrics_tab(self):
        """创建性能指标标签页"""
        with gr.Row():
            with gr.Column(scale=3):
                gr.Markdown("## 实时性能指标")

                # 指标搜索
                metric_search = gr.Textbox(
                    label="指标名称过滤",
                    placeholder="输入指标名称进行过滤...",
                    value=""
                )

                # 指标数据显示
                self._components['metrics_data'] = gr.JSON(
                    label="性能指标数据",
                    show_label=True
                )

            with gr.Column(scale=1):
                # 控制面板
                gr.Markdown("### 控制面板")

                refresh_metrics_btn = gr.Button("🔄 刷新指标", variant="primary")
                export_metrics_btn = gr.Button("📥 导出指标", variant="secondary")
                clear_metrics_btn = gr.Button("🗑️ 清理指标", variant="stop")

                # 清理选项
                clear_hours = gr.Slider(
                    minimum=1,
                    maximum=72,
                    value=24,
                    step=1,
                    label="清理多少小时前的数据"
                )

        # 性能统计摘要
        gr.Markdown("## 性能统计摘要")
        self._components['performance_summary'] = gr.Markdown(
            "📈 性能统计正在加载..."
        )

        # 绑定事件
        refresh_metrics_btn.click(
            fn=self._refresh_metrics,
            inputs=[metric_search],
            outputs=[
                self._components['metrics_data'],
                self._components['performance_summary']
            ]
        )

        export_metrics_btn.click(
            fn=self._export_metrics,
            outputs=[gr.File()]
        )

        clear_metrics_btn.click(
            fn=self._clear_metrics,
            inputs=[clear_hours],
            outputs=[self._components['metrics_data']]
        )

        metric_search.change(
            fn=self._refresh_metrics,
            inputs=[metric_search],
            outputs=[
                self._components['metrics_data'],
                self._components['performance_summary']
            ]
        )

    def _create_rag_metrics_tab(self):
        """创建RAG特定指标标签页"""
        gr.Markdown("## 🤖 RAG系统性能指标")

        with gr.Row():
            with gr.Column():
                # RAG响应时间统计
                self._components['rag_response_time'] = gr.Markdown(
                    "⏱️ RAG响应时间统计正在加载..."
                )

                # RAG查询统计
                self._components['rag_query_stats'] = gr.Markdown(
                    "📊 RAG查询统计正在加载..."
                )

            with gr.Column():
                # 检索质量指标
                self._components['rag_retrieval_quality'] = gr.Markdown(
                    "🎯 检索质量指标正在加载..."
                )

                # 上下文长度统计
                self._components['rag_context_stats'] = gr.Markdown(
                    "📝 上下文长度统计正在加载..."
                )

        # 刷新按钮
        refresh_rag_btn = gr.Button("🔄 刷新RAG指标", variant="primary")

        refresh_rag_btn.click(
            fn=self._refresh_rag_metrics,
            outputs=[
                self._components['rag_response_time'],
                self._components['rag_query_stats'],
                self._components['rag_retrieval_quality'],
                self._components['rag_context_stats']
            ]
        )

    def _create_resources_tab(self):
        """创建系统资源标签页"""
        gr.Markdown("## 💻 系统资源监控")

        with gr.Row():
            with gr.Column():
                # CPU和内存使用率
                self._components['cpu_memory'] = gr.Markdown(
                    "🖥️ CPU和内存使用率正在加载..."
                )

                # 磁盘使用情况
                self._components['disk_usage'] = gr.Markdown(
                    "💾 磁盘使用情况正在加载..."
                )

            with gr.Column():
                # 网络指标
                self._components['network_stats'] = gr.Markdown(
                    "🌐 网络统计正在加载..."
                )

                # 进程信息
                self._components['process_info'] = gr.Markdown(
                    "⚙️ 进程信息正在加载..."
                )

        # 刷新按钮
        refresh_resources_btn = gr.Button("🔄 刷新资源信息", variant="primary")

        refresh_resources_btn.click(
            fn=self._refresh_system_resources,
            outputs=[
                self._components['cpu_memory'],
                self._components['disk_usage'],
                self._components['network_stats'],
                self._components['process_info']
            ]
        )

    def _refresh_health_status(self) -> Tuple[str, str, Dict]:
        """刷新健康状态

        Returns:
            (整体状态, 运行时间, 组件详情)
        """
        try:
            # 获取系统健康状态
            system_health = self._health_service.check_health()

            # 格式化整体状态
            status_emoji = {
                HealthStatus.HEALTHY: "✅",
                HealthStatus.DEGRADED: "⚠️",
                HealthStatus.UNHEALTHY: "❌",
                HealthStatus.UNKNOWN: "❓"
            }

            overall_status = f"{status_emoji.get(system_health.overall_status, '❓')} " \
                           f"系统状态: **{system_health.overall_status.value.upper()}**"

            # 格式化运行时间
            if system_health.uptime:
                hours = int(system_health.uptime // 3600)
                minutes = int((system_health.uptime % 3600) // 60)
                uptime_str = f"⏱️ 系统运行时间: **{hours}小时 {minutes}分钟**"
            else:
                uptime_str = "⏱️ 系统运行时间: 未知"

            # 转换组件详情为字典
            component_details = system_health.to_dict()

            return overall_status, uptime_str, component_details

        except Exception as e:
            self._logger.error("刷新健康状态失败", exception=e)
            return "❌ 健康状态检查失败", "⏱️ 系统运行时间: 未知", {}

    def _refresh_metrics(self, search_pattern: str = "") -> Tuple[Dict, str]:
        """刷新性能指标

        Args:
            search_pattern: 搜索模式

        Returns:
            (指标数据, 性能摘要)
        """
        try:
            # 获取指标数据
            metrics_data = self._metrics_service.get_metrics(search_pattern if search_pattern else None)

            # 生成性能摘要
            summary_lines = []

            if 'performance_stats' in metrics_data:
                stats = metrics_data['performance_stats']
                summary_lines.append(f"📊 **总指标数**: {stats.get('total_metrics_recorded', 0)}")
                summary_lines.append(f"⚡ **每秒指标**: {stats.get('metrics_per_second', 0):.2f}")

            if 'counters' in metrics_data:
                counter_count = len(metrics_data['counters'])
                summary_lines.append(f"🔢 **计数器数量**: {counter_count}")

            if 'time_series' in metrics_data:
                ts_count = len(metrics_data['time_series'])
                summary_lines.append(f"📈 **时间序列**: {ts_count}")

            if 'histograms' in metrics_data:
                hist_count = len(metrics_data['histograms'])
                summary_lines.append(f"📊 **直方图**: {hist_count}")

            summary_lines.append(f"🕐 **最后更新**: {datetime.now().strftime('%H:%M:%S')}")

            performance_summary = "\n".join(summary_lines)

            return metrics_data, performance_summary

        except Exception as e:
            self._logger.error("刷新指标失败", exception=e)
            return {}, "❌ 指标刷新失败"

    def _export_metrics(self) -> Optional[str]:
        """导出指标数据

        Returns:
            导出文件路径
        """
        try:
            import tempfile
            import os

            # 创建临时文件
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            temp_dir = tempfile.gettempdir()
            file_path = os.path.join(temp_dir, f"metrics_export_{timestamp}.json")

            # 导出指标
            if self._metrics_service.export_metrics(file_path):
                return file_path
            else:
                return None

        except Exception as e:
            self._logger.error("导出指标失败", exception=e)
            return None

    def _clear_metrics(self, hours: int) -> Dict:
        """清理指标数据

        Args:
            hours: 清理多少小时前的数据

        Returns:
            清理后的指标数据
        """
        try:
            # 清理指标
            self._metrics_service.clear_metrics(hours)

            # 返回更新后的指标数据
            return self._metrics_service.get_metrics()

        except Exception as e:
            self._logger.error("清理指标失败", exception=e)
            return {}

    def _refresh_rag_metrics(self) -> Tuple[str, str, str, str]:
        """刷新RAG指标

        Returns:
            (响应时间, 查询统计, 检索质量, 上下文统计)
        """
        try:
            metrics_data = self._metrics_service.get_metrics("rag")

            # RAG响应时间统计
            response_time_text = "⏱️ **RAG响应时间统计**\n"
            if 'histograms' in metrics_data and 'rag_response_time' in metrics_data['histograms']:
                stats = metrics_data['histograms']['rag_response_time']
                response_time_text += f"- 平均响应时间: {stats['avg']:.2f}秒\n"
                response_time_text += f"- 最快响应: {stats['min']:.2f}秒\n"
                response_time_text += f"- 最慢响应: {stats['max']:.2f}秒\n"
                response_time_text += f"- 总查询次数: {stats['count']}"
            else:
                response_time_text += "暂无响应时间数据"

            # RAG查询统计
            query_stats_text = "📊 **RAG查询统计**\n"
            if 'counters' in metrics_data and 'rag_queries_total' in metrics_data['counters']:
                total_queries = metrics_data['counters']['rag_queries_total']
                query_stats_text += f"- 总查询数: {total_queries}\n"
                query_stats_text += f"- 今日查询数: 待实现\n"
                query_stats_text += f"- 查询成功率: 待实现"
            else:
                query_stats_text += "暂无查询统计数据"

            # 检索质量指标
            retrieval_quality_text = "🎯 **检索质量指标**\n"
            if 'time_series' in metrics_data and 'rag_retrieval_count' in metrics_data['time_series']:
                retrieval_data = metrics_data['time_series']['rag_retrieval_count']
                if retrieval_data:
                    avg_retrieval = sum(d['value'] for d in retrieval_data) / len(retrieval_data)
                    retrieval_quality_text += f"- 平均检索文档数: {avg_retrieval:.1f}\n"
                    retrieval_quality_text += f"- 检索相关性: 待实现\n"
                    retrieval_quality_text += f"- 命中率: 待实现"
                else:
                    retrieval_quality_text += "暂无检索数据"
            else:
                retrieval_quality_text += "暂无检索质量数据"

            # 上下文长度统计
            context_stats_text = "📝 **上下文长度统计**\n"
            if 'time_series' in metrics_data and 'rag_context_length' in metrics_data['time_series']:
                context_data = metrics_data['time_series']['rag_context_length']
                if context_data:
                    avg_length = sum(d['value'] for d in context_data) / len(context_data)
                    max_length = max(d['value'] for d in context_data)
                    min_length = min(d['value'] for d in context_data)
                    context_stats_text += f"- 平均上下文长度: {avg_length:.0f}字符\n"
                    context_stats_text += f"- 最长上下文: {max_length:.0f}字符\n"
                    context_stats_text += f"- 最短上下文: {min_length:.0f}字符"
                else:
                    context_stats_text += "暂无上下文数据"
            else:
                context_stats_text += "暂无上下文长度数据"

            return response_time_text, query_stats_text, retrieval_quality_text, context_stats_text

        except Exception as e:
            self._logger.error("刷新RAG指标失败", exception=e)
            error_msg = "❌ RAG指标刷新失败"
            return error_msg, error_msg, error_msg, error_msg

    def _refresh_system_resources(self) -> Tuple[str, str, str, str]:
        """刷新系统资源信息

        Returns:
            (CPU内存, 磁盘使用, 网络统计, 进程信息)
        """
        try:
            # 尝试获取系统资源信息
            try:
                import psutil

                # CPU和内存
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                cpu_memory_text = f"🖥️ **CPU和内存使用率**\n" \
                                f"- CPU使用率: {cpu_percent:.1f}%\n" \
                                f"- 内存使用率: {memory.percent:.1f}%\n" \
                                f"- 可用内存: {memory.available / (1024**3):.1f}GB\n" \
                                f"- 总内存: {memory.total / (1024**3):.1f}GB"

                # 磁盘使用
                disk = psutil.disk_usage('/')
                disk_text = f"💾 **磁盘使用情况**\n" \
                          f"- 磁盘使用率: {disk.percent:.1f}%\n" \
                          f"- 可用空间: {disk.free / (1024**3):.1f}GB\n" \
                          f"- 总空间: {disk.total / (1024**3):.1f}GB"

                # 网络统计（简单版本）
                network_text = f"🌐 **网络统计**\n" \
                             f"- 网络接口数: {len(psutil.net_if_addrs())}\n" \
                             f"- 网络连接数: {len(psutil.net_connections())}"

                # 进程信息
                process = psutil.Process()
                process_text = f"⚙️ **当前进程信息**\n" \
                             f"- 进程ID: {process.pid}\n" \
                             f"- 进程内存: {process.memory_info().rss / (1024**2):.1f}MB\n" \
                             f"- 进程CPU: {process.cpu_percent():.1f}%\n" \
                             f"- 线程数: {process.num_threads()}"

            except ImportError:
                # psutil不可用时的fallback
                cpu_memory_text = "🖥️ **CPU和内存使用率**\n系统监控不可用（缺少psutil包）"
                disk_text = "💾 **磁盘使用情况**\n磁盘监控不可用（缺少psutil包）"
                network_text = "🌐 **网络统计**\n网络监控不可用（缺少psutil包）"
                process_text = "⚙️ **进程信息**\n进程监控不可用（缺少psutil包）"

            return cpu_memory_text, disk_text, network_text, process_text

        except Exception as e:
            self._logger.error("刷新系统资源失败", exception=e)
            error_msg = "❌ 系统资源信息获取失败"
            return error_msg, error_msg, error_msg, error_msg


def create_performance_dashboard(
    metrics_service: Optional[MetricsService] = None,
    health_service: Optional[HealthCheckService] = None,
    logger_service: Optional[ILoggingService] = None
) -> PerformanceDashboard:
    """创建性能监控仪表板实例

    Args:
        metrics_service: 指标服务实例
        health_service: 健康检查服务实例
        logger_service: 日志服务实例

    Returns:
        性能监控仪表板实例
    """
    return PerformanceDashboard(
        metrics_service=metrics_service,
        health_service=health_service,
        logger_service=logger_service
    )
"""
扩展点系统实现
提供预定义的扩展点和钩子机制
"""

from typing import Dict, List, Any, Callable, Optional, TypeVar, Generic
from abc import ABC, abstractmethod
from dataclasses import dataclass
import threading

from .plugin_manager import get_plugin_manager
from ..logging.logging_service import get_logging_service


T = TypeVar('T')


@dataclass
class ExtensionContext:
    """扩展上下文"""
    extension_point: str
    data: Dict[str, Any]
    metadata: Dict[str, Any]


class ExtensionHook(ABC, Generic[T]):
    """扩展钩子基类"""

    @abstractmethod
    def execute(self, context: ExtensionContext) -> T:
        """执行扩展钩子

        Args:
            context: 扩展上下文

        Returns:
            扩展结果
        """
        pass


class DocumentProcessingHook(ExtensionHook[Dict[str, Any]]):
    """文档处理扩展钩子"""

    def execute(self, context: ExtensionContext) -> Dict[str, Any]:
        """执行文档处理扩展

        Args:
            context: 包含文档信息的上下文

        Returns:
            处理后的文档数据
        """
        # 默认实现 - 插件可以重写
        return context.data


class QueryProcessingHook(ExtensionHook[Dict[str, Any]]):
    """查询处理扩展钩子"""

    def execute(self, context: ExtensionContext) -> Dict[str, Any]:
        """执行查询处理扩展

        Args:
            context: 包含查询信息的上下文

        Returns:
            处理后的查询数据
        """
        # 默认实现 - 插件可以重写
        return context.data


class ResponseEnhancementHook(ExtensionHook[str]):
    """响应增强扩展钩子"""

    def execute(self, context: ExtensionContext) -> str:
        """执行响应增强扩展

        Args:
            context: 包含响应信息的上下文

        Returns:
            增强后的响应内容
        """
        # 默认实现 - 插件可以重写
        return context.data.get('response', '')


class ExtensionPointRegistry:
    """扩展点注册表"""

    def __init__(self):
        """初始化扩展点注册表"""
        self._logger = get_logging_service()
        self._plugin_manager = get_plugin_manager()
        self._lock = threading.RLock()

        # 预定义扩展点
        self._extension_points = {
            # 文档处理扩展点
            'document.before_upload': [],           # 文档上传前
            'document.after_upload': [],            # 文档上传后
            'document.before_processing': [],       # 文档处理前
            'document.after_processing': [],        # 文档处理后
            'document.before_indexing': [],         # 文档索引前
            'document.after_indexing': [],          # 文档索引后

            # 查询处理扩展点
            'query.before_processing': [],          # 查询处理前
            'query.after_processing': [],           # 查询处理后
            'query.before_retrieval': [],          # 检索前
            'query.after_retrieval': [],           # 检索后
            'query.before_generation': [],         # 生成前
            'query.after_generation': [],          # 生成后

            # 响应处理扩展点
            'response.before_formatting': [],       # 响应格式化前
            'response.after_formatting': [],        # 响应格式化后
            'response.before_delivery': [],         # 响应交付前
            'response.after_delivery': [],          # 响应交付后

            # 系统级扩展点
            'system.startup': [],                   # 系统启动
            'system.shutdown': [],                  # 系统关闭
            'system.error': [],                     # 系统错误
            'system.maintenance': [],               # 系统维护

            # RAG特定扩展点
            'rag.context_enhancement': [],          # 上下文增强
            'rag.answer_validation': [],            # 答案验证
            'rag.source_filtering': [],             # 来源过滤
            'rag.relevance_scoring': [],            # 相关性评分
        }

        self._logger.info("扩展点注册表初始化完成")

    def register_hook(self, extension_point: str, hook: ExtensionHook) -> bool:
        """注册扩展钩子

        Args:
            extension_point: 扩展点名称
            hook: 扩展钩子实例

        Returns:
            是否成功注册
        """
        with self._lock:
            try:
                if extension_point not in self._extension_points:
                    self._extension_points[extension_point] = []

                self._extension_points[extension_point].append(hook)

                # 同时注册到插件管理器
                self._plugin_manager.register_extension_point(
                    extension_point,
                    lambda context: hook.execute(context)
                )

                self._logger.info(f"注册扩展钩子成功: {extension_point}")
                return True

            except Exception as e:
                self._logger.error(f"注册扩展钩子失败: {extension_point}", exception=e)
                return False

    def unregister_hook(self, extension_point: str, hook: ExtensionHook) -> bool:
        """取消注册扩展钩子

        Args:
            extension_point: 扩展点名称
            hook: 扩展钩子实例

        Returns:
            是否成功取消注册
        """
        with self._lock:
            try:
                if extension_point in self._extension_points:
                    hooks = self._extension_points[extension_point]
                    if hook in hooks:
                        hooks.remove(hook)
                        self._logger.info(f"取消注册扩展钩子成功: {extension_point}")
                        return True

                return False

            except Exception as e:
                self._logger.error(f"取消注册扩展钩子失败: {extension_point}", exception=e)
                return False

    def execute_extension_point(self,
                              extension_point: str,
                              data: Dict[str, Any],
                              metadata: Dict[str, Any] = None) -> List[Any]:
        """执行扩展点

        Args:
            extension_point: 扩展点名称
            data: 传递给扩展的数据
            metadata: 扩展元数据

        Returns:
            扩展执行结果列表
        """
        with self._lock:
            try:
                if extension_point not in self._extension_points:
                    self._logger.warning(f"未知扩展点: {extension_point}")
                    return []

                # 创建扩展上下文
                context = ExtensionContext(
                    extension_point=extension_point,
                    data=data,
                    metadata=metadata or {}
                )

                results = []
                hooks = self._extension_points[extension_point]

                for hook in hooks:
                    try:
                        result = hook.execute(context)
                        results.append(result)
                    except Exception as e:
                        self._logger.error(f"执行扩展钩子失败: {extension_point}", exception=e)

                # 同时调用插件管理器的扩展点
                plugin_results = self._plugin_manager.call_extension_point(
                    extension_point, context
                )
                results.extend(plugin_results)

                return results

            except Exception as e:
                self._logger.error(f"执行扩展点失败: {extension_point}", exception=e)
                return []

    def get_extension_points(self) -> List[str]:
        """获取所有扩展点名称

        Returns:
            扩展点名称列表
        """
        with self._lock:
            return list(self._extension_points.keys())

    def get_hook_count(self, extension_point: str) -> int:
        """获取扩展点的钩子数量

        Args:
            extension_point: 扩展点名称

        Returns:
            钩子数量
        """
        with self._lock:
            return len(self._extension_points.get(extension_point, []))


class RAGExtensionPoints:
    """RAG系统扩展点封装类"""

    def __init__(self, registry: ExtensionPointRegistry = None):
        """初始化RAG扩展点

        Args:
            registry: 扩展点注册表实例
        """
        self._registry = registry or get_extension_registry()
        self._logger = get_logging_service()

    def before_document_upload(self, document_data: Dict[str, Any]) -> Dict[str, Any]:
        """文档上传前扩展点

        Args:
            document_data: 文档数据

        Returns:
            处理后的文档数据
        """
        results = self._registry.execute_extension_point(
            'document.before_upload',
            document_data
        )

        # 合并结果
        if results:
            for result in results:
                if isinstance(result, dict):
                    document_data.update(result)

        return document_data

    def after_document_upload(self, document_data: Dict[str, Any]) -> Dict[str, Any]:
        """文档上传后扩展点

        Args:
            document_data: 文档数据

        Returns:
            处理后的文档数据
        """
        results = self._registry.execute_extension_point(
            'document.after_upload',
            document_data
        )

        # 合并结果
        if results:
            for result in results:
                if isinstance(result, dict):
                    document_data.update(result)

        return document_data

    def before_query_processing(self, query_data: Dict[str, Any]) -> Dict[str, Any]:
        """查询处理前扩展点

        Args:
            query_data: 查询数据

        Returns:
            处理后的查询数据
        """
        results = self._registry.execute_extension_point(
            'query.before_processing',
            query_data
        )

        # 合并结果
        if results:
            for result in results:
                if isinstance(result, dict):
                    query_data.update(result)

        return query_data

    def after_query_processing(self, query_data: Dict[str, Any]) -> Dict[str, Any]:
        """查询处理后扩展点

        Args:
            query_data: 查询数据

        Returns:
            处理后的查询数据
        """
        results = self._registry.execute_extension_point(
            'query.after_processing',
            query_data
        )

        # 合并结果
        if results:
            for result in results:
                if isinstance(result, dict):
                    query_data.update(result)

        return query_data

    def enhance_context(self, context_data: Dict[str, Any]) -> Dict[str, Any]:
        """上下文增强扩展点

        Args:
            context_data: 上下文数据

        Returns:
            增强后的上下文数据
        """
        results = self._registry.execute_extension_point(
            'rag.context_enhancement',
            context_data
        )

        # 合并结果
        if results:
            for result in results:
                if isinstance(result, dict):
                    context_data.update(result)

        return context_data

    def validate_answer(self, answer_data: Dict[str, Any]) -> Dict[str, Any]:
        """答案验证扩展点

        Args:
            answer_data: 答案数据

        Returns:
            验证后的答案数据
        """
        results = self._registry.execute_extension_point(
            'rag.answer_validation',
            answer_data
        )

        # 合并结果
        if results:
            for result in results:
                if isinstance(result, dict):
                    answer_data.update(result)

        return answer_data


# 全局扩展点注册表实例
_extension_registry_instance: Optional[ExtensionPointRegistry] = None
_extension_registry_lock = threading.Lock()


def get_extension_registry() -> ExtensionPointRegistry:
    """获取扩展点注册表单例实例"""
    global _extension_registry_instance

    if _extension_registry_instance is None:
        with _extension_registry_lock:
            if _extension_registry_instance is None:
                _extension_registry_instance = ExtensionPointRegistry()

    return _extension_registry_instance


def get_rag_extensions() -> RAGExtensionPoints:
    """获取RAG扩展点实例"""
    return RAGExtensionPoints()
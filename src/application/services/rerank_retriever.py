"""
重排序检索器
封装基础检索器并集成重排序功能，提供增强的文档检索能力
"""

from typing import List, Optional, Dict, Any
from langchain.schema import Document
from langchain.schema.retriever import BaseRetriever

from src.application.services.rerank_service import RerankService
from src.infrastructure import get_logger, get_config


class RerankRetriever(BaseRetriever):
    """重排序检索器

    封装基础检索器，使用LLM重排序提升检索质量
    """

    def __init__(self,
                 base_retriever: BaseRetriever,
                 rerank_service: Optional[RerankService] = None,
                 initial_k: Optional[int] = None,
                 final_k: Optional[int] = None,
                 enable_filename_boost: bool = True,
                 **kwargs):
        """初始化重排序检索器

        Args:
            base_retriever: 基础检索器
            rerank_service: 重排序服务实例
            initial_k: 初始检索数量
            final_k: 最终返回数量
            enable_filename_boost: 是否启用文件名匹配增强
        """
        # 初始化BaseRetriever必需的属性
        object.__setattr__(self, 'tags', kwargs.get('tags', []))
        object.__setattr__(self, 'metadata', kwargs.get('metadata', {}))
        object.__setattr__(self, 'callbacks', kwargs.get('callbacks', None))
        
        # 使用object.__setattr__避免Pydantic字段验证
        object.__setattr__(self, 'base_retriever', base_retriever)
        object.__setattr__(self, 'rerank_service', rerank_service or RerankService())
        object.__setattr__(self, 'config', get_config())
        object.__setattr__(self, 'logger', get_logger())

        # 检索参数
        object.__setattr__(self, 'initial_k', initial_k or self._get_int_config("rerank_initial_k", 8))
        object.__setattr__(self, 'final_k', final_k or self._get_int_config("rerank_final_k", 4))
        object.__setattr__(self, 'enable_filename_boost', enable_filename_boost)

        # 文件名匹配配置
        object.__setattr__(self, 'filename_boost_score', self._get_float_config("filename_boost_score", 0.2))
        object.__setattr__(self, 'filename_match_threshold', self._get_float_config("filename_match_threshold", 0.3))

        self.logger.info("重排序检索器初始化完成", extra={
            "initial_k": self.initial_k,
            "final_k": self.final_k,
            "filename_boost": self.enable_filename_boost
        })

    def _get_int_config(self, key: str, default: int) -> int:
        """获取整数配置值"""
        value = self.config.get_value(key, default)
        try:
            return int(value)
        except (ValueError, TypeError):
            return default

    def _get_float_config(self, key: str, default: float) -> float:
        """获取浮点数配置值"""
        value = self.config.get_value(key, default)
        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    def get_relevant_documents(self, query: str) -> List[Document]:
        """获取相关文档

        Args:
            query: 查询文本

        Returns:
            重排序后的相关文档列表
        """
        try:
            # 1. 使用基础检索器获取初始结果
            initial_docs = self._get_initial_documents(query)

            if not initial_docs:
                self.logger.warning("基础检索器未返回任何文档")
                return []

            self.logger.debug("基础检索完成", extra={
                "query_preview": query[:50],
                "initial_count": len(initial_docs)
            })

            # 2. 应用文件名匹配增强
            if self.enable_filename_boost:
                initial_docs = self._apply_filename_boost(query, initial_docs)

            # 3. 使用重排序服务进行重排序
            reranked_docs = self.rerank_service.rerank_documents(
                query=query,
                documents=initial_docs,
                final_k=self.final_k
            )

            self.logger.info("重排序检索完成", extra={
                "query_preview": query[:50],
                "initial_count": len(initial_docs),
                "final_count": len(reranked_docs)
            })

            return reranked_docs

        except Exception as e:
            self.logger.error("重排序检索失败，降级到基础检索", exception=e)
            # 降级处理：直接使用基础检索器
            return self._get_fallback_documents(query)

    async def aget_relevant_documents(self, query: str) -> List[Document]:
        """异步获取相关文档"""
        # 目前使用同步实现，后续可以优化为真正的异步
        return self.get_relevant_documents(query)

    def _get_relevant_documents(self, query: str) -> List[Document]:
        """BaseRetriever要求的内部方法"""
        return self.get_relevant_documents(query)

    def _get_initial_documents(self, query: str) -> List[Document]:
        """获取初始文档"""
        try:
            # 更新基础检索器的搜索参数
            if hasattr(self.base_retriever, 'search_kwargs'):
                original_k = self.base_retriever.search_kwargs.get('k', 4)
                self.base_retriever.search_kwargs['k'] = self.initial_k

                # 执行检索
                documents = self.base_retriever.get_relevant_documents(query)

                # 恢复原始参数
                self.base_retriever.search_kwargs['k'] = original_k

                return documents
            else:
                # 如果检索器不支持动态参数，直接使用
                return self.base_retriever.get_relevant_documents(query)

        except Exception as e:
            self.logger.error("基础检索失败", exception=e)
            return []

    def _apply_filename_boost(self, query: str, documents: List[Document]) -> List[Document]:
        """应用文件名匹配增强

        Args:
            query: 查询文本
            documents: 文档列表

        Returns:
            增强后的文档列表
        """
        if not documents:
            return documents

        query_lower = query.lower()
        enhanced_docs = []

        for doc in documents:
            # 获取文件名
            source = doc.metadata.get("source", "")
            filename = source.split("/")[-1] if "/" in source else source
            filename_lower = filename.lower()

            # 计算文件名匹配度
            match_score = self._calculate_filename_match(query_lower, filename_lower)

            # 如果匹配度超过阈值，提升文档权重
            if match_score > self.filename_match_threshold:
                # 创建增强的文档副本
                enhanced_doc = Document(
                    page_content=doc.page_content,
                    metadata={
                        **doc.metadata,
                        "filename_match_score": match_score,
                        "boosted": True
                    }
                )
                enhanced_docs.append(enhanced_doc)

                self.logger.debug("文件名匹配增强", extra={
                    "filename": filename,
                    "match_score": match_score,
                    "query": query[:30]
                })
            else:
                enhanced_docs.append(doc)

        # 根据文件名匹配分数重新排序
        enhanced_docs.sort(
            key=lambda x: x.metadata.get("filename_match_score", 0.0),
            reverse=True
        )

        return enhanced_docs

    def _calculate_filename_match(self, query: str, filename: str) -> float:
        """计算文件名匹配度

        Args:
            query: 查询文本（小写）
            filename: 文件名（小写）

        Returns:
            匹配度分数 (0-1)
        """
        if not query or not filename:
            return 0.0

        # 移除文件扩展名
        filename_base = filename.rsplit('.', 1)[0] if '.' in filename else filename

        # 分词
        query_words = set(query.split())
        filename_words = set(filename_base.replace('_', ' ').replace('-', ' ').split())

        if not query_words or not filename_words:
            return 0.0

        # 计算交集比例
        intersection = query_words.intersection(filename_words)
        union = query_words.union(filename_words)

        # Jaccard相似度
        jaccard_score = len(intersection) / len(union) if union else 0.0

        # 检查是否有完全匹配的词
        exact_matches = len(intersection)
        exact_match_bonus = exact_matches / len(query_words) if query_words else 0.0

        # 检查子串匹配
        substring_match = 0.0
        for word in query_words:
            if word in filename_base:
                substring_match += 1
        substring_match = substring_match / len(query_words) if query_words else 0.0

        # 综合评分
        final_score = (jaccard_score * 0.4 + exact_match_bonus * 0.4 + substring_match * 0.2)

        return min(1.0, final_score)

    def _get_fallback_documents(self, query: str) -> List[Document]:
        """降级处理：获取基础检索结果

        Args:
            query: 查询文本

        Returns:
            基础检索结果
        """
        try:
            # 使用基础检索器，限制返回数量
            if hasattr(self.base_retriever, 'search_kwargs'):
                original_k = self.base_retriever.search_kwargs.get('k', 4)
                self.base_retriever.search_kwargs['k'] = self.final_k

                documents = self.base_retriever.get_relevant_documents(query)

                # 恢复原始参数
                self.base_retriever.search_kwargs['k'] = original_k

                return documents
            else:
                documents = self.base_retriever.get_relevant_documents(query)
                return documents[:self.final_k]

        except Exception as e:
            self.logger.error("降级检索也失败", exception=e)
            return []

    def update_config(self, **kwargs):
        """更新配置参数

        Args:
            **kwargs: 配置参数
        """
        if 'initial_k' in kwargs:
            self.initial_k = kwargs['initial_k']
        if 'final_k' in kwargs:
            self.final_k = kwargs['final_k']
        if 'enable_filename_boost' in kwargs:
            self.enable_filename_boost = kwargs['enable_filename_boost']

        self.logger.info("重排序检索器配置已更新", extra=kwargs)

    def get_stats(self) -> Dict[str, Any]:
        """获取检索器统计信息

        Returns:
            统计信息字典
        """
        return {
            "initial_k": self.initial_k,
            "final_k": self.final_k,
            "filename_boost_enabled": self.enable_filename_boost,
            "filename_boost_score": self.filename_boost_score,
            "filename_match_threshold": self.filename_match_threshold
        }

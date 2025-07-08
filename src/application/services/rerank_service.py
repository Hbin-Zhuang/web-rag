"""
重排序服务
使用LLM对检索结果进行重新评分和排序，提高检索准确性
"""

import json
import time
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from langchain.schema import Document
from langchain_google_genai import ChatGoogleGenerativeAI

from src.infrastructure import get_logger, get_config
from src.infrastructure.caching import get_cache_service
from src.infrastructure.caching.document_serializer import get_document_serializer
from src.infrastructure.monitoring import get_metrics_service


class RerankService:
    """LLM重排序服务

    使用大语言模型对初始检索结果进行相关性评分和重新排序
    """

    def __init__(self, config_service=None):
        """初始化重排序服务

        Args:
            config_service: 配置服务实例
        """
        self.config = config_service or get_config()
        self.logger = get_logger()
        self.cache_service = get_cache_service()
        self.metrics = get_metrics_service()
        self.serializer = get_document_serializer()

        # 重排序配置
        self.use_rerank = self._get_bool_config("use_rerank", True)
        self.initial_k = self._get_int_config("rerank_initial_k", 8)
        self.final_k = self._get_int_config("rerank_final_k", 4)
        self.score_threshold = self._get_float_config("rerank_score_threshold", 0.6)
        self.cache_ttl = self._get_int_config("rerank_cache_ttl", 3600)
        self.temperature = self._get_float_config("rerank_temperature", 0.1)
        self.max_retries = self._get_int_config("rerank_max_retries", 3)

        # 多样性检索配置
        self.use_diversity = self._get_bool_config("use_diversity_retrieval", True)
        self.max_per_source = self._get_int_config("diversity_max_per_source", 3)
        self.min_sources = self._get_int_config("diversity_min_sources", 2)

        # 创建LLM实例
        self.llm = self._create_llm()

        self.logger.info("重排序服务初始化完成", extra={
            "use_rerank": self.use_rerank,
            "initial_k": self.initial_k,
            "final_k": self.final_k,
            "use_diversity": self.use_diversity
        })

    def _get_bool_config(self, key: str, default: bool) -> bool:
        """获取布尔配置值"""
        value = self.config.get_value(key, default)
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on')
        return bool(value)

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

    def _create_llm(self) -> Optional[ChatGoogleGenerativeAI]:
        """创建LLM实例"""
        try:
            api_key = self.config.get_value("google_api_key")
            if not api_key:
                self.logger.error("Google API Key未配置")
                return None

            model_name = self.config.get_value("chat_model", "gemini-2.0-flash-001")

            llm = ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=api_key,
                temperature=self.temperature,
                convert_system_message_to_human=True
            )

            self.logger.info(f"重排序LLM创建成功: {model_name}")
            return llm

        except Exception as e:
            self.logger.error("重排序LLM创建失败", exception=e)
            return None

    def rerank_documents(self, query: str, documents: List[Document],
                        final_k: Optional[int] = None) -> List[Document]:
        """对文档进行重排序

        Args:
            query: 查询文本
            documents: 待重排序的文档列表
            final_k: 最终返回的文档数量

        Returns:
            重排序后的文档列表
        """
        if not self.use_rerank or not self.llm:
            self.logger.info("重排序功能未启用，返回原始结果")
            return documents[:final_k or self.final_k]

        if not documents:
            return []

        final_k = final_k or self.final_k

        # 检查缓存
        cache_key = self._generate_cache_key(query, documents, final_k)
        cached_result = self._get_cached_result(cache_key)
        if cached_result:
            self.metrics.increment_counter('rerank_cache_hit_total')
            return cached_result

        self.metrics.increment_counter('rerank_cache_miss_total')

        start_time = time.time()

        try:
            # 应用多样性感知检索
            if self.use_diversity:
                documents = self._apply_diversity_retrieval(documents)

            # 执行重排序
            reranked_docs = self._perform_rerank(query, documents, final_k)

            # 缓存结果
            self._cache_result(cache_key, reranked_docs)

            # 记录指标
            processing_time = time.time() - start_time
            self.metrics.record_histogram('rerank_duration', processing_time)
            self.metrics.increment_counter('rerank_success_total')

            self.logger.info("重排序完成", extra={
                "query_preview": query[:50],
                "input_docs": len(documents),
                "output_docs": len(reranked_docs),
                "processing_time": processing_time
            })

            return reranked_docs

        except Exception as e:
            self.metrics.increment_counter('rerank_error_total')
            self.logger.error("重排序失败，返回原始结果", exception=e)
            return documents[:final_k]

    def _apply_diversity_retrieval(self, documents: List[Document]) -> List[Document]:
        """应用多样性感知检索策略

        Args:
            documents: 原始文档列表

        Returns:
            多样性处理后的文档列表
        """
        if not documents:
            return documents

        # 按文档源分组
        source_groups = {}
        for doc in documents:
            source = doc.metadata.get("source", "unknown")
            # 提取文件名作为源标识
            if "/" in source:
                source = source.split("/")[-1]

            if source not in source_groups:
                source_groups[source] = []
            source_groups[source].append(doc)

        # 如果源数量少于最小要求，直接返回
        if len(source_groups) < self.min_sources:
            return documents

        # 轮询选择策略
        result = []
        max_rounds = self.max_per_source

        for round_num in range(max_rounds):
            for source, docs in source_groups.items():
                if round_num < len(docs):
                    result.append(docs[round_num])

        self.logger.debug("多样性检索应用完成", extra={
            "original_count": len(documents),
            "diverse_count": len(result),
            "source_count": len(source_groups)
        })

        return result

    def _perform_rerank(self, query: str, documents: List[Document],
                       final_k: int) -> List[Document]:
        """执行重排序

        Args:
            query: 查询文本
            documents: 文档列表
            final_k: 最终返回数量

        Returns:
            重排序后的文档列表
        """
        if len(documents) <= final_k:
            return documents

        # 构建重排序提示
        prompt = self._build_rerank_prompt(query, documents)

        # 重试机制
        for attempt in range(self.max_retries):
            try:
                response = self.llm.invoke(prompt)
                scores = self._parse_scores(response.content, len(documents))

                if scores:
                    # 根据评分排序
                    scored_docs = list(zip(documents, scores))
                    scored_docs.sort(key=lambda x: x[1], reverse=True)

                    # 过滤低分文档并返回top-k
                    filtered_docs = [
                        doc for doc, score in scored_docs
                        if score >= self.score_threshold
                    ]

                    return filtered_docs[:final_k]

            except Exception as e:
                self.logger.warning(f"重排序尝试 {attempt + 1} 失败", exception=e)
                if attempt == self.max_retries - 1:
                    raise

        return documents[:final_k]

    def _build_rerank_prompt(self, query: str, documents: List[Document]) -> str:
        """构建重排序提示"""
        doc_texts = []
        for i, doc in enumerate(documents):
            # 包含文件名信息
            source = doc.metadata.get("source", "未知文档")
            if "/" in source:
                source = source.split("/")[-1]

            content_preview = doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content
            doc_texts.append(f"文档{i+1} (来源: {source}):\n{content_preview}")

        prompt = f"""
请根据查询内容对以下文档进行相关性评分。

查询: {query}

文档列表:
{chr(10).join(doc_texts)}

请为每个文档打分(0-1之间，1表示最相关)，考虑以下因素：
1. 内容与查询的语义相关性
2. 文档来源/文件名与查询的匹配度
3. 信息的完整性和准确性

请只返回分数，格式为: [分数1, 分数2, 分数3, ...]
例如: [0.9, 0.7, 0.3, 0.8]
"""
        return prompt

    def _parse_scores(self, response: str, expected_count: int) -> Optional[List[float]]:
        """解析LLM返回的评分"""
        try:
            # 尝试提取JSON格式的分数
            import re
            pattern = r'\[([\d\.,\s]+)\]'
            match = re.search(pattern, response)

            if match:
                scores_str = match.group(1)
                scores = [float(s.strip()) for s in scores_str.split(',')]

                if len(scores) == expected_count:
                    # 确保分数在0-1范围内
                    scores = [max(0.0, min(1.0, score)) for score in scores]
                    return scores

            self.logger.warning("无法解析重排序评分", extra={
                "response": response[:100],
                "expected_count": expected_count
            })
            return None

        except Exception as e:
            self.logger.error("解析重排序评分失败", exception=e)
            return None

    def _generate_cache_key(self, query: str, documents: List[Document],
                           final_k: int) -> str:
        """生成缓存键"""
        # 使用查询和文档内容的哈希作为缓存键
        content_hash = hashlib.md5(
            (query + str(final_k) + str([doc.page_content[:100] for doc in documents])).encode()
        ).hexdigest()
        return f"rerank:{content_hash}"

    def _get_cached_result(self, cache_key: str) -> Optional[List[Document]]:
        """获取缓存结果"""
        try:
            if hasattr(self.cache_service, 'get'):
                cached_data = self.cache_service.get(cache_key)
                if cached_data:
                    # 使用序列化器反序列化Document对象
                    if isinstance(cached_data, list):
                        return self.serializer.deserialize_documents_from_dict(cached_data)
                    elif isinstance(cached_data, str):
                        return self.serializer.deserialize_documents(cached_data)
        except Exception as e:
            self.logger.debug(f"获取重排序缓存失败: {str(e)}")
        return None

    def _cache_result(self, cache_key: str, documents: List[Document]):
        """缓存结果"""
        try:
            # 使用序列化器序列化Document对象
            serializable_docs = self.serializer.serialize_documents_to_dict(documents)
            if hasattr(self.cache_service, 'set'):
                self.cache_service.set(cache_key, serializable_docs, self.cache_ttl)
            elif hasattr(self.cache_service, 'put'):
                self.cache_service.put(cache_key, serializable_docs)
        except Exception as e:
            self.logger.debug(f"缓存重排序结果失败: {str(e)}")

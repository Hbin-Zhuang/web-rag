"""
增强检索服务
提供文件名匹配、语义检索和混合检索策略
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from langchain.schema import Document
from langchain_community.vectorstores import Chroma

from src.infrastructure import get_logger, get_config
from src.shared.state.application_state import app_state


class EnhancedRetrievalService:
    """增强检索服务

    提供多种检索策略的组合，包括：
    1. 文件名/标题匹配
    2. 语义向量检索
    3. 混合检索策略
    """

    def __init__(self, config_service=None):
        """初始化增强检索服务"""
        self.config = config_service or get_config()
        self.logger = get_logger()

        # 检索配置
        self.enable_filename_search = self.config.get_value("enable_filename_search", True)
        self.filename_weight = self.config.get_value("filename_search_weight", 0.3)
        self.semantic_weight = self.config.get_value("semantic_search_weight", 0.7)
        self.min_filename_score = self.config.get_value("min_filename_score", 0.2)

        self.logger.info("增强检索服务初始化完成", extra={
            "filename_search": self.enable_filename_search,
            "filename_weight": self.filename_weight,
            "semantic_weight": self.semantic_weight
        })

    def hybrid_search(self, query: str, k: int = 4) -> List[Document]:
        """混合检索：结合文件名匹配和语义检索

        Args:
            query: 查询文本
            k: 返回文档数量

        Returns:
            检索结果文档列表
        """
        if not app_state.vectorstore:
            self.logger.warning("向量存储未初始化")
            return []

        try:
            # 1. 执行语义检索
            semantic_docs = self._semantic_search(query, k * 2)  # 获取更多候选

            # 2. 如果启用文件名搜索，执行文件名匹配
            if self.enable_filename_search:
                filename_docs = self._filename_search(query, semantic_docs)

                # 3. 合并和重排序结果
                final_docs = self._merge_results(query, semantic_docs, filename_docs, k)
            else:
                final_docs = semantic_docs[:k]

            self.logger.info("混合检索完成", extra={
                "query_preview": query[:50],
                "semantic_count": len(semantic_docs),
                "final_count": len(final_docs)
            })

            return final_docs

        except Exception as e:
            self.logger.error("混合检索失败", exception=e)
            return []

    def _semantic_search(self, query: str, k: int) -> List[Document]:
        """语义向量检索

        Args:
            query: 查询文本
            k: 返回数量

        Returns:
            语义检索结果
        """
        try:
            retriever = app_state.vectorstore.as_retriever(search_kwargs={"k": k})
            documents = retriever.get_relevant_documents(query)

            # 添加语义检索标记
            for doc in documents:
                doc.metadata["search_type"] = "semantic"

            return documents

        except Exception as e:
            self.logger.error("语义检索失败", exception=e)
            return []

    def _filename_search(self, query: str, candidate_docs: List[Document]) -> List[Document]:
        """文件名匹配检索

        Args:
            query: 查询文本
            candidate_docs: 候选文档列表

        Returns:
            文件名匹配的文档列表
        """
        if not candidate_docs:
            return []

        filename_matches = []
        query_lower = query.lower()

        for doc in candidate_docs:
            # 获取文件名
            source = doc.metadata.get("source", "")
            filename = self._extract_filename(source)

            # 计算文件名匹配分数
            match_score = self._calculate_filename_similarity(query_lower, filename.lower())

            if match_score >= self.min_filename_score:
                # 创建增强文档
                enhanced_doc = Document(
                    page_content=doc.page_content,
                    metadata={
                        **doc.metadata,
                        "search_type": "filename",
                        "filename_score": match_score,
                        "filename": filename
                    }
                )
                filename_matches.append(enhanced_doc)

        # 按文件名匹配分数排序
        filename_matches.sort(key=lambda x: x.metadata["filename_score"], reverse=True)

        self.logger.debug("文件名匹配完成", extra={
            "query": query[:30],
            "matches": len(filename_matches)
        })

        return filename_matches

    def _merge_results(self, query: str, semantic_docs: List[Document],
                      filename_docs: List[Document], k: int) -> List[Document]:
        """合并语义检索和文件名匹配结果

        Args:
            query: 查询文本
            semantic_docs: 语义检索结果
            filename_docs: 文件名匹配结果
            k: 最终返回数量

        Returns:
            合并后的结果
        """
        # 创建文档评分字典
        doc_scores = {}

        # 语义检索评分（基于排序位置）
        for i, doc in enumerate(semantic_docs):
            doc_id = self._get_doc_id(doc)
            semantic_score = (len(semantic_docs) - i) / len(semantic_docs)
            doc_scores[doc_id] = {
                "doc": doc,
                "semantic_score": semantic_score,
                "filename_score": 0.0
            }

        # 文件名匹配评分
        for doc in filename_docs:
            doc_id = self._get_doc_id(doc)
            filename_score = doc.metadata.get("filename_score", 0.0)

            if doc_id in doc_scores:
                doc_scores[doc_id]["filename_score"] = filename_score
            else:
                # 新的文档（仅通过文件名匹配找到）
                doc_scores[doc_id] = {
                    "doc": doc,
                    "semantic_score": 0.0,
                    "filename_score": filename_score
                }

        # 计算综合评分
        scored_docs = []
        for doc_id, scores in doc_scores.items():
            combined_score = (
                scores["semantic_score"] * self.semantic_weight +
                scores["filename_score"] * self.filename_weight
            )

            # 更新文档元数据
            doc = scores["doc"]
            doc.metadata.update({
                "combined_score": combined_score,
                "semantic_score": scores["semantic_score"],
                "filename_score": scores["filename_score"]
            })

            scored_docs.append((doc, combined_score))

        # 按综合评分排序
        scored_docs.sort(key=lambda x: x[1], reverse=True)

        # 返回top-k结果
        final_docs = [doc for doc, score in scored_docs[:k]]

        self.logger.debug("结果合并完成", extra={
            "total_candidates": len(doc_scores),
            "final_count": len(final_docs),
            "top_score": scored_docs[0][1] if scored_docs else 0
        })

        return final_docs

    def _extract_filename(self, source: str) -> str:
        """提取文件名"""
        if not source:
            return ""

        # 提取文件名（去除路径）
        filename = source.split("/")[-1] if "/" in source else source

        # 去除文件扩展名
        if "." in filename:
            filename = filename.rsplit(".", 1)[0]

        return filename

    def _calculate_filename_similarity(self, query: str, filename: str) -> float:
        """计算文件名相似度

        Args:
            query: 查询文本（小写）
            filename: 文件名（小写）

        Returns:
            相似度分数 (0-1)
        """
        if not query or not filename:
            return 0.0

        # 预处理：分词
        query_words = set(self._tokenize(query))
        filename_words = set(self._tokenize(filename))

        if not query_words:
            return 0.0

        # 1. 精确匹配分数
        exact_matches = query_words.intersection(filename_words)
        exact_score = len(exact_matches) / len(query_words)

        # 2. 部分匹配分数
        partial_score = 0.0
        for query_word in query_words:
            for filename_word in filename_words:
                if query_word in filename_word or filename_word in query_word:
                    partial_score += 0.5
                    break
        partial_score = min(1.0, partial_score / len(query_words))

        # 3. 子串匹配分数
        substring_score = 0.0
        for word in query_words:
            if word in filename:
                substring_score += 1
        substring_score = substring_score / len(query_words)

        # 综合评分
        final_score = exact_score * 0.5 + partial_score * 0.3 + substring_score * 0.2

        return min(1.0, final_score)

    def _tokenize(self, text: str) -> List[str]:
        """文本分词

        Args:
            text: 输入文本

        Returns:
            词汇列表
        """
        # 使用正则表达式分词，支持中英文
        words = re.findall(r'\b\w+\b', text.lower())

        # 处理中文分词（简单按字符分割）
        chinese_chars = re.findall(r'[\u4e00-\u9fff]+', text)
        for chars in chinese_chars:
            words.extend(list(chars))

        # 过滤短词
        words = [word for word in words if len(word) > 1]

        return words

    def _get_doc_id(self, doc: Document) -> str:
        """获取文档唯一标识"""
        # 使用内容前100字符和来源作为ID
        content_preview = doc.page_content[:100]
        source = doc.metadata.get("source", "")
        return f"{source}:{hash(content_preview)}"

    def search_by_filename(self, filename_query: str, k: int = 4) -> List[Document]:
        """按文件名搜索

        Args:
            filename_query: 文件名查询
            k: 返回数量

        Returns:
            匹配的文档列表
        """
        if not app_state.vectorstore:
            return []

        try:
            # 获取所有文档进行文件名匹配
            all_docs = self._semantic_search("", k * 5)  # 获取更多候选
            filename_matches = self._filename_search(filename_query, all_docs)

            return filename_matches[:k]

        except Exception as e:
            self.logger.error("文件名搜索失败", exception=e)
            return []

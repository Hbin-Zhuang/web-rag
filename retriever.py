"""
检索增强生成 (RAG) 模块
负责文档检索和回答生成
"""

import time
from typing import List, Dict, Any, Optional
from langchain.schema import Document
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate

# 使用新的基础设施服务
from src.infrastructure.config.config_migration_adapter import get_legacy_config
from src.infrastructure import get_logger

class DocumentRetriever:
    """文档检索器"""

    def __init__(self, vectorstore=None, config_service=None, logger_service=None):
        """初始化文档检索器

        Args:
            vectorstore: 向量存储实例
            config_service: 配置服务实例
            logger_service: 日志服务实例
        """
        # 获取服务实例 (支持依赖注入)
        self.config = config_service or get_legacy_config()
        self.logger = logger_service or get_logger()

        self.vectorstore = vectorstore
        self.qa_chain = None
        self._create_qa_chain()

    def _create_qa_chain(self):
        """创建问答链"""
        try:
            if not self.vectorstore:
                self.logger.warning("向量存储未提供，QA链创建延迟")
                return

            if not self.config.validate_config():
                self.logger.error("配置验证失败，请检查GOOGLE_API_KEY")
                return

            # 创建语言模型
            llm = ChatGoogleGenerativeAI(
                model=self.config.CHAT_MODEL,
                temperature=0.3,
                max_tokens=self.config.MAX_TOKENS,
                google_api_key=self.config.GOOGLE_API_KEY
            )

            # 创建检索器
            retriever = self.vectorstore.as_retriever(
                search_kwargs={"k": self.config.SIMILARITY_TOP_K}
            )

            # 创建提示模板
            template = """
请基于以下上下文信息来回答问题。如果无法从上下文中找到答案，请如实说明。

上下文信息:
{context}

问题: {question}

请提供准确、有用的回答:
"""

            prompt = PromptTemplate(
                template=template,
                input_variables=["context", "question"]
            )

            # 创建QA链
            self.qa_chain = RetrievalQA.from_chain_type(
                llm=llm,
                chain_type="stuff",
                retriever=retriever,
                chain_type_kwargs={"prompt": prompt},
                return_source_documents=True
            )

            self.logger.info("QA链创建成功", extra={
                "chat_model": self.config.CHAT_MODEL,
                "max_tokens": self.config.MAX_TOKENS,
                "similarity_top_k": self.config.SIMILARITY_TOP_K
            })

        except Exception as e:
            self.logger.error("QA链创建失败", exception=e)
            self.qa_chain = None

    def query(self, question: str, include_sources: bool = True) -> Dict[str, Any]:
        """
        查询文档并生成回答

        Args:
            question: 用户问题
            include_sources: 是否包含源文档信息

        Returns:
            包含回答和源文档的字典
        """
        start_time = time.time()

        try:
            if not question.strip():
                self.logger.warning("查询问题为空")
                return {
                    "answer": "请提供一个有效的问题。",
                    "sources": [],
                    "query_time": 0.0
                }

            if not self.qa_chain:
                self.logger.error("QA链未初始化")
                return {
                    "answer": "系统未就绪，请稍后再试或检查配置。",
                    "sources": [],
                    "query_time": 0.0
                }

            # 执行查询
            self.logger.info("开始执行文档查询", extra={
                "question_preview": question[:100]
            })

            result = self.qa_chain({"query": question})

            query_time = time.time() - start_time

            # 处理结果
            answer = result.get("result", "抱歉，无法生成回答。")
            source_docs = result.get("source_documents", [])

            # 格式化源文档信息
            sources = []
            if include_sources and source_docs:
                sources = self._format_source_documents(source_docs)

            self.logger.info("文档查询完成", extra={
                "question_preview": question[:50],
                "answer_preview": answer[:100],
                "sources_count": len(sources),
                "query_time": f"{query_time:.2f}s"
            })

            return {
                "answer": answer,
                "sources": sources,
                "query_time": round(query_time, 2)
            }

        except Exception as e:
            query_time = time.time() - start_time
            self.logger.error("文档查询失败", exception=e, extra={
                "question": question[:100],
                "query_time": f"{query_time:.2f}s"
            })

            return {
                "answer": f"查询过程中出现错误: {str(e)}",
                "sources": [],
                "query_time": round(query_time, 2)
            }

    def _format_source_documents(self, documents: List[Document]) -> List[Dict[str, Any]]:
        """格式化源文档信息"""
        sources = []
        for i, doc in enumerate(documents, 1):
            metadata = doc.metadata

            source_info = {
                "index": i,
                "content": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content,
                "source_file": metadata.get("source_file", "未知来源"),
                "page": metadata.get("page", "未知页码"),
                "chunk_id": metadata.get("chunk_id", f"chunk_{i}")
            }

            sources.append(source_info)

        return sources

    def search_similar_content(self, query: str, k: int = None) -> List[Dict[str, Any]]:
        """
        搜索相似内容（不生成回答）

        Args:
            query: 搜索查询
            k: 返回结果数量

        Returns:
            相似文档列表
        """
        try:
            if not self.vectorstore:
                self.logger.error("向量存储不可用")
                return []

            if not query.strip():
                self.logger.warning("搜索查询为空")
                return []

            k = k or self.config.SIMILARITY_TOP_K

            similar_docs = self.vectorstore.similarity_search(query, k=k)

            results = []
            for i, doc in enumerate(similar_docs, 1):
                result = {
                    "rank": i,
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "relevance_score": "N/A"  # Chroma doesn't return scores by default
                }
                results.append(result)

            self.logger.info("相似内容搜索完成", extra={
                "query_preview": query[:50],
                "results_count": len(results),
                "k": k
            })

            return results

        except Exception as e:
            self.logger.error("相似内容搜索失败", exception=e, extra={
                "query": query[:100]
            })
            return []

    def update_vectorstore(self, vectorstore):
        """更新向量存储"""
        try:
            self.vectorstore = vectorstore
            self._create_qa_chain()  # 重新创建QA链

            self.logger.info("向量存储已更新，QA链重新初始化")

        except Exception as e:
            self.logger.error("更新向量存储失败", exception=e)

    def get_retriever_info(self) -> Dict[str, Any]:
        """获取检索器信息"""
        try:
            return {
                "qa_chain_ready": self.qa_chain is not None,
                "vectorstore_ready": self.vectorstore is not None,
                "chat_model": self.config.CHAT_MODEL,
                "max_tokens": self.config.MAX_TOKENS,
                "similarity_top_k": self.config.SIMILARITY_TOP_K,
                "config_valid": self.config.validate_config()
            }
        except Exception as e:
            self.logger.error("获取检索器信息失败", exception=e)
            return {"status": "error", "error": str(e)}

    def clear_cache(self):
        """清理缓存（如果有的话）"""
        try:
            # 这里可以实现缓存清理逻辑
            self.logger.info("检索器缓存已清理")
        except Exception as e:
            self.logger.error("清理检索器缓存失败", exception=e)
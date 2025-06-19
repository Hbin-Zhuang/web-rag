"""
文档向量化和索引管理模块
负责文档的向量化、存储和检索
"""

import os
from typing import List, Optional, Dict, Any
from langchain.schema import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Chroma

# 使用新的基础设施服务
from src.infrastructure.config.config_migration_adapter import get_legacy_config
from src.infrastructure.utilities import get_utility_service, ProgressTracker
from src.infrastructure import get_logger

class DocumentIndexer:
    """文档索引器"""

    def __init__(self, config_service=None, logger_service=None, utility_service=None):
        """初始化文档索引器

        Args:
            config_service: 配置服务实例
            logger_service: 日志服务实例
            utility_service: 工具服务实例
        """
        # 获取服务实例 (支持依赖注入)
        self.config = config_service or get_legacy_config()
        self.logger = logger_service or get_logger()
        self.utility = utility_service or get_utility_service()

        self.embeddings = None
        self.vectorstore = None
        self._initialize_embeddings()

    def _initialize_embeddings(self):
        """初始化嵌入模型"""
        try:
            if not self.config.validate_config():
                self.logger.error("配置验证失败，请检查GOOGLE_API_KEY")
                return

            self.embeddings = GoogleGenerativeAIEmbeddings(
                model=self.config.EMBEDDING_MODEL,
                google_api_key=self.config.GOOGLE_API_KEY
            )
            self.logger.info("嵌入模型初始化成功", extra={
                "embedding_model": self.config.EMBEDDING_MODEL
            })

        except Exception as e:
            self.logger.error("嵌入模型初始化失败", exception=e)
            self.embeddings = None

    def _get_or_create_vectorstore(self) -> Optional[Chroma]:
        """获取或创建向量数据库"""
        try:
            if not self.embeddings:
                self.logger.error("嵌入模型未初始化")
                return None

            # 确保数据库目录存在
            os.makedirs(self.config.CHROMA_DB_PATH, exist_ok=True)

            # 创建或连接到现有的Chroma数据库
            self.vectorstore = Chroma(
                persist_directory=self.config.CHROMA_DB_PATH,
                embedding_function=self.embeddings,
                collection_name="documents"
            )

            self.logger.info("向量数据库连接成功", extra={
                "database_path": self.config.CHROMA_DB_PATH
            })
            return self.vectorstore

        except Exception as e:
            self.logger.error("向量数据库连接失败", exception=e, extra={
                "database_path": self.config.CHROMA_DB_PATH
            })
            return None

    def create_embeddings(self, documents: List[Document]) -> Optional[Chroma]:
        """
        为文档创建向量嵌入并存储

        Args:
            documents: 要处理的文档列表

        Returns:
            Chroma向量存储实例或None（如果失败）
        """
        try:
            if not documents:
                self.logger.warning("没有文档需要向量化")
                return None

            if not self.embeddings:
                self.logger.error("嵌入模型未初始化")
                return None

            # 获取向量数据库
            vectorstore = self._get_or_create_vectorstore()
            if not vectorstore:
                return None

            # 分批处理文档以避免内存问题
            batch_size = 10  # 可以根据需要调整
            document_batches = self.utility.split_into_batches(documents, batch_size)

            # 创建进度跟踪器
            progress = ProgressTracker(
                total=len(documents),
                description="向量化文档",
                logger=self.logger
            )

            total_added = 0
            for batch in document_batches:
                try:
                    # 添加文档到向量数据库
                    vectorstore.add_documents(batch)
                    total_added += len(batch)
                    progress.update(len(batch))

                    progress_info = progress.get_progress()
                    self.logger.info(f"向量化进度更新", extra={
                        "percentage": progress_info['percentage'],
                        "current": progress_info['current'],
                        "total": progress_info['total']
                    })

                except Exception as e:
                    self.logger.error("批次处理失败", exception=e, extra={
                        "batch_size": len(batch)
                    })
                    continue

            # 持久化数据库
            vectorstore.persist()

            self.logger.info("向量化完成", extra={
                "processed_documents": total_added,
                "total_documents": len(documents),
                "success_rate": f"{(total_added/len(documents)*100):.1f}%" if documents else "0%"
            })
            return vectorstore

        except Exception as e:
            self.logger.error("创建文档嵌入失败", exception=e)
            return None

    def add_documents(self, documents: List[Document]) -> bool:
        """
        向现有向量数据库添加新文档

        Args:
            documents: 要添加的文档列表

        Returns:
            是否成功添加
        """
        try:
            if not documents:
                self.logger.warning("没有文档需要添加")
                return False

            # 获取现有向量数据库或创建新的
            if not self.vectorstore:
                self.vectorstore = self._get_or_create_vectorstore()

            if not self.vectorstore:
                self.logger.error("无法获取向量数据库")
                return False

            # 检查文档是否已存在（基于chunk_id）
            new_documents = []
            for doc in documents:
                chunk_id = doc.metadata.get("chunk_id")
                if chunk_id and not self._document_exists(chunk_id):
                    new_documents.append(doc)

            if not new_documents:
                self.logger.info("所有文档都已存在，跳过添加")
                return True

            # 添加新文档
            self.vectorstore.add_documents(new_documents)
            self.vectorstore.persist()

            self.logger.info("成功添加新文档", extra={
                "new_documents": len(new_documents),
                "total_provided": len(documents)
            })
            return True

        except Exception as e:
            self.logger.error("添加文档失败", exception=e)
            return False

    def _document_exists(self, chunk_id: str) -> bool:
        """检查文档是否已存在"""
        try:
            # 这里可以实现更复杂的重复检查逻辑
            # 目前简单返回False，让调用者处理重复问题
            return False
        except Exception:
            return False

    def get_vectorstore(self) -> Optional[Chroma]:
        """
        获取向量数据库实例

        Returns:
            Chroma向量存储实例或None
        """
        if not self.vectorstore:
            self.vectorstore = self._get_or_create_vectorstore()
        return self.vectorstore

    def search_similar_documents(
        self,
        query: str,
        k: int = None
    ) -> List[Document]:
        """
        搜索相似文档

        Args:
            query: 查询文本
            k: 返回结果数量

        Returns:
            相似文档列表
        """
        try:
            if not query.strip():
                self.logger.warning("查询文本为空")
                return []

            vectorstore = self.get_vectorstore()
            if not vectorstore:
                self.logger.error("向量数据库不可用")
                return []

            k = k or self.config.SIMILARITY_TOP_K
            results = vectorstore.similarity_search(query, k=k)

            self.logger.info("相似性搜索完成", extra={
                "query_preview": self.utility.truncate_text(query, 50),
                "results_count": len(results),
                "k": k
            })
            return results

        except Exception as e:
            self.logger.error("相似性搜索失败", exception=e, extra={"query": query[:100]})
            return []

    def get_database_info(self) -> Dict[str, Any]:
        """获取数据库信息"""
        try:
            vectorstore = self.get_vectorstore()
            if not vectorstore:
                return {"status": "unavailable"}

            # 获取集合信息
            collection = vectorstore._collection
            count = collection.count()

            return {
                "status": "active",
                "document_count": count,
                "database_path": self.config.CHROMA_DB_PATH,
                "embedding_model": self.config.EMBEDDING_MODEL,
                "collection_name": "documents"
            }

        except Exception as e:
            self.logger.error("获取数据库信息失败", exception=e)
            return {"status": "error", "error": str(e)}

    def clear_database(self) -> bool:
        """清空数据库"""
        try:
            vectorstore = self.get_vectorstore()
            if not vectorstore:
                return False

            # 删除所有文档
            vectorstore.delete_collection()
            self.vectorstore = None

            self.logger.info("数据库已清空")
            return True

        except Exception as e:
            self.logger.error("清空数据库失败", exception=e)
            return False
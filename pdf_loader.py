"""
PDF文档加载和分块处理模块
负责PDF文件的读取、解析和文本分割
"""

import os
from typing import List, Optional
from langchain.schema import Document
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from config import Config
from utils import logger, validate_file_type, validate_file_size, calculate_file_hash

class PDFLoader:
    """PDF文档加载器"""

    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=Config.CHUNK_SIZE,
            chunk_overlap=Config.CHUNK_OVERLAP,
            separators=["\n\n", "\n", " ", ""]
        )

    def validate_pdf(self, file_path: str) -> bool:
        """验证PDF文件"""
        # 检查文件是否存在
        if not os.path.exists(file_path):
            logger.error(f"文件不存在: {file_path}")
            return False

        # 检查文件类型
        if not validate_file_type(file_path, Config.ALLOWED_FILE_TYPES):
            logger.error(f"不支持的文件类型: {file_path}")
            return False

        # 检查文件大小
        if not validate_file_size(file_path, Config.MAX_FILE_SIZE_MB):
            logger.error(f"文件大小超过限制: {file_path}")
            return False

        return True

    def load_pdf(self, file_path: str) -> Optional[List[Document]]:
        """
        加载PDF文档

        Args:
            file_path: PDF文件路径

        Returns:
            Document列表或None（如果失败）
        """
        try:
            # 验证PDF文件
            if not self.validate_pdf(file_path):
                return None

            # 使用PyPDFLoader加载PDF
            loader = PyPDFLoader(file_path)
            documents = loader.load()

            if not documents:
                logger.warning(f"PDF文件为空或无法读取: {file_path}")
                return None

            # 添加元数据
            file_hash = calculate_file_hash(file_path)
            for doc in documents:
                doc.metadata.update({
                    "source_file": os.path.basename(file_path),
                    "file_path": file_path,
                    "file_hash": file_hash,
                    "loader_type": "PyPDFLoader"
                })

            logger.info(f"成功加载PDF文档: {file_path}, 页数: {len(documents)}")
            return documents

        except Exception as e:
            logger.error(f"加载PDF文档失败: {file_path}, 错误: {e}")
            return None

    def split_documents(self, documents: List[Document]) -> List[Document]:
        """
        分割文档为更小的块

        Args:
            documents: 原始文档列表

        Returns:
            分割后的文档块列表
        """
        try:
            if not documents:
                logger.warning("没有文档需要分割")
                return []

            # 使用文本分割器处理文档
            split_docs = self.text_splitter.split_documents(documents)

            # 为每个分块添加额外元数据
            for i, doc in enumerate(split_docs):
                doc.metadata.update({
                    "chunk_index": i,
                    "chunk_size": len(doc.page_content),
                    "chunk_id": f"{doc.metadata.get('file_hash', 'unknown')}_{i}"
                })

            logger.info(f"文档分割完成: {len(documents)} 页 -> {len(split_docs)} 块")
            return split_docs

        except Exception as e:
            logger.error(f"文档分割失败: {e}")
            return []

    def process_pdf(self, file_path: str) -> Optional[List[Document]]:
        """
        完整的PDF处理流程：加载 -> 分割

        Args:
            file_path: PDF文件路径

        Returns:
            处理后的文档块列表或None（如果失败）
        """
        try:
            # 步骤1: 加载PDF文档
            documents = self.load_pdf(file_path)
            if not documents:
                return None

            # 步骤2: 分割文档
            split_documents = self.split_documents(documents)
            if not split_documents:
                return None

            logger.info(f"PDF处理完成: {file_path}")
            return split_documents

        except Exception as e:
            logger.error(f"PDF处理流程失败: {file_path}, 错误: {e}")
            return None

    def get_document_info(self, documents: List[Document]) -> dict:
        """获取文档信息统计"""
        if not documents:
            return {}

        total_chars = sum(len(doc.page_content) for doc in documents)
        source_files = set(doc.metadata.get("source_file", "unknown") for doc in documents)

        return {
            "total_chunks": len(documents),
            "total_characters": total_chars,
            "source_files": list(source_files),
            "avg_chunk_size": total_chars // len(documents) if documents else 0,
            "chunk_size_config": Config.CHUNK_SIZE,
            "chunk_overlap_config": Config.CHUNK_OVERLAP
        }
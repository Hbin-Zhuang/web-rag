"""
文档处理服务
封装PDF文档的上传、处理、向量化等核心业务逻辑
"""

import os
import tempfile
from pathlib import Path
from typing import Optional, Tuple, List
from datetime import datetime

from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings

# 使用新的基础设施服务
from src.infrastructure.config.config_migration_adapter import get_legacy_config
from src.infrastructure.utilities import get_utility_service
from src.infrastructure import get_logger
from src.shared.state.application_state import app_state, FileInfo


class DocumentService:
    """文档处理服务"""

    def __init__(self, model_service=None, config_service=None, logger_service=None, utility_service=None):
        """初始化文档服务

        Args:
            model_service: 模型管理服务实例，用于依赖注入
            config_service: 配置服务实例
            logger_service: 日志服务实例
            utility_service: 工具服务实例
        """
        self.model_service = model_service

        # 获取服务实例 (支持依赖注入)
        if config_service:
            # 如果提供了ConfigurationService，使用ConfigMigrationAdapter适配
            from src.infrastructure.config.config_migration_adapter import ConfigMigrationAdapter
            self.config = ConfigMigrationAdapter(config_service)
        else:
            self.config = get_legacy_config()
        self.logger = logger_service or get_logger()
        self.utility = utility_service or get_utility_service()

        # 使用配置服务初始化文本分割器
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.config.CHUNK_SIZE,
            chunk_overlap=self.config.CHUNK_OVERLAP,
            length_function=len,
        )

        self.logger.info("DocumentService 初始化完成", extra={
            "chunk_size": self.config.CHUNK_SIZE,
            "chunk_overlap": self.config.CHUNK_OVERLAP
        })

    def process_pdf(self, file) -> str:
        """
        处理PDF文件并创建向量数据库

        Args:
            file: 上传的文件对象

        Returns:
            处理结果消息
        """
        self.logger.info("开始处理PDF文件", extra={"file": str(file)})

        if file is None:
            self.logger.warning("未提供文件")
            return "❌ 请选择一个 PDF 文件"

        try:
            # 获取文件路径和名称
            file_path, file_name = self._get_file_info(file)

            self.logger.info("获取文件信息", extra={
                "file_path": file_path,
                "file_name": file_name
            })

            # 验证文件
            if not self._validate_file(file_path):
                return f"❌ 文件验证失败: {file_path}"

            self.logger.info("文件验证通过，开始处理文档")

            # 加载并处理PDF
            documents = self._load_pdf(file_path)
            if not documents:
                return "❌ PDF 文件为空或无法读取"

            self.logger.info("成功加载文档", extra={"pages": len(documents)})

            # 分割文档
            texts = self._split_documents(documents)
            self.logger.info("文档分割完成", extra={"chunks": len(texts)})

            # 创建向量存储
            success = self._create_vector_store(texts)
            if not success:
                return "❌ 向量数据库创建失败"

            # 更新文件记录
            self._update_file_record(file_name, len(documents), len(texts))

            self.logger.info("文档处理完成", extra={
                "file_name": file_name,
                "pages": len(documents),
                "chunks": len(texts)
            })
            return f"✅ 文档 '{file_name}' 处理完成！\\n📄 页数: {len(documents)}\\n📝 文档片段: {len(texts)}"

        except Exception as e:
            error_msg = f"❌ 处理文档时发生错误: {str(e)}"
            self.logger.error("文档处理失败", exception=e, extra={"file": str(file)})
            return error_msg

    def process_pdf_and_update_status(self, file, selected_model: str) -> Tuple[str, str, str, str]:
        """
        处理PDF并更新系统状态

        Args:
            file: 上传的文件对象
            selected_model: 选择的模型

        Returns:
            (upload_status, model_status, system_status, file_list)
        """
        try:
            # 更新当前模型
            app_state.current_model = selected_model

            # 处理PDF
            upload_status = self.process_pdf(file)

            # 获取更新后的状态
            model_status = f"当前模型: {app_state.current_model} (就绪)"
            system_status = self._get_system_status()
            file_list = self._get_uploaded_files_display()

            return upload_status, model_status, system_status, file_list

        except Exception as e:
            error_msg = f"❌ 处理失败: {str(e)}"
            return error_msg, "模型状态获取失败", "系统状态获取失败", "文件列表获取失败"

    def _get_file_info(self, file) -> Tuple[str, str]:
        """获取文件路径和名称"""
        if hasattr(file, 'name'):
            file_path = file.name
            file_name = Path(file_path).name
        else:
            file_path = str(file)
            file_name = Path(file_path).name
        return file_path, file_name

    def _validate_file(self, file_path: str) -> bool:
        """验证文件是否有效"""
        # 检查文件是否存在
        if not os.path.exists(file_path):
            self.logger.error(f"文件不存在: {file_path}")
            return False

        # 验证文件类型
        if not self.utility.validate_file_type(file_path, self.config.ALLOWED_FILE_TYPES):
            self.logger.error(f"不支持的文件类型: {file_path}")
            return False

        # 验证文件大小
        if not self.utility.validate_file_size(file_path, self.config.MAX_FILE_SIZE_MB):
            self.logger.error(f"文件大小超过限制: {file_path}")
            return False

        # 计算文件哈希（用于去重检测）
        file_hash = self.utility.calculate_file_hash(file_path)
        if file_hash:
            self.logger.debug(f"文件哈希计算完成: {file_path} -> {file_hash[:8]}...")

        return True

    def _load_pdf(self, file_path: str):
        """加载PDF文档"""
        self.logger.info("正在加载 PDF...")
        loader = PyPDFLoader(file_path)
        documents = loader.load()
        return documents

    def _split_documents(self, documents):
        """分割文档"""
        self.logger.info("正在分割文档...")
        texts = self.text_splitter.split_documents(documents)
        return texts

    def _create_vector_store(self, texts) -> bool:
        """创建或更新向量存储"""
        try:
            self.logger.info("正在创建嵌入...")

            # 创建嵌入模型
            embeddings = self._create_embeddings()
            if not embeddings:
                return False

            self.logger.info("正在处理向量数据库...")

            # 检查是否已有向量数据库
            if app_state.vectorstore is not None:
                self.logger.info("检测到已有向量数据库，将添加新文档...")
                try:
                    app_state.vectorstore.add_documents(texts)
                    self.logger.info("✅ 新文档已添加到现有向量数据库")
                except Exception as e:
                    self.logger.error("添加文档到向量数据库失败", exception=e, extra={"file": str(file)})
                    # 重新创建向量数据库
                    self.logger.info("正在重新创建向量数据库...")
                    app_state.vectorstore = Chroma.from_documents(
                        documents=texts,
                        embedding=embeddings
                    )
                    self.logger.info("✅ 向量数据库重新创建成功")
            else:
                self.logger.info("创建新的向量数据库...")
                app_state.vectorstore = Chroma.from_documents(
                    documents=texts,
                    embedding=embeddings
                )
                self.logger.info("✅ 向量数据库创建成功")

            return True

        except Exception as e:
            self.logger.error("向量存储创建失败", exception=e)
            return False

    def _create_embeddings(self):
        """创建嵌入模型"""
        try:
            embeddings = GoogleGenerativeAIEmbeddings(
                model="models/embedding-001",
                request_timeout=120
            )
            self.logger.info("✅ Embedding 模型初始化成功")
            return embeddings
        except Exception as e:
            self.logger.error("Embedding 模型初始化失败，尝试备用方案", exception=e)
            try:
                embeddings = GoogleGenerativeAIEmbeddings(
                    model="models/text-embedding-004",
                    request_timeout=120
                )
                self.logger.info("✅ 使用备用 embedding 模型成功")
                return embeddings
            except Exception as e2:
                self.logger.error("无法初始化 embedding 模型", exception=e2)
                return None

    def _update_file_record(self, file_name: str, pages: int, chunks: int):
        """更新文件记录"""
        file_info = FileInfo(
            name=file_name,
            upload_time=datetime.now(),
            pages=pages,
            chunks=chunks,
            model=app_state.current_model
        )
        app_state.add_uploaded_file(file_info)

    def _get_system_status(self) -> str:
        """获取系统状态"""
        try:
            state_info = app_state.get_state_info()

            status_parts = [
                f"🤖 当前模型: {state_info['current_model']}",
                f"📊 状态: {'就绪' if state_info['qa_chain_initialized'] else '未加载'}",
                f"📚 已上传文档: {state_info['uploaded_files_count']} 个",
                f"🔧 向量数据库: {'已初始化' if state_info['vectorstore_initialized'] else '未初始化'}",
                f"🕐 最后更新: {datetime.fromisoformat(state_info['last_update']).strftime('%H:%M:%S')}"
            ]

            return "\\n".join(status_parts)

        except Exception as e:
            return f"❌ 获取系统状态失败: {str(e)}"

    def _get_uploaded_files_display(self) -> str:
        """获取上传文件列表显示"""
        try:
            files = app_state.get_uploaded_files()

            if not files:
                return "暂无已上传的文件"

            file_list = ["## 📁 已上传的文件\\n"]

            for i, file_info in enumerate(files, 1):
                upload_time = file_info.upload_time.strftime("%Y-%m-%d %H:%M:%S")
                file_list.append(
                    f"**{i}. {file_info.name}**\\n"
                    f"   - 📅 上传时间: {upload_time}\\n"
                    f"   - 📄 页数: {file_info.pages}\\n"
                    f"   - 📝 文档片段: {file_info.chunks}\\n"
                    f"   - 🤖 处理模型: {file_info.model}\\n"
                )

            return "\\n".join(file_list)

        except Exception as e:
            return f"❌ 获取文件列表失败: {str(e)}"

    def get_uploaded_files_count(self) -> int:
        """获取已上传文件数量"""
        return len(app_state.get_uploaded_files())

    def clear_uploaded_files(self):
        """清空上传文件记录"""
        app_state.clear_uploaded_files()
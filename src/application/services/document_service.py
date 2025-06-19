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

from config import Config
from utils import logger
from src.shared.state.application_state import app_state, FileInfo


class DocumentService:
    """文档处理服务"""

    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )

    def process_pdf(self, file) -> str:
        """
        处理PDF文件并创建向量数据库

        Args:
            file: 上传的文件对象

        Returns:
            处理结果消息
        """
        print(f"DocumentService: 开始处理文件: {file}")

        if file is None:
            return "❌ 请选择一个 PDF 文件"

        try:
            # 获取文件路径和名称
            file_path, file_name = self._get_file_info(file)

            print(f"文件路径: {file_path}")
            print(f"文件名: {file_name}")

            # 检查文件是否存在
            if not os.path.exists(file_path):
                return f"❌ 文件不存在: {file_path}"

            print("✅ 系统准备完成，将添加新文档到现有知识库")

            # 加载并处理PDF
            documents = self._load_pdf(file_path)
            if not documents:
                return "❌ PDF 文件为空或无法读取"

            print(f"成功加载 {len(documents)} 页文档")

            # 分割文档
            texts = self._split_documents(documents)
            print(f"文档分割为 {len(texts)} 个片段")

            # 创建向量存储
            success = self._create_vector_store(texts)
            if not success:
                return "❌ 向量数据库创建失败"

            # 更新文件记录
            self._update_file_record(file_name, len(documents), len(texts))

            print("✅ 文档处理完成")
            return f"✅ 文档 '{file_name}' 处理完成！\\n📄 页数: {len(documents)}\\n📝 文档片段: {len(texts)}"

        except Exception as e:
            error_msg = f"❌ 处理文档时发生错误: {str(e)}"
            print(error_msg)
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

    def _load_pdf(self, file_path: str):
        """加载PDF文档"""
        print("正在加载 PDF...")
        loader = PyPDFLoader(file_path)
        documents = loader.load()
        return documents

    def _split_documents(self, documents):
        """分割文档"""
        print("正在分割文档...")
        texts = self.text_splitter.split_documents(documents)
        return texts

    def _create_vector_store(self, texts) -> bool:
        """创建或更新向量存储"""
        try:
            print("正在创建嵌入...")

            # 创建嵌入模型
            embeddings = self._create_embeddings()
            if not embeddings:
                return False

            print("正在处理向量数据库...")

            # 检查是否已有向量数据库
            if app_state.vectorstore is not None:
                print("检测到已有向量数据库，将添加新文档...")
                try:
                    app_state.vectorstore.add_documents(texts)
                    print("✅ 新文档已添加到现有向量数据库")
                except Exception as e:
                    print(f"❌ 添加文档到向量数据库失败: {e}")
                    # 重新创建向量数据库
                    print("正在重新创建向量数据库...")
                    app_state.vectorstore = Chroma.from_documents(
                        documents=texts,
                        embedding=embeddings
                    )
                    print("✅ 向量数据库重新创建成功")
            else:
                print("创建新的向量数据库...")
                app_state.vectorstore = Chroma.from_documents(
                    documents=texts,
                    embedding=embeddings
                )
                print("✅ 向量数据库创建成功")

            return True

        except Exception as e:
            print(f"❌ 向量存储创建失败: {e}")
            return False

    def _create_embeddings(self):
        """创建嵌入模型"""
        try:
            embeddings = GoogleGenerativeAIEmbeddings(
                model="models/embedding-001",
                request_timeout=120
            )
            print("✅ Embedding 模型初始化成功")
            return embeddings
        except Exception as e:
            print(f"❌ Embedding 模型初始化失败，尝试备用方案: {e}")
            try:
                embeddings = GoogleGenerativeAIEmbeddings(
                    model="models/text-embedding-004",
                    request_timeout=120
                )
                print("✅ 使用备用 embedding 模型成功")
                return embeddings
            except Exception as e2:
                print(f"❌ 无法初始化 embedding 模型: {str(e2)}")
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
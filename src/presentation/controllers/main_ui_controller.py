"""
主UI控制器
集成所有Tab控制器和事件管理，构建完整的Gradio界面
"""

from typing import Any, Dict
import gradio as gr
import os
import sys
import traceback

from src.presentation.controllers.ui_controller import UIController


class MainUIController(UIController):
    """主UI控制器

    负责协调所有Tab控制器，管理整体UI架构和事件系统
    """

    def __init__(self, document_service, chat_service, model_service, config_service, logger):
        """初始化主UI控制器

        Args:
            document_service: 文档处理服务
            chat_service: 聊天服务
            model_service: 模型管理服务
            config_service: 配置服务
            logger: 日志服务
        """
        super().__init__("main_ui")

        # 服务依赖
        self.document_service = document_service
        self.chat_service = chat_service
        self.model_service = model_service
        self.config_service = config_service
        self.logger = logger

        # Gradio界面实例
        self.demo = None

    def create_components(self) -> Dict[str, Any]:
        """创建主界面组件"""
        return {}

    def setup_events(self) -> Dict[str, Any]:
        """设置事件绑定"""
        return []

    def build_interface(self) -> gr.Blocks:
        """构建完整的Gradio界面

        Returns:
            配置完成的Gradio Blocks实例
        """
        try:
            # 创建主界面
            with gr.Blocks(
                title="Web RAG 系统 v4.0 (企业级版)",
                theme=gr.themes.Soft()
            ) as self.demo:

                # 标题和说明
                gr.Markdown("# 🚀 Web RAG 系统 v4.0 (企业级版)")
                gr.Markdown("基于 Google Gemini 的智能文档问答系统 - 企业级性能优化与扩展性增强")

                with gr.Tabs():
                    # 上传Tab
                    with gr.TabItem("📄 文档上传", id="upload"):
                        self._build_upload_tab()

                    # 聊天Tab
                    with gr.TabItem("💬 智能对话", id="chat"):
                        self._build_chat_tab()

                    # 状态Tab
                    with gr.TabItem("📊 系统状态", id="status"):
                        self._build_status_tab()

                # 在Gradio上下文中绑定事件
                self._bind_upload_events()
                self._bind_chat_events()
                self._bind_status_events()
                self._bind_load_events()

            return self.demo

        except Exception as e:
            print(f"❌ 构建界面失败: {e}")
            print(f"错误详情: {traceback.format_exc()}")
            return self._create_error_interface(e)

    def _build_upload_tab(self):
        """构建上传Tab"""
        gr.Markdown("## 上传 PDF 文档")
        gr.Markdown("注意: 上传后请等待处理完成，状态会显示在下方")

        with gr.Row():
            with gr.Column(scale=2):
                self.upload_file = gr.File(
                    label="📄 选择 PDF 文件",
                    file_types=[".pdf"],
                    type="filepath"
                )
            with gr.Column(scale=1):
                with gr.Group():
                    gr.Markdown("### 🤖 模型配置")

                    # 获取可用模型和当前模型
                    available_models = self.config_service.get_value("fallback_models")
                    current_model = self.config_service.get_value("chat_model")

                    self.model_dropdown = gr.Dropdown(
                        label="选择 Gemini 模型",
                        choices=available_models,
                        value=current_model,
                        interactive=True
                    )

        gr.Markdown("### 处理状态")
        self.upload_status = gr.Textbox(
            label="状态",
            value="等待文件上传...",
            interactive=False
        )

        self.uploaded_files_display = gr.Markdown("### 暂无已上传文件")

    def _build_chat_tab(self):
        """构建聊天Tab"""
        gr.Markdown("## 与文档内容对话")
        gr.Markdown("提示: 请先上传并处理 PDF 文件，然后在此提问")

        self.chatbot = gr.Chatbot(
            label="对话历史",
            height=400
        )

        with gr.Row():
            self.msg = gr.Textbox(
                label="输入您的问题",
                placeholder="请输入您想要询问的问题...",
                lines=3,
                scale=4
            )
            with gr.Column(scale=1):
                self.send_btn = gr.Button("发送", variant="primary")
                self.clear_btn = gr.Button("清除对话")

    def _build_status_tab(self):
        """构建状态Tab"""
        gr.Markdown("## 🔧 系统状态")

        with gr.Row():
            with gr.Column(scale=1):
                self.refresh_btn = gr.Button("🔄 刷新状态", variant="primary")
            with gr.Column(scale=2):
                pass  # 空列占位

        with gr.Row():
            with gr.Column(scale=2):
                self.system_status = gr.Markdown("🔄 正在获取系统状态...")
            with gr.Column(scale=1):
                self.model_info = gr.Markdown("🔄 正在获取模型信息...")

        gr.Markdown("## 🔧 技术栈")
        gr.Markdown("""
**LLM**: Google Gemini (自动选择可用模型)

**嵌入模型**: Google Embedding-001

**向量数据库**: ChromaDB

**框架**: LangChain + Gradio
""")

    def _bind_upload_events(self):
        """绑定上传Tab事件"""
        self.upload_file.upload(
            fn=self._process_document_with_model,
            inputs=[self.upload_file, self.model_dropdown],
            outputs=[self.upload_status, self.uploaded_files_display]
        )

    def _bind_chat_events(self):
        """绑定聊天Tab事件"""
        self.send_btn.click(
            fn=self._chat_with_documents,
            inputs=[self.msg, self.chatbot],
            outputs=[self.chatbot, self.msg]
        )

        self.msg.submit(
            fn=self._chat_with_documents,
            inputs=[self.msg, self.chatbot],
            outputs=[self.chatbot, self.msg]
        )

        self.clear_btn.click(
            fn=self._clear_chat,
            outputs=[self.chatbot]
        )

    def _bind_status_events(self):
        """绑定状态Tab事件"""
        self.refresh_btn.click(
            fn=lambda: (self._get_system_status(), self._get_model_info()),
            outputs=[self.system_status, self.model_info]
        )

    def _bind_load_events(self):
        """绑定页面加载事件"""
        # 页面加载时初始化状态
        self.demo.load(
            fn=lambda: (self._get_system_status(), self._get_model_info()),
            outputs=[self.system_status, self.model_info]
        )

        # 页面加载时初始化文件列表
        self.demo.load(
            fn=self._get_uploaded_files_display,
            outputs=[self.uploaded_files_display]
        )

        # 页面加载时确保模型下拉框有正确的默认值
        self.demo.load(
            fn=self._init_model_dropdown,
            outputs=[self.model_dropdown]
        )

    # 事件处理函数
    def _process_document_with_model(self, file_path, selected_model):
        """处理文档上传并指定模型"""
        try:
            if not file_path:
                return "❌ 请先选择文件", "### 暂无已上传文件"

            if not selected_model:
                return "❌ 请先选择模型", "### 暂无已上传文件"

            self.logger.info(f"开始处理文档: {file_path}, 模型: {selected_model}")

            # 更新当前模型
            if hasattr(self.model_service, 'switch_model'):
                self.model_service.switch_model(selected_model)

            # 处理PDF
            result_message = self.document_service.process_pdf(file_path)

            # 获取更新后的文件列表
            updated_files_display = self._get_uploaded_files_display()

            return result_message, updated_files_display

        except Exception as e:
            self.logger.error(f"文档处理失败: {e}")
            return f"❌ 处理失败: {str(e)}", "### 暂无已上传文件"

    def _chat_with_documents(self, message, history):
        """与文档对话"""
        try:
            if not message or not message.strip():
                history = history or []
                history.append(["", "❌ 请输入内容"])
                return history, ""

            # 检查是否有文档
            from src.shared.state.application_state import get_application_state
            app_state = get_application_state()
            if app_state.get_uploaded_files_count() == 0:
                history = history or []
                history.append([message, "❌ 请先上传 PDF 文档"])
                return history, ""

            self.logger.info(f"处理用户问题: {message}")

            # 调用聊天服务
            response, updated_history = self.chat_service.chat_with_pdf(message, history or [])

            return updated_history, ""

        except Exception as e:
            self.logger.error(f"对话处理失败: {e}")
            error_response = f"抱歉，处理您的问题时发生错误: {str(e)}"
            history = history or []
            history.append([message, error_response])
            return history, ""

    def _clear_chat(self):
        """清空对话"""
        try:
            self.chat_service.clear_conversation_history()
            return []
        except Exception as e:
            self.logger.error(f"清空对话失败: {e}")
            return []

    def _get_system_status(self):
        """获取系统状态"""
        try:
            from src.shared.state.application_state import get_application_state

            app_state = get_application_state()
            status_info = app_state.get_status_info()

            # 构建简洁的状态显示
            python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

            # 获取当前工作目录
            current_dir = os.getcwd()

            # 状态图标
            api_icon = "✅" if os.getenv('GOOGLE_API_KEY') else "❌"
            vectorstore_icon = "✅" if status_info['vectorstore_initialized'] else "❌"
            qa_chain_icon = "✅" if status_info['qa_chain_initialized'] else "❌"

            # 获取文档片段总数
            total_chunks = self._get_total_chunks_count()

            status_md = f"""
## 📊 系统状态

**Python 版本**: {python_version}

**工作目录**: {current_dir}

**API 密钥**: {api_icon} {'已配置' if os.getenv('GOOGLE_API_KEY') else '未配置'}

**当前模型**: {status_info['current_model']}

**向量数据库**: {vectorstore_icon} {'已加载' if status_info['vectorstore_initialized'] else '未加载'} ({total_chunks})

**QA 链**: {qa_chain_icon} {'已初始化' if status_info['qa_chain_initialized'] else '未初始化'}

## 📋 使用说明

1. 在"文档上传"标签页上传 PDF 文件
2. 等待处理完成（查看状态信息）
3. 在"智能对话"标签页提问
4. 系统会基于文档内容回答问题
"""
            return status_md

        except Exception as e:
            return f"❌ 获取状态失败: {str(e)}"

    def _get_model_info(self):
        """获取模型信息"""
        try:
            from src.shared.state.application_state import get_application_state
            app_state = get_application_state()
            status_info = app_state.get_status_info()

            model_md = f"""
## 🤖 可用模型列表

**默认模型**: {status_info['current_model']}

**所有可用模型**:
{chr(10).join([f'- {model}' for model in status_info['available_models']])}

**模型说明**:
- **2.5 系列**: 最新预览版本，性能最佳
- **2.0 系列**: 稳定版本，生产推荐
- **1.5 系列**: 备用版本，确保可用性
"""
            return model_md

        except Exception as e:
            return f"❌ 获取模型信息失败: {str(e)}"

    def _get_uploaded_files_display(self):
        """获取已上传文件的显示内容"""
        try:
            from src.shared.state.application_state import get_application_state
            app_state = get_application_state()
            files = app_state.get_uploaded_files()

            if not files:
                return "### 暂无已上传文件"

            file_list = ["### 📁 已上传文件\n"]

            for i, file_info in enumerate(files, 1):
                upload_time = file_info.upload_time.strftime("%Y-%m-%d %H:%M:%S")
                file_list.append(
                    f"**{i}. {file_info.name}**\n"
                    f"- 📅 上传时间: {upload_time}\n"
                    f"- 📄 页数: {file_info.pages}\n"
                    f"- 📝 文档片段: {file_info.chunks}\n"
                    f"- 🤖 处理模型: {file_info.model}\n"
                )

            return "\n".join(file_list)

        except Exception as e:
            self.logger.error(f"获取文件列表失败: {e}")
            return f"### ❌ 获取文件列表失败: {str(e)}"

    def _get_total_chunks_count(self):
        """获取总文档片段数量"""
        try:
            from src.shared.state.application_state import get_application_state
            app_state = get_application_state()
            uploaded_files = app_state.get_uploaded_files()
            return sum(f.chunks for f in uploaded_files) if uploaded_files else 0
        except:
            return 0

    def _init_model_dropdown(self):
        """初始化模型下拉框的默认值"""
        try:
            current_model = self.config_service.get_value("chat_model")
            return current_model
        except Exception as e:
            self.logger.error(f"获取默认模型失败: {e}")
            return None

    def _create_error_interface(self, error) -> gr.Blocks:
        """创建错误界面

        Args:
            error: 错误信息

        Returns:
            显示错误的Gradio界面
        """
        with gr.Blocks(title="Web RAG 系统 - 错误") as error_demo:
            gr.Markdown("# ❌ 系统错误")
            gr.Markdown(f"**错误信息**: {str(error)}")
            gr.Markdown("**解决方案**: 请检查依赖配置和环境设置")

        return error_demo

    def launch(self, **kwargs) -> None:
        """启动界面

        Args:
            **kwargs: Gradio launch参数
        """
        if self.demo is None:
            print("❌ 界面未构建，请先调用 build_interface()")
            return

        try:
            print("🚀 启动 Web RAG 系统 v4.0 (企业级版)...")
            print(f"📋 API 密钥状态: {'✅ 已配置' if os.getenv('GOOGLE_API_KEY') else '❌ 未配置'}")
            print(f"🏗️ 架构: 企业级分层架构 + 性能优化 + 扩展性增强")
            print(f"🎯 当前模型: {self.model_service.get_current_model()}")

            # 检测运行环境
            is_spaces = os.getenv("SPACE_ID") is not None

            if is_spaces:
                # Hugging Face Spaces 环境配置
                default_kwargs = {"share": True}
            else:
                # 本地开发环境配置
                default_kwargs = {
                    "server_name": "127.0.0.1",
                    "server_port": 7860,  # 改为7860避免端口冲突
                    "share": False,
                    "show_error": True,
                    "inbrowser": False,
                    "debug": True
                }

            # 合并用户提供的参数
            launch_kwargs = {**default_kwargs, **kwargs}

            # 启动界面
            self.demo.launch(**launch_kwargs)

        except Exception as e:
            print(f"❌ 启动失败: {e}")
            print(f"错误详情: {traceback.format_exc()}")

    def get_demo(self) -> gr.Blocks:
        """获取Gradio demo实例

        Returns:
            Gradio Blocks实例
        """
        return self.demo
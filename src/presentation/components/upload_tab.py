"""
文档上传Tab组件
处理PDF文件上传和模型配置的UI界面
"""

from typing import Any, Dict, List
import gradio as gr
from src.presentation.controllers.ui_controller import TabController


class UploadTabController(TabController):
    """文档上传Tab控制器

    管理PDF文件上传、模型选择和处理状态显示
    """

    def __init__(self, document_service, model_service, config_service, logger):
        """初始化上传Tab控制器

        Args:
            document_service: 文档处理服务实例
            model_service: 模型管理服务实例
            config_service: 配置服务实例
            logger: 日志服务实例
        """
        super().__init__("upload_tab", "📄 文档上传")
        self.document_service = document_service
        self.model_service = model_service
        self.config_service = config_service
        self.logger = logger

    def create_components(self) -> Dict[str, Any]:
        """创建上传Tab的UI组件"""
        return {}

    def setup_events(self) -> List[Dict[str, Any]]:
        """设置事件绑定配置"""
        return [
            {
                "component": "upload_file",
                "event": "upload",
                "handler": "process_document_with_model",
                "inputs": ["upload_file", "model_dropdown"],
                "outputs": ["upload_status", "uploaded_files_display"]
            }
        ]

    def _render_content(self) -> None:
        """渲染上传Tab页面内容"""
        gr.Markdown("## 上传文档")
        gr.Markdown("**支持格式**: PDF、Word(.docx)、Excel(.xlsx)、PowerPoint(.pptx)、Markdown(.md)、文本(.txt)")
        gr.Markdown("注意: 上传后请等待处理完成，状态会显示在下方")

        with gr.Row():
            with gr.Column(scale=2):
                self.components["upload_file"] = gr.File(
                    label="📄 选择文档文件",
                    file_types=[".pdf", ".docx", ".xlsx", ".pptx", ".txt", ".md"],
                    type="filepath"
                )
            with gr.Column(scale=1):
                with gr.Group():
                    gr.Markdown("### 🤖 模型配置")

                    # 获取可用模型和当前模型
                    available_models = self.config_service.get_value("fallback_models")
                    current_model = self.model_service.get_current_model()  # 使用model_service获取当前模型

                    self.components["model_dropdown"] = gr.Dropdown(
                        label="选择 Gemini 模型",
                        choices=available_models,
                        value=current_model,  # 设置默认值
                        interactive=True
                    )

        gr.Markdown("### 处理状态")
        self.components["upload_status"] = gr.Textbox(
            label="状态",
            value="等待文件上传...",
            interactive=False
        )

        # 已上传文件列表显示 - 修改为可更新的组件
        self.components["uploaded_files_display"] = gr.Markdown("### 暂无已上传文件")

    def get_event_handlers(self):
        """获取事件处理函数"""
        return {
            "process_document_with_model": self._process_document_with_model
        }

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

            # 使用统一的文档处理方法
            result_message = self.document_service.process_document(file_path)

            # 获取更新后的文件列表
            updated_files_display = self._get_uploaded_files_display()

            return result_message, updated_files_display

        except Exception as e:
            self.logger.error(f"文档处理失败: {e}")
            return f"❌ 处理失败: {str(e)}", "### 暂无已上传文件"

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
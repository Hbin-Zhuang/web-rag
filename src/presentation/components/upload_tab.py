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

    def __init__(self, document_service, model_service):
        """初始化上传Tab控制器

        Args:
            document_service: 文档处理服务实例
            model_service: 模型管理服务实例
        """
        super().__init__("upload_tab", "📄 文档上传")
        self.document_service = document_service
        self.model_service = model_service

    def create_components(self) -> Dict[str, Any]:
        """创建上传Tab的UI组件"""
        # 注意：这些组件将在_render_content中创建
        # 这里返回空字典，因为Gradio组件需要在with语句内创建
        return {}

    def setup_events(self) -> List[Dict[str, Any]]:
        """设置事件绑定配置"""
        return [
            {
                "component": "file_input",
                "event": "upload",
                "handler": "process_pdf_and_update_status",
                "inputs": ["file_input", "model_dropdown"],
                "outputs": ["upload_output", "model_status", "status_output", "uploaded_files_display"]
            },
            {
                "component": "file_input",
                "event": "clear",
                "handler": "clear_file_status",
                "inputs": [],
                "outputs": ["upload_output"]
            },
            {
                "component": "model_dropdown",
                "event": "change",
                "handler": "switch_model",
                "inputs": ["model_dropdown"],
                "outputs": ["model_status", "model_dropdown"]
            }
        ]

    def _render_content(self) -> None:
        """渲染上传Tab页面内容"""
        gr.Markdown("### 上传 PDF 文档")
        gr.Markdown("**注意**: 上传后请等待处理完成，状态会显示在下方")

        with gr.Row():
            with gr.Column(scale=2):
                # 文件上传组件
                self.components["file_input"] = gr.File(
                    label="选择 PDF 文件",
                    file_types=[".pdf"]
                )

                # 处理状态显示
                self.components["upload_output"] = gr.Textbox(
                    label="处理状态",
                    lines=6,
                    interactive=False,
                    placeholder="等待文件上传..."
                )

                # 已上传文件列表
                self.components["uploaded_files_display"] = gr.Markdown(
                    label="已上传文件列表",
                    value="*暂无已上传文件*"
                )

            with gr.Column(scale=1):
                gr.Markdown("### 🤖 模型配置")

                # 模型选择下拉框
                self.components["model_dropdown"] = gr.Dropdown(
                    choices=self.model_service.get_available_models(),
                    value=self.model_service.get_current_model(),
                    label="选择 Gemini 模型",
                    info="选择后自动切换模型"
                )

                # 模型状态显示
                self.components["model_status"] = gr.Textbox(
                    label="模型状态",
                    value=self.model_service.get_model_status(),
                    interactive=False,
                    lines=5
                )

        # 预留给其他组件的引用
        self.components["status_output"] = None  # 将在主界面中设置

    def get_event_handlers(self):
        """获取事件处理函数

        Returns:
            包含所有事件处理函数的字典
        """
        return {
            "process_pdf_and_update_status": self._process_pdf_and_update_status,
            "clear_file_status": self._clear_file_status,
            "switch_model": self._switch_model
        }

    def _process_pdf_and_update_status(self, file, selected_model):
        """处理PDF文件上传并更新状态 - 事件处理器"""
        try:
            if file is None:
                return "❌ 请先选择文件", "等待文件上传...", "系统待机中", "*暂无已上传文件*"

            # 切换模型（如果需要）
            if selected_model != self.model_service.get_current_model():
                model_status, _ = self.model_service.switch_model(selected_model)
            else:
                model_status = self.model_service.get_model_status()

            # 处理PDF文件
            result = self.document_service.process_pdf(file.name)

            # 获取更新后的状态信息
            from src.application.services.model_service import ModelService
            from src.application.services.document_service import DocumentService
            from src.shared.state.application_state import ApplicationState

            # 创建状态显示（简化版，避免循环依赖）
            state = ApplicationState()
            files_count = len(state.get_uploaded_files())
            status_info = f"✅ 系统运行正常\n\n📊 **文档统计**: {files_count} 个文件已处理"

            # 获取文件列表显示
            files_display = self.document_service._get_uploaded_files_display()

            return result, model_status, status_info, files_display

        except Exception as e:
            error_msg = f"❌ 处理失败: {str(e)}"
            return error_msg, self.model_service.get_model_status(), "系统遇到错误", "*暂无已上传文件*"

    def _clear_file_status(self):
        """清除文件状态 - 事件处理器"""
        return "等待文件上传..."

    def _switch_model(self, selected_model):
        """切换模型 - 事件处理器"""
        try:
            model_status, current_model = self.model_service.switch_model(selected_model)
            return model_status, current_model
        except Exception as e:
            error_msg = f"❌ 模型切换失败: {str(e)}"
            return error_msg, self.model_service.get_current_model()

    def set_status_output_component(self, status_component):
        """设置状态输出组件的引用

        Args:
            status_component: 系统状态显示组件
        """
        self.components["status_output"] = status_component
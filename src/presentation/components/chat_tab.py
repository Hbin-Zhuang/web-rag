"""
智能对话Tab组件
处理与文档内容的智能对话界面
"""

from typing import Any, Dict, List
import gradio as gr
from src.presentation.controllers.ui_controller import TabController


class ChatTabController(TabController):
    """智能对话Tab控制器

    管理聊天界面、消息输入和对话历史
    """

    def __init__(self, chat_service, logger):
        """初始化对话Tab控制器

        Args:
            chat_service: 聊天服务实例
            logger: 日志服务实例
        """
        super().__init__("chat_tab", "💬 智能对话")
        self.chat_service = chat_service
        self.logger = logger

    def create_components(self) -> Dict[str, Any]:
        """创建对话Tab的UI组件"""
        return {}

    def setup_events(self) -> List[Dict[str, Any]]:
        """设置事件绑定配置"""
        return [
            {
                "component": "msg",
                "event": "submit",
                "handler": "chat_with_documents",
                "inputs": ["msg", "chatbot"],
                "outputs": ["chatbot", "msg"]
            },
            {
                "component": "send_btn",
                "event": "click",
                "handler": "chat_with_documents",
                "inputs": ["msg", "chatbot"],
                "outputs": ["chatbot", "msg"]
            },
            {
                "component": "clear_btn",
                "event": "click",
                "handler": "clear_chat",
                "inputs": [],
                "outputs": ["chatbot"]
            }
        ]

    def _render_content(self) -> None:
        """渲染对话Tab页面内容"""
        gr.Markdown("## 与文档内容对话")
        gr.Markdown("提示: 请先上传并处理 PDF 文件，然后在此提问")

        self.components["chatbot"] = gr.Chatbot(
            label="对话历史",
            height=400
        )

        with gr.Row():
            self.components["msg"] = gr.Textbox(
                label="输入您的问题",
                placeholder="请输入您想要询问的问题...",
                lines=3,
                scale=4
            )
            with gr.Column(scale=1):
                self.components["send_btn"] = gr.Button("发送", variant="primary")
                self.components["clear_btn"] = gr.Button("清除对话")

    def get_event_handlers(self):
        """获取事件处理函数"""
        return {
            "chat_with_documents": self._chat_with_documents,
            "clear_chat": self._clear_chat
        }

    def _chat_with_documents(self, message, history):
        """与文档对话"""
        try:
            if not message.strip():
                return history, ""

            self.logger.info(f"处理用户问题: {message}")

            # 使用正确的方法名 chat_with_pdf
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
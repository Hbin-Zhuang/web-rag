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

    def __init__(self, chat_service):
        """初始化对话Tab控制器

        Args:
            chat_service: 聊天服务实例
        """
        super().__init__("chat_tab", "💬 智能对话")
        self.chat_service = chat_service

    def create_components(self) -> Dict[str, Any]:
        """创建对话Tab的UI组件"""
        # 组件将在_render_content中创建
        return {}

    def setup_events(self) -> List[Dict[str, Any]]:
        """设置事件绑定配置"""
        return [
            {
                "component": "msg_input",
                "event": "submit",
                "handler": "chat_with_pdf",
                "inputs": ["msg_input", "chatbot"],
                "outputs": ["chatbot", "msg_input"]
            },
            {
                "component": "submit_btn",
                "event": "click",
                "handler": "chat_with_pdf",
                "inputs": ["msg_input", "chatbot"],
                "outputs": ["chatbot", "msg_input"]
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
        gr.Markdown("### 与文档内容对话")
        gr.Markdown("**提示**: 请先上传并处理 PDF 文件，然后在此提问")

        # 聊天机器人组件
        self.components["chatbot"] = gr.Chatbot(
            label="对话历史",
            height=500,
            placeholder="上传PDF文件后，在下方输入问题开始对话"
        )

        # 消息输入框
        self.components["msg_input"] = gr.Textbox(
            label="输入消息",
            placeholder="请输入您的问题...",
            lines=2,
            scale=4
        )

        # 按钮组
        with gr.Row():
            self.components["submit_btn"] = gr.Button(
                "发送",
                variant="primary",
                scale=1
            )
            self.components["clear_btn"] = gr.Button(
                "清除对话",
                variant="secondary",
                scale=1
            )

    def get_event_handlers(self):
        """获取事件处理函数

        Returns:
            包含所有事件处理函数的字典
        """
        return {
            "chat_with_pdf": self._chat_with_pdf,
            "clear_chat": self._clear_chat
        }

    def _chat_with_pdf(self, message, history):
        """与PDF文档聊天 - 事件处理器"""
        try:
            if not message or not message.strip():
                return history, ""

            # 调用聊天服务
            response = self.chat_service.chat_with_pdf(message)

            # 添加到聊天历史
            history = history or []
            history.append([message, response])

            return history, ""  # 清空输入框

        except Exception as e:
            error_response = f"❌ 聊天失败: {str(e)}"
            history = history or []
            history.append([message, error_response])
            return history, ""

    def _clear_chat(self):
        """清除聊天历史 - 事件处理器"""
        return []  # 返回空列表清除chatbot内容
"""
主UI控制器
集成所有Tab控制器和事件管理，构建完整的Gradio界面
"""

from typing import Any, Dict
import gradio as gr
import os
import traceback

from src.presentation.controllers.ui_controller import UIController
from src.presentation.components.upload_tab import UploadTabController
from src.presentation.components.chat_tab import ChatTabController
from src.presentation.components.status_tab import StatusTabController
from src.presentation.handlers.event_manager import EventManager, CrossTabEventManager


class MainUIController(UIController):
    """主UI控制器

    负责协调所有Tab控制器，管理整体UI架构和事件系统
    """

    def __init__(self, document_service, chat_service, model_service):
        """初始化主UI控制器

        Args:
            document_service: 文档处理服务
            chat_service: 聊天服务
            model_service: 模型管理服务
        """
        super().__init__("main_ui")

        # 服务依赖
        self.document_service = document_service
        self.chat_service = chat_service
        self.model_service = model_service

        # Tab控制器
        self.upload_tab = UploadTabController(document_service, model_service)
        self.chat_tab = ChatTabController(chat_service)
        self.status_tab = StatusTabController(model_service, document_service)

        # 事件管理器
        self.event_manager = EventManager()
        self.cross_tab_manager = CrossTabEventManager(self.event_manager)

        # Gradio界面实例
        self.demo = None

        # 初始化组件
        self.initialize()

    def create_components(self) -> Dict[str, Any]:
        """创建主界面组件"""
        return {
            "upload_tab": self.upload_tab,
            "chat_tab": self.chat_tab,
            "status_tab": self.status_tab
        }

    def setup_events(self) -> Dict[str, Any]:
        """设置事件绑定"""
        # 注册各Tab控制器的事件
        self.event_manager.register_controller_events(self.upload_tab)
        self.event_manager.register_controller_events(self.chat_tab)
        self.event_manager.register_controller_events(self.status_tab)

        return []

    def build_interface(self) -> gr.Blocks:
        """构建完整的Gradio界面

        Returns:
            配置完成的Gradio Blocks实例
        """
        try:
            # 创建主界面
            with gr.Blocks(
                title="Web RAG 系统 (重构版 v2.0)",
                theme=gr.themes.Soft()
            ) as self.demo:

                # 标题和说明
                gr.Markdown("# 🚀 Web RAG 系统 (重构版 v2.0)")
                gr.Markdown("基于 Google Gemini 的智能文档问答系统 - 采用分层架构设计")

                # 渲染各个Tab页面
                self.upload_tab.render()
                self.chat_tab.render()
                self.status_tab.render()

                # 设置跨Tab组件引用
                self._setup_cross_tab_references()

            # 设置事件绑定
            self._setup_all_events()

            return self.demo

        except Exception as e:
            print(f"❌ 构建界面失败: {e}")
            print(f"错误详情: {traceback.format_exc()}")
            return self._create_error_interface(e)

    def _setup_cross_tab_references(self) -> None:
        """设置跨Tab组件引用"""
        try:
            # 设置上传Tab对状态Tab的引用
            status_component = self.status_tab.get_status_component()
            if status_component:
                self.upload_tab.set_status_output_component(status_component)

        except Exception as e:
            print(f"⚠️ 设置跨Tab引用失败: {e}")

    def _setup_all_events(self) -> None:
        """设置所有事件绑定"""
        try:
            # 初始化控制器
            self.upload_tab.initialize()
            self.chat_tab.initialize()
            self.status_tab.initialize()

            # 绑定所有事件
            self.event_manager.bind_all_events()

            # 设置跨Tab事件（如果需要）
            self.cross_tab_manager.setup_cross_tab_events()

            # 打印事件管理器摘要
            self.event_manager.print_summary()

        except Exception as e:
            print(f"❌ 设置事件绑定失败: {e}")

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
            print("🚀 启动 Web RAG 系统 (重构版 v2.0)...")
            print(f"📋 API 密钥状态: {'✅ 已配置' if os.getenv('GOOGLE_API_KEY') else '❌ 未配置'}")
            print(f"🏗️ 架构: 分层架构 + 组件化UI")
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
                    "server_port": 7862,  # 使用新端口
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

    def print_architecture_info(self) -> None:
        """打印架构信息"""
        print("🏗️ UI架构信息:")
        print(f"   - 主控制器: {self.name}")
        print(f"   - Tab控制器: {len(self.components)} 个")
        print(f"     - 上传Tab: {self.upload_tab.name}")
        print(f"     - 聊天Tab: {self.chat_tab.name}")
        print(f"     - 状态Tab: {self.status_tab.name}")
        print(f"   - 事件管理器: {self.event_manager.get_handler_count()} 个处理器")
        print(f"   - 事件绑定: {self.event_manager.get_event_count()} 个")
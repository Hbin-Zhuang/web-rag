"""
系统状态Tab组件
处理系统状态监控和信息显示界面
"""

from typing import Any, Dict, List
import gradio as gr
import os
import sys
from src.presentation.controllers.ui_controller import TabController


class StatusTabController(TabController):
    """系统状态Tab控制器

    管理系统状态显示、模型信息和状态刷新
    """

    def __init__(self, model_service, document_service, logger):
        """初始化状态Tab控制器

        Args:
            model_service: 模型管理服务实例
            document_service: 文档处理服务实例
            logger: 日志服务实例
        """
        super().__init__("status_tab", "📊 系统状态")
        self.model_service = model_service
        self.document_service = document_service
        self.logger = logger

    def create_components(self) -> Dict[str, Any]:
        """创建状态Tab的UI组件"""
        return {}

    def setup_events(self) -> List[Dict[str, Any]]:
        """设置事件绑定配置"""
        return [
            {
                "component": "refresh_btn",
                "event": "click",
                "handler": "refresh_status",
                "inputs": [],
                "outputs": ["system_status", "model_info"]
            }
        ]

    def _render_content(self) -> None:
        """渲染状态Tab页面内容"""
        gr.Markdown("## 🔧 系统状态")

        with gr.Row():
            with gr.Column(scale=1):
                self.components["refresh_btn"] = gr.Button("🔄 刷新状态", variant="primary")
            with gr.Column(scale=2):
                pass  # 空列占位

        with gr.Row():
            with gr.Column(scale=2):
                self.components["system_status"] = gr.Markdown("🔄 正在获取系统状态...")
            with gr.Column(scale=1):
                self.components["model_info"] = gr.Markdown("🔄 正在获取模型信息...")

        gr.Markdown("## 🔧 技术栈")
        tech_info = gr.Markdown("""
**LLM**: Google Gemini (自动选择可用模型)

**嵌入模型**: Google Embedding-001

**向量数据库**: ChromaDB

**框架**: LangChain + Gradio
""")

    def get_event_handlers(self):
        """获取事件处理函数"""
        return {
            "refresh_status": self._refresh_status
        }

    def _refresh_status(self):
        """刷新状态"""
        return self._get_system_status(), self._get_model_info()

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

            status_md = f"""
## 📊 系统状态

**Python 版本**: {python_version}

**工作目录**: {current_dir}

**API 密钥**: {api_icon} {'已配置' if os.getenv('GOOGLE_API_KEY') else '未配置'}

**当前模型**: {status_info['current_model']}

**向量数据库**: {vectorstore_icon} {'已加载' if status_info['vectorstore_initialized'] else '未加载'}

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

    def get_status_component(self):
        """获取状态输出组件

        用于其他Tab组件更新状态显示

        Returns:
            状态输出组件
        """
        return self.components.get("system_status")
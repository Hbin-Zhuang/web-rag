"""
系统状态Tab组件
处理系统状态监控和信息显示界面
"""

from typing import Any, Dict, List
import gradio as gr
from src.presentation.controllers.ui_controller import TabController


class StatusTabController(TabController):
    """系统状态Tab控制器

    管理系统状态显示、模型信息和状态刷新
    """

    def __init__(self, model_service, document_service):
        """初始化状态Tab控制器

        Args:
            model_service: 模型管理服务实例
            document_service: 文档处理服务实例
        """
        super().__init__("status_tab", "⚙️ 系统状态")
        self.model_service = model_service
        self.document_service = document_service

    def create_components(self) -> Dict[str, Any]:
        """创建状态Tab的UI组件"""
        # 组件将在_render_content中创建
        return {}

    def setup_events(self) -> List[Dict[str, Any]]:
        """设置事件绑定配置"""
        return [
            {
                "component": "refresh_btn",
                "event": "click",
                "handler": "get_system_status",
                "inputs": [],
                "outputs": ["status_output"]
            }
        ]

    def _render_content(self) -> None:
        """渲染状态Tab页面内容"""
        with gr.Row():
            with gr.Column(scale=2):
                # 系统状态显示
                self.components["status_output"] = gr.Markdown(
                    value=self._get_system_status(),
                    label="系统状态"
                )

                # 刷新按钮
                self.components["refresh_btn"] = gr.Button(
                    "🔄 刷新状态",
                    variant="secondary"
                )

            with gr.Column(scale=1):
                gr.Markdown("### 📋 模型信息")

                # 模型信息显示
                self.components["models_info"] = gr.Markdown(
                    value=self.model_service.get_model_selection_info()
                )

    def get_event_handlers(self):
        """获取事件处理函数

        Returns:
            包含所有事件处理函数的字典
        """
        return {
            "get_system_status": self._get_system_status
        }

    def _get_system_status(self):
        """获取系统状态信息 - 事件处理器"""
        try:
            from src.shared.state.application_state import ApplicationState
            from datetime import datetime
            import os

            # 获取应用状态
            state = ApplicationState()
            state_info = state.get_status_info()

            # 构建状态显示
            status = f"""
## 🚀 Web RAG 系统状态 (v2.0 重构版)

---

## 📊 系统概览

**架构版本**: v2.0 分层架构

**运行状态**: {'🟢 正常运行' if state_info['vectorstore_ready'] or state_info['qa_chain_ready'] else '🟡 待机状态'}

**当前模型**: {state_info['current_model']}

**向量库状态**: {'✅ 已就绪' if state_info['vectorstore_ready'] else '⏳ 未初始化'}

**问答链状态**: {'✅ 已就绪' if state_info['qa_chain_ready'] else '⏳ 未初始化'}

**已上传文件**: {len(state_info['uploaded_files'])} 个

**最后更新**: {datetime.fromisoformat(state_info['last_update']).strftime('%Y-%m-%d %H:%M:%S')}

---

## 📋 使用说明

1. 在"文档上传"标签页上传 PDF 文件
2. 等待处理完成（查看状态信息）
3. 在"智能对话"标签页提问
4. 系统会基于文档内容回答问题

---

## 🔧 技术栈

**LLM**: Google Gemini (当前: {state_info['current_model']})

**嵌入模型**: Google Embedding-001

**向量数据库**: ChromaDB

**框架**: LangChain + Gradio

**架构**: 分层架构 (服务层 + 状态管理)

---

## 🚀 支持的 Gemini 模型

**最新 2.5 系列 (Preview)**
- `gemini-2.5-flash-preview-05-20` - 最新 Flash，支持思维链推理

**稳定 2.0 系列**
- `gemini-2.0-flash` - 下一代特性，生产环境推荐
- `gemini-2.0-flash-lite` - 成本优化版，高频调用

**备用 1.5 系列**
- `gemini-1.5-flash` - 快速多模态处理
- `gemini-1.5-pro` - 复杂推理任务

---

## 💡 模型选择策略

系统会自动按优先级尝试模型：
1. **优先**: 最新 2.5 系列（性能最佳）
2. **备选**: 稳定 2.0 系列（生产可靠）
3. **兜底**: 1.5 系列（确保可用性）

---

"""
            return status

        except Exception as e:
            return f"❌ 获取系统状态失败: {str(e)}"

    def get_status_component(self):
        """获取状态输出组件

        用于其他Tab组件更新状态显示

        Returns:
            状态输出组件
        """
        return self.components.get("status_output")
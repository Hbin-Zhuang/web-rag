#!/usr/bin/env python3
"""
Web RAG 系统 - 主程序 (重构版本)
基于 Google Gemini 的智能文档问答系统 - 采用分层架构设计
"""

import gradio as gr
import os
import sys
import traceback
from datetime import datetime

# 导入配置管理
from config import Config

# 导入服务层
from src.application.services import DocumentService, ChatService, ModelService
from src.shared.state.application_state import app_state

# 验证配置
if not Config.validate_config():
    print("❌ 配置错误：请设置GOOGLE_API_KEY环境变量")
    print("💡 提示：")
    print("   1. 复制 .env.example 为 .env")
    print("   2. 在 .env 文件中填入您的 Google API Key")
    print("   3. 或设置环境变量: export GOOGLE_API_KEY=your_key_here")
    print("   4. 获取API Key: https://aistudio.google.com/")
    sys.exit(1)

# 设置环境变量（从配置中读取）
os.environ["GOOGLE_API_KEY"] = Config.GOOGLE_API_KEY

try:
    # 初始化服务实例
    document_service = DocumentService()
    chat_service = ChatService()
    model_service = ModelService()

    def process_pdf_and_update_status(file, selected_model):
        """
        处理PDF并更新系统状态 - 事件处理器

        Args:
            file: 上传的文件对象
            selected_model: 选择的模型

        Returns:
            (upload_status, model_status, system_status, file_list)
        """
        try:
            return document_service.process_pdf_and_update_status(file, selected_model)
        except Exception as e:
            error_msg = f"❌ 处理失败: {str(e)}"
            print(f"处理PDF错误: {e}")
            print(f"错误详情: {traceback.format_exc()}")
            return error_msg, "模型状态获取失败", "系统状态获取失败", "文件列表获取失败"

    def chat_with_pdf(message, history):
        """
        与PDF内容对话 - 事件处理器

        Args:
            message: 用户输入的消息
            history: 对话历史

        Returns:
            (更新后的历史, 清空的输入框)
        """
        try:
            answer, updated_history = chat_service.chat_with_pdf(message, history)
            return updated_history, ""
        except Exception as e:
            error_msg = f"❌ 对话失败: {str(e)}"
            print(f"对话错误: {e}")
            print(f"错误详情: {traceback.format_exc()}")
            history.append([message, error_msg])
            return history, ""

    def switch_model(selected_model):
        """
        切换模型 - 事件处理器

        Args:
            selected_model: 选择的模型名称

        Returns:
            (状态消息, 当前选择的模型)
        """
        try:
            success, message = model_service.switch_model(selected_model)
            if success:
                # 重置聊天服务的QA链，强制使用新模型
                chat_service.reset_qa_chain()
                return message, selected_model
            else:
                # 切换失败，返回原模型
                current_model = model_service.get_current_model()
                return message, current_model
        except Exception as e:
            error_msg = f"❌ 模型切换异常: {str(e)}"
            print(f"模型切换错误: {e}")
            current_model = model_service.get_current_model()
            return error_msg, current_model

    def get_system_status():
        """获取系统状态 - 事件处理器"""
        try:
            state_info = app_state.get_state_info()

            # 检查向量数据库状态
            vectorstore_status = "❌ 未加载"
            if state_info['vectorstore_initialized']:
                vectorstore_status = "✅ 已加载"

            # 检查QA链状态
            qa_status = "❌ 未初始化" if not state_info['qa_chain_initialized'] else "✅ 已初始化"

            status = f"""
## 📊 系统状态

**Python 版本**: {sys.version.split()[0]}

**工作目录**: {os.getcwd()}

**API 密钥**: {'✅ 已配置' if os.getenv('GOOGLE_API_KEY') else '❌ 未配置'}

**当前模型**: {state_info['current_model']}

**向量数据库**: {vectorstore_status}

**QA 链**: {qa_status}

**已上传文档**: {state_info['uploaded_files_count']} 个

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

    def get_uploaded_files_display():
        """获取已上传文件列表的显示内容 - 事件处理器"""
        try:
            return document_service._get_uploaded_files_display()
        except Exception as e:
            return f"❌ 获取文件列表失败: {str(e)}"

    # 创建 Gradio 界面
    with gr.Blocks(title="Web RAG 系统 (重构版)", theme=gr.themes.Soft()) as demo:
        gr.Markdown("# 🚀 Web RAG 系统 (重构版)")
        gr.Markdown("基于 Google Gemini 的智能文档问答系统 - 采用分层架构设计")

        with gr.Tab("📄 文档上传"):
            gr.Markdown("### 上传 PDF 文档")
            gr.Markdown("**注意**: 上传后请等待处理完成，状态会显示在下方")

            with gr.Row():
                with gr.Column(scale=2):
                    file_input = gr.File(
                        label="选择 PDF 文件",
                        file_types=[".pdf"]
                    )
                    upload_output = gr.Textbox(
                        label="处理状态",
                        lines=6,
                        interactive=False,
                        placeholder="等待文件上传..."
                    )

                    # 已上传文件列表
                    uploaded_files_display = gr.Markdown(
                        label="已上传文件列表",
                        value="*暂无已上传文件*"
                    )

                with gr.Column(scale=1):
                    gr.Markdown("### 🤖 模型配置")
                    model_dropdown = gr.Dropdown(
                        choices=model_service.get_available_models(),
                        value=model_service.get_current_model(),
                        label="选择 Gemini 模型",
                        info="选择后自动切换模型"
                    )
                    model_status = gr.Textbox(
                        label="模型状态",
                        value=model_service.get_model_status(),
                        interactive=False,
                        lines=5
                    )

        with gr.Tab("💬 智能对话"):
            gr.Markdown("### 与文档内容对话")
            gr.Markdown("**提示**: 请先上传并处理 PDF 文件，然后在此提问")

            chatbot = gr.Chatbot()
            msg = gr.Textbox()
            with gr.Row():
                submit_btn = gr.Button("发送")
                clear_btn = gr.Button("清除对话")

            # 绑定对话事件
            msg.submit(chat_with_pdf, [msg, chatbot], [chatbot, msg])
            submit_btn.click(chat_with_pdf, [msg, chatbot], [chatbot, msg])
            clear_btn.click(lambda: [], None, chatbot)

        with gr.Tab("⚙️ 系统状态"):
            with gr.Row():
                with gr.Column(scale=2):
                    status_output = gr.Markdown(
                        value=get_system_status(),
                        label="系统状态"
                    )
                    refresh_btn = gr.Button("🔄 刷新状态", variant="secondary")

                    # 刷新按钮事件
                    refresh_btn.click(
                        fn=get_system_status,
                        outputs=status_output
                    )

                with gr.Column(scale=1):
                    gr.Markdown("### 📋 模型信息")
                    models_info = gr.Markdown(
                        value=model_service.get_model_selection_info()
                    )

        # 事件绑定 - 在所有组件定义完成后
        # 文件上传事件
        file_input.upload(
            fn=process_pdf_and_update_status,
            inputs=[file_input, model_dropdown],
            outputs=[upload_output, model_status, status_output, uploaded_files_display]
        )

        # 文件清除时重置状态
        file_input.clear(
            fn=lambda: "等待文件上传...",
            inputs=None,
            outputs=upload_output
        )

        # 模型下拉框改变时自动切换
        model_dropdown.change(
            fn=switch_model,
            inputs=model_dropdown,
            outputs=[model_status, model_dropdown]  # 同时更新状态和下拉框值
        )

except ImportError as e:
    print(f"❌ 导入错误: {e}")

    # 创建简化版界面
    with gr.Blocks(title="Web RAG 系统") as demo:
        gr.Markdown("# ❌ 依赖缺失")
        gr.Markdown(f"**错误**: {e}")
        gr.Markdown("**解决方案**: 请运行 `pip3 install langchain langchain-google-genai langchain-community chromadb`")

if __name__ == "__main__":
    try:
        print("🚀 启动 Web RAG 系统 (重构版)...")
        print(f"📋 API 密钥状态: {'✅ 已配置' if os.getenv('GOOGLE_API_KEY') else '❌ 未配置'}")
        print(f"🏗️ 架构: 分层架构 + 服务模式")
        print(f"🎯 当前模型: {model_service.get_current_model()}")

        # 检测运行环境
        is_spaces = os.getenv("SPACE_ID") is not None

        if is_spaces:
            # Hugging Face Spaces 环境配置
            demo.launch(share=True)
        else:
            # 本地开发环境配置
            demo.launch(
                server_name="127.0.0.1",
                server_port=7861,  # 使用不同端口避免冲突
                share=False,
                show_error=True,
                inbrowser=False,
                debug=True  # 启用调试模式
            )
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        print(f"错误详情: {traceback.format_exc()}")
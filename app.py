#!/usr/bin/env python3
"""
Web RAG 系统 v4.0 (企业级版)
基于 Google Gemini 的智能文档问答系统
"""

import os
import sys
import traceback
import gradio as gr
from datetime import datetime

# 导入基础设施层
try:
    from src.infrastructure import (
        initialize_infrastructure,
        get_config,
        get_logger,
        get_metrics_service,
        get_health_check_service,
        create_performance_dashboard
    )

    # 初始化基础设施
    initialize_infrastructure()

    # 获取基础设施服务
    config_service = get_config()
    logger = get_logger()

    logger.info("Web RAG 系统启动", extra={
        "environment": config_service.get_environment().value,
        "version": "v4.0"
    })

    # 导入服务层
    from src.application.services.document_service import DocumentService
    from src.application.services.chat_service import ChatService
    from src.application.services.model_service import ModelService
    from src.shared.state.application_state import ApplicationState

    # 初始化应用状态和服务
    application_state = ApplicationState()

    # 创建服务实例
    model_service = ModelService(config_service, logger)
    document_service = DocumentService(
        model_service=model_service,
        config_service=config_service,
        logger_service=logger
    )
    chat_service = ChatService(model_service)

    logger.info("Web RAG 系统初始化完成")

    # 创建界面 - 恢复简洁设计
    with gr.Blocks(
        title="Web RAG 系统",
        theme=gr.themes.Soft()
    ) as demo:
        gr.Markdown("# 🚀 Web RAG 系统")
        gr.Markdown("基于 Google Gemini 的智能文档问答系统")

        with gr.Tabs():
            # 文档上传标签页
            with gr.TabItem("📄 文档上传", id="upload"):
                gr.Markdown("## 上传 PDF 文档")
                gr.Markdown("注意: 上传后请等待处理完成，状态会显示在下方")

                with gr.Row():
                    with gr.Column(scale=2):
                        upload_file = gr.File(
                            label="📄 选择 PDF 文件",
                            file_types=[".pdf"],
                            type="filepath"
                        )
                    with gr.Column(scale=1):
                        with gr.Group():
                            gr.Markdown("### 🤖 模型配置")

                            # 获取可用模型和当前模型
                            available_models = config_service.get_value("fallback_models")
                            current_model = config_service.get_value("chat_model")

                            model_dropdown = gr.Dropdown(
                                label="选择 Gemini 模型",
                                choices=available_models,
                                value=current_model,  # 设置默认值
                                interactive=True
                            )

                gr.Markdown("### 处理状态")
                upload_status = gr.Textbox(
                    label="状态",
                    value="等待文件上传...",
                    interactive=False
                )

                # 已上传文件列表显示 - 修改为可更新的组件
                uploaded_files_display = gr.Markdown("### 暂无已上传文件")

            # 智能问答标签页
            with gr.TabItem("💬 智能问答", id="chat"):
                gr.Markdown("## 与文档内容对话")
                gr.Markdown("提示: 请先上传并处理 PDF 文件，然后在此提问")

                chatbot = gr.Chatbot(
                    label="对话历史",
                    height=400
                )

                with gr.Row():
                    msg = gr.Textbox(
                        label="输入您的问题",
                        placeholder="请输入您想要询问的问题...",
                        lines=3,
                        scale=4
                    )
                    with gr.Column(scale=1):
                        send_btn = gr.Button("发送", variant="primary")
                        clear_btn = gr.Button("清除对话")

            # 系统状态标签页
            with gr.TabItem("📊 系统状态", id="status"):
                gr.Markdown("## 🔧 系统状态")

                with gr.Row():
                    with gr.Column(scale=1):
                        refresh_btn = gr.Button("🔄 刷新状态", variant="primary")
                    with gr.Column(scale=2):
                        pass  # 空列占位

                with gr.Row():
                    with gr.Column(scale=2):
                        system_status = gr.Markdown("🔄 正在获取系统状态...")
                    with gr.Column(scale=1):
                        model_info = gr.Markdown("🔄 正在获取模型信息...")

                gr.Markdown("## 🔧 技术栈")
                tech_info = gr.Markdown("""
**LLM**: Google Gemini (自动选择可用模型)

**嵌入模型**: Google Embedding-001

**向量数据库**: ChromaDB

**框架**: LangChain + Gradio
""")

        # 事件处理函数
        def process_document_with_model(file_path, selected_model):
            """处理文档上传并指定模型"""
            try:
                if not file_path:
                    return "❌ 请先选择文件", "### 暂无已上传文件"

                if not selected_model:
                    return "❌ 请先选择模型", "### 暂无已上传文件"

                logger.info(f"开始处理文档: {file_path}, 模型: {selected_model}")

                # 更新当前模型
                if hasattr(model_service, 'switch_model'):
                    model_service.switch_model(selected_model)

                # 使用正确的方法名处理PDF
                result_message = document_service.process_pdf(file_path)

                # 获取更新后的文件列表
                updated_files_display = get_uploaded_files_display()

                return result_message, updated_files_display

            except Exception as e:
                logger.error(f"文档处理失败: {e}")
                return f"❌ 处理失败: {str(e)}", "### 暂无已上传文件"

        def get_uploaded_files_display():
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
                logger.error(f"获取文件列表失败: {e}")
                return f"### ❌ 获取文件列表失败: {str(e)}"

        def chat_with_documents(message, history):
            """与文档对话"""
            try:
                if not message.strip():
                    return history, ""

                logger.info(f"处理用户问题: {message}")

                # 使用正确的方法名 chat_with_pdf
                response, updated_history = chat_service.chat_with_pdf(message, history or [])

                return updated_history, ""

            except Exception as e:
                logger.error(f"对话处理失败: {e}")
                error_response = f"抱歉，处理您的问题时发生错误: {str(e)}"
                history = history or []
                history.append([message, error_response])
                return history, ""

        def get_system_status():
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

        def get_model_info():
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

        def clear_chat():
            """清空对话"""
            try:
                chat_service.clear_conversation_history()
                return []
            except Exception as e:
                logger.error(f"清空对话失败: {e}")
                return []

        def init_model_dropdown():
            """初始化模型下拉框的默认值"""
            try:
                current_model = config_service.get_value("chat_model")
                return current_model
            except Exception as e:
                logger.error(f"获取默认模型失败: {e}")
                return None

        # 绑定事件
        # 上传按钮事件（处理文档时考虑选择的模型，并更新文件列表）
        upload_file.upload(
            fn=process_document_with_model,
            inputs=[upload_file, model_dropdown],
            outputs=[upload_status, uploaded_files_display]
        )

        # 发送消息事件
        send_btn.click(
            fn=chat_with_documents,
            inputs=[msg, chatbot],
            outputs=[chatbot, msg]
        )

        # 回车发送
        msg.submit(
            fn=chat_with_documents,
            inputs=[msg, chatbot],
            outputs=[chatbot, msg]
        )

        # 清空对话
        clear_btn.click(
            fn=clear_chat,
            outputs=[chatbot]
        )

        # 刷新状态
        refresh_btn.click(
            fn=lambda: (get_system_status(), get_model_info()),
            outputs=[system_status, model_info]
        )

        # 页面加载时初始化
        demo.load(
            fn=lambda: (get_system_status(), get_model_info()),
            outputs=[system_status, model_info]
        )

        # 页面加载时初始化文件列表
        demo.load(
            fn=get_uploaded_files_display,
            outputs=[uploaded_files_display]
        )

        # 页面加载时确保模型下拉框有正确的默认值
        demo.load(
            fn=init_model_dropdown,
            outputs=[model_dropdown]
        )

except Exception as e:
    error_msg = f"系统初始化失败: {e}"
    error_details = traceback.format_exc()

    print(f"❌ {error_msg}")
    print(f"错误详情: {error_details}")

    # 创建错误界面
    with gr.Blocks(title="Web RAG 系统 - 系统错误") as demo:
        gr.Markdown("# ❌ 系统错误")
        gr.Markdown(f"**错误信息**: {str(e)}")
        gr.Markdown("**建议**: 检查依赖配置和环境设置")


if __name__ == "__main__":
    try:
        is_spaces = os.getenv("SPACE_ID") is not None

        if is_spaces:
            demo.launch(share=True)
        else:
            demo.launch(
                server_name="127.0.0.1",
                server_port=7860,
                share=False,
                show_error=True,
                inbrowser=False,
                debug=True
            )

    except Exception as e:
        print(f"❌ 启动失败: {e}")
        print(f"错误详情: {traceback.format_exc()}")
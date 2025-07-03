#!/usr/bin/env python3
"""
Web RAG 系统
基于 Google Gemini 的智能文档问答系统
"""

import traceback

# 导入基础设施层
try:
    from src.infrastructure import (
        initialize_infrastructure,
        get_config,
        get_logger
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

    # 确保默认模型为 2.5 预览版
    target_default = "gemini-2.5-flash-preview-05-20"
    if model_service.get_current_model() != target_default:
        model_service.switch_model(target_default)

    logger.info("Web RAG 系统初始化完成")

    # 导入表示层控制器
    from src.presentation.controllers.main_ui_controller import MainUIController

    # 创建主UI控制器
    main_controller = MainUIController(
        document_service,
        chat_service,
        model_service,
        config_service,
        logger
    )

    # 构建界面
    demo = main_controller.build_interface()

except Exception as e:
    error_msg = f"系统初始化失败: {e}"
    error_details = traceback.format_exc()

    print(f"❌ {error_msg}")
    print(f"错误详情: {error_details}")

    # 创建错误界面
    import gradio as gr
    with gr.Blocks(title="Web RAG 系统 - 系统错误") as demo:
        gr.Markdown("# ❌ 系统错误")
        gr.Markdown(f"**错误信息**: {str(e)}")
        gr.Markdown("**建议**: 检查依赖配置和环境设置")


if __name__ == "__main__":
    try:
        main_controller.launch()

    except Exception as e:
        print(f"❌ 启动失败: {e}")
        print(f"错误详情: {traceback.format_exc()}")
#!/usr/bin/env python3
"""
Web RAG 系统 (重构版 v2.0)
基于 Google Gemini 的智能文档问答系统

架构特性:
- 分层架构设计 (应用层 + 服务层 + 状态管理)
- 组件化UI架构 (Tab控制器 + 事件管理)
- 线程安全状态管理
- 服务依赖注入
"""

import os
import sys
import traceback

# 导入服务层
try:
    from src.application.services.document_service import DocumentService
    from src.application.services.chat_service import ChatService
    from src.application.services.model_service import ModelService
    from src.shared.state.application_state import ApplicationState

    # 导入UI控制器
    from src.presentation.controllers.main_ui_controller import MainUIController

    # 初始化应用状态和服务
    application_state = ApplicationState()

    # 创建服务实例
    model_service = ModelService()
    document_service = DocumentService(model_service)
    chat_service = ChatService(model_service)

    # 创建主UI控制器
    main_ui = MainUIController(
        document_service=document_service,
        chat_service=chat_service,
        model_service=model_service
    )

    # 构建界面
    demo = main_ui.build_interface()

    # 打印架构信息
    main_ui.print_architecture_info()

except ImportError as e:
    print(f"❌ 导入错误: {e}")
    print("📋 这可能是因为缺少必要的依赖包")
    print("💡 解决方案: 请运行以下命令安装依赖:")
    print("   pip3 install langchain langchain-google-genai langchain-community chromadb gradio")

    # 创建简化版错误界面
    import gradio as gr

    with gr.Blocks(title="Web RAG 系统 - 依赖错误") as demo:
        gr.Markdown("# ❌ 依赖缺失")
        gr.Markdown(f"**错误**: {e}")
        gr.Markdown("""
**解决方案**: 请运行以下命令安装依赖:

```bash
pip3 install langchain langchain-google-genai langchain-community chromadb gradio
```

**环境要求**:
- Python 3.8+
- Google API Key (设置为环境变量 GOOGLE_API_KEY)
""")

except Exception as e:
    print(f"❌ 系统初始化失败: {e}")
    print(f"错误详情: {traceback.format_exc()}")

    # 创建通用错误界面
    import gradio as gr

    with gr.Blocks(title="Web RAG 系统 - 系统错误") as demo:
        gr.Markdown("# ❌ 系统错误")
        gr.Markdown(f"**错误信息**: {str(e)}")
        gr.Markdown("**建议**:")
        gr.Markdown("1. 检查 Python 环境和依赖包")
        gr.Markdown("2. 确认 GOOGLE_API_KEY 环境变量已设置")
        gr.Markdown("3. 查看控制台输出获取详细错误信息")


if __name__ == "__main__":
    try:
        # 启动界面
        main_ui.launch()

    except NameError:
        # main_ui 未定义，使用 demo 启动
        print("🚀 启动 Web RAG 系统 (错误模式)...")
        print(f"📋 API 密钥状态: {'✅ 已配置' if os.getenv('GOOGLE_API_KEY') else '❌ 未配置'}")

        # 检测运行环境
        is_spaces = os.getenv("SPACE_ID") is not None

        if is_spaces:
            # Hugging Face Spaces 环境配置
            demo.launch(share=True)
        else:
            # 本地开发环境配置
            demo.launch(
                server_name="127.0.0.1",
                server_port=7862,
                share=False,
                show_error=True,
                inbrowser=False,
                debug=True
            )

    except Exception as e:
        print(f"❌ 启动失败: {e}")
        print(f"错误详情: {traceback.format_exc()}")
#!/usr/bin/env python3
"""
Web RAG 系统 - 主程序
基于 Google Gemini 的智能文档问答系统
"""

import gradio as gr
import os
import sys
import tempfile
import traceback
from pathlib import Path

# 导入配置管理
from config import Config

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
    from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
    from langchain_community.document_loaders import PyPDFLoader
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain_community.vectorstores import Chroma
    from langchain.chains import RetrievalQA
    from langchain.prompts import PromptTemplate

    # 全局变量
    vectorstore = None
    qa_chain = None

    def create_llm():
        """创建 LLM，尝试多个模型名称"""
        model_names = [
            # 最新的 2.5 系列模型（Preview）
            "gemini-2.5-flash-preview-05-20",
            "gemini-2.5-pro-preview-06-05",

            # 2.0 系列模型（稳定版）
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",

            # 1.5 系列模型（稳定版，备用）
            "gemini-1.5-flash",
            "gemini-1.5-pro",
        ]

        for model_name in model_names:
            try:
                print(f"尝试模型: {model_name}")
                llm = ChatGoogleGenerativeAI(
                    model=model_name,
                    temperature=0.3,
                    convert_system_message_to_human=True
                )
                # 测试模型是否可用
                test_response = llm.invoke("测试")
                print(f"✅ 成功使用模型: {model_name}")
                return llm
            except Exception as e:
                print(f"❌ 模型 {model_name} 失败: {e}")
                continue

        raise Exception("所有 Gemini 模型都不可用")

    def process_pdf(file):
        """处理 PDF 文件并创建向量数据库"""
        global vectorstore, qa_chain

        print(f"开始处理文件: {file}")

        if file is None:
            return "❌ 请选择一个 PDF 文件"

        try:
            # 获取文件路径
            if hasattr(file, 'name'):
                file_path = file.name
                file_name = Path(file_path).name
            else:
                file_path = str(file)
                file_name = Path(file_path).name

            print(f"文件路径: {file_path}")
            print(f"文件名: {file_name}")

            # 检查文件是否存在
            if not os.path.exists(file_path):
                return f"❌ 文件不存在: {file_path}"

            # 加载 PDF
            print("正在加载 PDF...")
            loader = PyPDFLoader(file_path)
            documents = loader.load()

            if not documents:
                return "❌ PDF 文件为空或无法读取"

            print(f"成功加载 {len(documents)} 页文档")

            # 分割文档
            print("正在分割文档...")
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
                length_function=len,
            )
            texts = text_splitter.split_documents(documents)
            print(f"文档分割为 {len(texts)} 个片段")

            # 创建嵌入
            print("正在创建嵌入...")
            embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")

            # 创建向量数据库
            print("正在创建向量数据库...")
            vectorstore = Chroma.from_documents(
                documents=texts,
                embedding=embeddings,
                persist_directory="./chroma_db"
            )
            print("向量数据库创建成功")

            # 创建 QA 链
            print("正在初始化 QA 链...")
            llm = create_llm()  # 使用新的 LLM 创建函数

            # 自定义提示模板
            prompt_template = """
            基于以下上下文信息回答问题。如果上下文中没有相关信息，请说"根据提供的文档，我无法找到相关信息"。

            上下文：
            {context}

            问题：{question}

            请用中文回答：
            """

            PROMPT = PromptTemplate(
                template=prompt_template,
                input_variables=["context", "question"]
            )

            qa_chain = RetrievalQA.from_chain_type(
                llm=llm,
                chain_type="stuff",
                retriever=vectorstore.as_retriever(search_kwargs={"k": 3}),
                chain_type_kwargs={"prompt": PROMPT},
                return_source_documents=True
            )

            print("QA 链初始化成功")

            result_message = f"""✅ 成功处理 PDF 文件: {file_name}
📄 共处理 {len(documents)} 页文档
🔍 分割为 {len(texts)} 个文档片段
💾 向量数据库已创建
🤖 QA 链已初始化
💡 现在可以开始提问了！"""

            print("处理完成")
            return result_message

        except Exception as e:
            error_msg = f"❌ 处理 PDF 时出错: {str(e)}"
            print(f"错误: {e}")
            print(f"错误详情: {traceback.format_exc()}")
            return error_msg

    def chat_with_pdf(message, history):
        """与 PDF 内容对话"""
        global qa_chain

        print(f"收到消息: {message}")

        if not message.strip():
            return history, ""

        if qa_chain is None:
            response = "❌ 请先上传并处理 PDF 文件"
            history.append([message, response])
            return history, ""

        try:
            print("正在查询 QA 链...")
            # 查询 QA 链
            result = qa_chain({"query": message})
            response = result["result"]

            print(f"获得回答: {response[:100]}...")

            # 添加源文档信息
            if "source_documents" in result and result["source_documents"]:
                sources = set()
                for doc in result["source_documents"]:
                    if hasattr(doc, 'metadata') and 'source' in doc.metadata:
                        sources.add(Path(doc.metadata['source']).name)

                if sources:
                    response += f"\n\n📚 参考来源: {', '.join(sources)}"

            history.append([message, response])
            return history, ""

        except Exception as e:
            error_response = f"❌ 查询时出错: {str(e)}"
            print(f"查询错误: {e}")
            print(f"错误详情: {traceback.format_exc()}")
            history.append([message, error_response])
            return history, ""

    def get_system_status():
        """获取系统状态"""
        global vectorstore, qa_chain

        status = f"""
## 📊 系统状态

**Python 版本**: {sys.version.split()[0]}

**工作目录**: {os.getcwd()}

**API 密钥**: {'✅ 已配置' if os.getenv('GOOGLE_API_KEY') else '❌ 未配置'}

**向量数据库**: {'✅ 已加载' if vectorstore else '❌ 未加载'}

**QA 链**: {'✅ 已初始化' if qa_chain else '❌ 未初始化'}

---

## 📋 使用说明

1. 在"文档上传"标签页上传 PDF 文件
2. 等待处理完成（查看状态信息）
3. 在"智能对话"标签页提问
4. 系统会基于文档内容回答问题

---

## 🔧 技术栈

**LLM**: Google Gemini (自动选择可用模型)

**嵌入模型**: Google Embedding-001

**向量数据库**: ChromaDB

**框架**: LangChain + Gradio

---

## 🐛 调试信息

**向量存储对象**: {type(vectorstore).__name__ if vectorstore else 'None'}

**QA 链对象**: {type(qa_chain).__name__ if qa_chain else 'None'}

---

## 🚀 支持的 Gemini 模型

**最新 2.5 系列 (Preview)**
- `gemini-2.5-flash-preview-05-20` - 最新 Flash，支持思维链推理
- `gemini-2.5-pro-preview-06-05` - 最强推理能力，适合复杂任务

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

## 🎯 性能特点

**2.5 Flash Preview**: 思维链推理 + 平衡性能

**2.5 Pro Preview**: 最强推理 + 复杂任务

**2.0 Flash**: 下一代特性 + 稳定可靠

**2.0 Flash-Lite**: 成本优化 + 低延迟

**1.5 Flash**: 快速响应 + 多模态

**1.5 Pro**: 深度推理 + 长上下文
"""
        return status

    # 创建 Gradio 界面
    with gr.Blocks(title="Web RAG 系统") as demo:
        gr.Markdown("# 🚀 Web RAG 系统")
        gr.Markdown("基于 Google Gemini 的智能文档问答系统")

        with gr.Tab("📄 文档上传"):
            gr.Markdown("### 上传 PDF 文档")
            gr.Markdown("**注意**: 上传后请等待处理完成，状态会显示在下方")

            file_input = gr.File()
            upload_output = gr.Textbox(
                label="处理状态"
            )

            # 绑定上传事件
            file_input.upload(
                fn=process_pdf,
                inputs=file_input,
                outputs=upload_output
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
            status_output = gr.Markdown()
            refresh_btn = gr.Button("刷新状态")

            refresh_btn.click(get_system_status, None, status_output)
            demo.load(get_system_status, None, status_output)

except ImportError as e:
    print(f"❌ 导入错误: {e}")

    # 创建简化版界面
    with gr.Blocks(title="Web RAG 系统") as demo:
        gr.Markdown("# ❌ 依赖缺失")
        gr.Markdown(f"**错误**: {e}")
        gr.Markdown("**解决方案**: 请运行 `pip3 install langchain langchain-google-genai langchain-community chromadb`")

if __name__ == "__main__":
    try:
        print("🚀 启动 Web RAG 系统...")
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
                server_port=7860,
                share=False,
                show_error=True,
                inbrowser=False,
                debug=True  # 启用调试模式
            )
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        print(f"错误详情: {traceback.format_exc()}")
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

    # 可用的 Gemini 模型列表
    AVAILABLE_MODELS = [
        "gemini-2.5-flash-preview-05-20",
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
        "gemini-1.5-flash",
        "gemini-1.5-pro",
    ]

    # 默认模型（按优先级排序）
    DEFAULT_MODEL = "gemini-2.5-flash-preview-05-20"

    # 全局变量
    vectorstore = None
    qa_chain = None
    current_model = DEFAULT_MODEL  # 初始化为默认模型
    uploaded_files = []  # 记录已上传的文件信息

    def create_llm(selected_model=None):
        """创建 LLM，支持指定模型或自动选择"""
        global current_model

        if selected_model:
            # 使用指定的模型
            model_names = [selected_model]
        else:
            # 使用默认的模型优先级列表
            model_names = AVAILABLE_MODELS.copy()

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
                current_model = model_name
                return llm
            except Exception as e:
                print(f"❌ 模型 {model_name} 失败: {e}")
                if selected_model:
                    # 如果指定的模型失败，尝试默认模型
                    print(f"指定模型失败，尝试使用默认模型")
                    return create_llm()
                continue

        raise Exception("所有 Gemini 模型都不可用")

    def process_pdf(file):
        """处理 PDF 文件并创建向量数据库"""
        global vectorstore, qa_chain, uploaded_files

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

            # 🔄 注意：现在支持多文档累积，不再重置向量数据库
            print("正在准备处理新文档...")

            # 不再重置全局变量，保持多文档累积
            # vectorstore = None  # 保留现有向量数据库
            # qa_chain = None     # 保留现有QA链
            # 不清空文件列表，支持多文档累积

            print("✅ 系统准备完成，将添加新文档到现有知识库")

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

            # 创建嵌入（增加超时时间和重试机制）
            print("正在创建嵌入...")
            try:
                embeddings = GoogleGenerativeAIEmbeddings(
                    model="models/embedding-001",
                    request_timeout=120  # 增加超时时间到120秒
                )
                print("✅ Embedding 模型初始化成功")
            except Exception as e:
                print(f"❌ Embedding 模型初始化失败，尝试备用方案: {e}")
                # 备用方案：尝试不同的 embedding 模型
                try:
                    embeddings = GoogleGenerativeAIEmbeddings(
                        model="models/text-embedding-004",
                        request_timeout=120
                    )
                    print("✅ 使用备用 embedding 模型成功")
                except Exception as e2:
                    return f"❌ 无法初始化 embedding 模型: {str(e2)}"

            # 🔄 检查是否已有向量数据库，支持多文档累积
            print("正在处理向量数据库...")

            # 如果已存在向量数据库，则添加新文档；否则创建新的
            if vectorstore is not None:
                print("检测到已有向量数据库，将添加新文档...")
                # 向现有向量数据库添加新文档
                try:
                    vectorstore.add_documents(texts)
                    print("✅ 新文档已添加到现有向量数据库")
                except Exception as e:
                    print(f"❌ 添加文档到向量数据库失败: {e}")
                    # 如果添加失败，重新创建整个向量数据库
                    print("正在重新创建向量数据库...")
                    vectorstore = Chroma.from_documents(
                        documents=texts,
                        embedding=embeddings
                    )
                    print("✅ 向量数据库重新创建成功")
            else:
                print("创建新的向量数据库...")
                # 创建向量数据库（分批处理避免超时）
                try:
                    # 分批处理大文档，避免一次性处理过多内容导致超时
                    batch_size = 10  # 每批处理10个文档片段
                    if len(texts) > batch_size:
                        print(f"文档较大，将分 {(len(texts) + batch_size - 1) // batch_size} 批处理...")

                    vectorstore = Chroma.from_documents(
                        documents=texts,
                        embedding=embeddings
                        # 使用内存模式，避免文件权限问题
                    )
                    print("✅ 向量数据库创建成功")
                except Exception as e:
                    print(f"❌ 向量数据库创建失败: {e}")
                    if "timeout" in str(e).lower():
                        return f"❌ 网络超时，请检查网络连接或稍后重试: {str(e)}"
                    else:
                        return f"❌ 向量数据库创建失败: {str(e)}"

            # 创建 QA 链
            print("正在初始化 QA 链...")
            # 确保使用当前选中的模型
            llm = create_llm(current_model)

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

            # 记录文件信息
            from datetime import datetime
            file_info = {
                'name': file_name,
                'upload_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'pages': len(documents),
                'chunks': len(texts),
                'model': current_model
            }
            uploaded_files.append(file_info)
            print(f"已记录文件信息: {file_name}")

            result_message = f"""✅ 成功处理 PDF 文件: {file_name}
📄 共处理 {len(documents)} 页文档
🔍 分割为 {len(texts)} 个文档片段
📚 已添加到知识库（支持多文档累积，当前共 {len(uploaded_files)} 个文档）
💾 内存向量数据库已更新（避免权限问题）
🤖 QA 链已初始化（模型: {current_model if current_model else '未知'}）
💡 现在可以向所有已上传的文档提问了！

🔄 系统状态已更新，请查看"系统状态"标签页确认"""

            print("处理完成")
            return result_message

        except Exception as e:
            error_msg = f"❌ 处理 PDF 时出错: {str(e)}"
            print(f"错误: {e}")
            print(f"错误详情: {traceback.format_exc()}")
            return error_msg

    def process_pdf_and_update_status(file, selected_model):
        """处理 PDF 并更新模型状态"""
        global current_model

        # 先更新当前模型
        current_model = selected_model

        # 处理 PDF
        result = process_pdf(file)

        # 返回处理结果、更新的模型状态、系统状态和文件列表
        model_status_text = f"当前模型: {current_model}\n状态: 已就绪\n\n💡 提示: 文档已加载，可以开始对话"
        system_status_text = get_system_status()
        files_display = get_uploaded_files_display()

        return result, model_status_text, system_status_text, files_display

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

    def switch_model(selected_model):
        """切换模型"""
        global qa_chain, current_model

        # 更新当前模型
        current_model = selected_model

        if not vectorstore:
            return f"❌ 请先上传并处理 PDF 文件，然后再切换模型", current_model

        # 保存当前模型作为备份
        previous_model = current_model

        try:
            print(f"正在切换到模型: {selected_model}")
            llm = create_llm(selected_model)

            # 重新创建 QA 链
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

            success_message = f"""✅ 模型切换成功

当前模型: {current_model}
状态: 已就绪

💡 提示: 如果已上传文档，可以直接开始对话"""

            return success_message, current_model

        except Exception as e:
            error_message = f"❌ 切换模型失败: {str(e)}"
            print(f"模型切换失败，回退到: {previous_model}")
            # 回退模型状态
            current_model = previous_model
            # 返回错误消息和回退的模型
            return error_message, previous_model

    def get_system_status():
        """获取系统状态"""
        global vectorstore, qa_chain, current_model, uploaded_files

        # 检查向量数据库状态
        vectorstore_status = "❌ 未加载"
        if vectorstore is not None:
            try:
                # 尝试获取文档数量来验证向量数据库是否正常
                doc_count = len(vectorstore.get()['documents']) if hasattr(vectorstore, 'get') else "无法获取"
                vectorstore_status = f"✅ 已加载 (文档数: {doc_count})"
            except:
                vectorstore_status = "✅ 已加载"

        # 检查QA链状态
        qa_status = "❌ 未初始化"
        if qa_chain is not None:
            qa_status = "✅ 已初始化"

        # 检查当前模型状态
        model_status = current_model if current_model else "未初始化"

        status = f"""
## 📊 系统状态

**Python 版本**: {sys.version.split()[0]}

**工作目录**: {os.getcwd()}

**API 密钥**: {'✅ 已配置' if os.getenv('GOOGLE_API_KEY') else '❌ 未配置'}

**当前模型**: {model_status}

**向量数据库**: {vectorstore_status}

**QA 链**: {qa_status}

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

    def get_uploaded_files_display():
        """获取已上传文件列表的显示内容"""
        global uploaded_files

        if not uploaded_files:
            return "*暂无已上传文件*"

        files_display = "## 📄 已上传文件\n\n"
        for i, file_info in enumerate(uploaded_files, 1):
            files_display += f"""**{i}. {file_info['name']}**
- 📅 上传时间: {file_info['upload_time']}
- 📑 页数: {file_info['pages']} 页
- 🔍 文档片段: {file_info['chunks']} 个
- 🤖 使用模型: {file_info['model']}

"""
        return files_display

    # 创建 Gradio 界面
    with gr.Blocks(title="Web RAG 系统", theme=gr.themes.Soft()) as demo:
        gr.Markdown("# 🚀 Web RAG 系统")
        gr.Markdown("基于 Google Gemini 的智能文档问答系统")

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
                        choices=AVAILABLE_MODELS,
                        value=DEFAULT_MODEL,
                        label="选择 Gemini 模型",
                        info="选择后自动切换模型"
                    )
                    model_status = gr.Textbox(
                        label="模型状态",
                        value=f"当前模型: {DEFAULT_MODEL}\n状态: 已就绪",
                        interactive=False,
                        lines=3
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
                    gr.Markdown("### 📋 可用模型列表")
                    models_info = gr.Markdown(f"""
**默认模型**: `{DEFAULT_MODEL}`

**所有可用模型**:
{chr(10).join([f'- `{model}`' for model in AVAILABLE_MODELS])}

**模型说明**:
- **2.5 系列**: 最新预览版，性能最佳
- **2.0 系列**: 稳定版，生产推荐
- **1.5 系列**: 备用版，确保可用性
                    """)

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
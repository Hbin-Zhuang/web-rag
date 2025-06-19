"""
聊天服务
封装聊天问答、QA链管理等核心业务逻辑
"""

from typing import List, Tuple, Optional
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

from memory import ConversationManager
from src.shared.state.application_state import app_state


class ChatService:
    """聊天服务"""

    def __init__(self):
        self.conversation_manager = ConversationManager()

    def chat_with_pdf(self, message: str, history: List[List[str]]) -> Tuple[str, List[List[str]]]:
        """
        与PDF文档聊天

        Args:
            message: 用户输入的消息
            history: 对话历史

        Returns:
            (回复消息, 更新后的历史)
        """
        try:
            if not message.strip():
                return "请输入有效的问题。", history

            # 检查是否有可用的问答链
            qa_chain = self._get_or_create_qa_chain()
            if not qa_chain:
                return "❌ 系统尚未就绪，请先上传PDF文档。", history

            print(f"用户问题: {message}")

            # 执行问答
            try:
                result = qa_chain({"query": message})
                answer = result["result"]
                print(f"AI回答: {answer}")
            except Exception as e:
                print(f"问答执行失败: {e}")
                answer = f"❌ 处理问题时发生错误: {str(e)}"

            # 更新对话历史
            history.append([message, answer])

            return answer, history

        except Exception as e:
            error_msg = f"❌ 聊天服务异常: {str(e)}"
            print(error_msg)
            history.append([message, error_msg])
            return error_msg, history

    def _get_or_create_qa_chain(self):
        """获取或创建问答链"""
        # 检查是否已有问答链
        if app_state.qa_chain is not None:
            return app_state.qa_chain

        # 检查是否有向量存储
        if app_state.vectorstore is None:
            print("向量存储未初始化")
            return None

        try:
            # 创建LLM
            llm = self._create_llm()
            if not llm:
                return None

            # 创建问答链
            app_state.qa_chain = RetrievalQA.from_chain_type(
                llm=llm,
                chain_type="stuff",
                retriever=app_state.vectorstore.as_retriever(search_kwargs={"k": 4}),
                chain_type_kwargs={
                    "prompt": self._create_prompt_template()
                },
                return_source_documents=True
            )

            print("✅ 问答链创建成功")
            return app_state.qa_chain

        except Exception as e:
            print(f"❌ 问答链创建失败: {e}")
            return None

    def _create_llm(self):
        """创建语言模型"""
        try:
            current_model = app_state.current_model
            print(f"创建LLM，使用模型: {current_model}")

            llm = ChatGoogleGenerativeAI(
                model=current_model,
                temperature=0.3,
                convert_system_message_to_human=True
            )

            # 测试模型是否可用
            test_response = llm.invoke("测试")
            print(f"✅ LLM创建成功: {current_model}")
            return llm

        except Exception as e:
            print(f"❌ LLM创建失败: {e}")
            return None

    def _create_prompt_template(self) -> PromptTemplate:
        """创建提示模板"""
        template = """你是一个专业的AI助手，专门基于提供的文档内容来回答用户问题。

请遵循以下规则：
1. 仅基于提供的上下文内容回答问题
2. 如果上下文中没有相关信息，请明确说明"根据提供的文档内容，我无法找到相关信息"
3. 回答要准确、简洁且有帮助
4. 如果可能，请引用具体的文档内容
5. 使用中文回答

上下文文档：
{context}

用户问题：{question}

请基于上述文档内容回答用户问题："""

        return PromptTemplate(
            template=template,
            input_variables=["context", "question"]
        )

    def reset_qa_chain(self):
        """重置问答链"""
        try:
            app_state.qa_chain = None
            print("✅ 问答链已重置")
        except Exception as e:
            print(f"❌ 重置问答链失败: {e}")

    def is_ready(self) -> bool:
        """检查聊天服务是否就绪"""
        return (app_state.vectorstore is not None and
                app_state.qa_chain is not None)

    def get_conversation_history(self) -> List[dict]:
        """获取对话历史"""
        return self.conversation_manager.get_history()

    def clear_conversation_history(self):
        """清空对话历史"""
        self.conversation_manager.clear_history()
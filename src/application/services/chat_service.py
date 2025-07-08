"""
聊天服务
封装聊天问答、QA链管理等核心业务逻辑
"""

from typing import List, Tuple, Optional
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

from src.application.services.memory_service import MemoryService
from src.application.services.rerank_service import RerankService
from src.application.services.rerank_retriever import RerankRetriever
from src.shared.state.application_state import app_state
from src.infrastructure import get_logger, get_config
from src.infrastructure.utilities import get_utility_service


class ChatService:
    """聊天服务"""

    def __init__(self, model_service=None, memory_service=None, config_service=None, logger_service=None):
        """初始化聊天服务

        Args:
            model_service: 模型管理服务实例，用于依赖注入
            memory_service: 内存管理服务实例
            config_service: 配置服务实例
            logger_service: 日志服务实例
        """
        self.model_service = model_service
        self.config = config_service or get_config()
        self.logger = logger_service or get_logger()
        self.utility = get_utility_service()

        # 内存管理服务
        self.memory_service = memory_service or MemoryService(
            config_service=config_service,
            logger_service=logger_service
        )

        # 重排序服务
        self.rerank_service = RerankService(self.config)

        # 重排序配置
        self.use_rerank = self.config.get_value("use_rerank", True)

        self.logger.info("ChatService 初始化完成", extra={
            "memory_service_type": type(self.memory_service).__name__,
            "use_rerank": self.use_rerank
        })

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
                self.logger.warning("用户输入为空")
                return "请输入有效的问题。", history

            # 检查是否有可用的问答链
            qa_chain = self._get_or_create_qa_chain()
            if not qa_chain:
                error_msg = "❌ 系统尚未就绪，请先上传PDF文档。"
                self.logger.warning("QA链未就绪")
                return error_msg, history

            self.logger.info("开始处理用户问题", extra={
                "question_preview": self.utility.truncate_text(message, 100)
            })

            # 添加用户消息到内存
            self.memory_service.add_message_to_current_session("user", message)

            # 获取对话上下文以增强RAG查询
            conversation_context = self.memory_service.get_current_session_context(include_messages=3)

            # 构建增强的查询（包含上下文）
            enhanced_query = self._build_enhanced_query(message, conversation_context)

            # 执行问答
            try:
                result = qa_chain({"query": enhanced_query})
                answer = result["result"]

                # 处理参考来源
                source_documents = result.get("source_documents", [])
                if source_documents:
                    sources = []
                    for doc in source_documents[:3]:  # 最多显示3个来源
                        src = doc.metadata.get("source", "未知")
                        if "/" in src:
                            src = src.split("/")[-1]  # 只取文件名
                        sources.append(src)

                    # 去重并添加到答案末尾
                    unique_sources = list(dict.fromkeys(sources))
                    if unique_sources:
                        answer += f"\n\n📚 **参考来源**: {', '.join(unique_sources)}"

                # 添加AI回复到内存
                self.memory_service.add_message_to_current_session("assistant", answer)

                self.logger.info("问答处理成功", extra={
                    "answer_preview": self.utility.truncate_text(answer, 100),
                    "session_id": self.memory_service.current_session_id,
                    "source_count": len(source_documents)
                })

            except Exception as e:
                self.logger.error("问答执行失败", exception=e)
                answer = f"❌ 处理问题时发生错误: {str(e)}"

                # 记录错误到内存
                self.memory_service.add_message_to_current_session("assistant", answer, {
                    "error": True,
                    "error_type": type(e).__name__
                })

            # 更新对话历史
            history.append([message, answer])

            # 定期保存会话：按服务器端 MemoryService 的总消息计数判断
            try:
                total_msgs = self.memory_service.get_current_session_info().get("message_count", 0)
                # 一问一答计为 2 条消息；当对话轮次达到 5（即 10 条消息）时保存
                if total_msgs % 10 == 0 and total_msgs != 0:
                    self.logger.info("达到 5 轮对话，自动持久化会话", extra={
                        "total_messages": total_msgs,
                        "session_id": self.memory_service.current_session_id
                    })
                    self.memory_service.save_current_session()
            except Exception as e:
                self.logger.error("自动保存会话失败", exception=e)

            return answer, history

        except Exception as e:
            error_msg = f"❌ 聊天服务异常: {str(e)}"
            self.logger.error("聊天服务异常", exception=e)
            history.append([message, error_msg])
            return error_msg, history

    def _build_enhanced_query(self, message: str, context: str) -> str:
        """构建增强的查询，包含对话上下文"""
        if not context.strip():
            return message

        # 如果上下文过长，截取最相关的部分
        if len(context) > 500:
            context = self.utility.truncate_text(context, 500)

        enhanced_query = f"""
基于以下对话上下文回答问题：

对话上下文：
{context}

当前问题：{message}

请考虑对话上下文来提供更准确和相关的回答。
"""
        return enhanced_query

    def _get_or_create_qa_chain(self):
        """获取或创建问答链"""
        # 检查是否已有问答链
        if app_state.qa_chain is not None:
            return app_state.qa_chain

        # 检查是否有向量存储
        if app_state.vectorstore is None:
            self.logger.warning("向量存储未初始化")
            return None

        try:
            # 创建LLM
            llm = self._create_llm()
            if not llm:
                return None

            # 获取内存变量以集成到问答链中
            memory_variables = self.memory_service.get_memory_variables()

            # 创建检索器
            retriever = self._create_retriever()
            if not retriever:
                self.logger.error("检索器创建失败")
                return None

            # 创建问答链
            app_state.qa_chain = RetrievalQA.from_chain_type(
                llm=llm,
                chain_type="stuff",
                retriever=retriever,
                chain_type_kwargs={
                    "prompt": self._create_prompt_template()
                },
                return_source_documents=True
            )

            self.logger.info("问答链创建成功", extra={
                "use_rerank": self.use_rerank
            })
            return app_state.qa_chain

        except Exception as e:
            self.logger.error("问答链创建失败", exception=e)
            return None

    def _create_retriever(self):
        """创建检索器"""
        try:
            if self.use_rerank:
                # 创建基础检索器
                base_retriever = app_state.vectorstore.as_retriever(
                    search_kwargs={"k": int(self.config.get_value("rerank_initial_k", 8))}
                )

                # 创建重排序检索器
                rerank_retriever = RerankRetriever(
                    base_retriever=base_retriever,
                    rerank_service=self.rerank_service,
                    final_k=int(self.config.get_value("rerank_final_k", 4))
                )

                self.logger.info("重排序检索器创建成功")
                return rerank_retriever
            else:
                # 使用基础检索器
                basic_retriever = app_state.vectorstore.as_retriever(
                    search_kwargs={"k": self.config.get_value("similarity_top_k", 4)}
                )

                self.logger.info("基础检索器创建成功")
                return basic_retriever

        except Exception as e:
            self.logger.error("检索器创建失败", exception=e)
            return None

    def _create_llm(self):
        """创建语言模型"""
        try:
            current_model = app_state.current_model
            self.logger.info("创建LLM", extra={"model": current_model})

            llm = ChatGoogleGenerativeAI(
                model=current_model,
                temperature=0.3,
                convert_system_message_to_human=True
            )

            # 测试模型是否可用
            test_response = llm.invoke("测试")
            self.logger.info("LLM创建成功", extra={"model": current_model})
            return llm

        except Exception as e:
            self.logger.error("LLM创建失败", exception=e)
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
6. 考虑对话的连续性，如果问题涉及之前的讨论内容，请适当关联

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
            self.logger.info("问答链已重置")
        except Exception as e:
            self.logger.error("重置问答链失败", exception=e)

    def is_ready(self) -> bool:
        """检查聊天服务是否就绪"""
        return (app_state.vectorstore is not None and
                app_state.qa_chain is not None)

    def get_conversation_history(self) -> List[dict]:
        """获取对话历史"""
        try:
            chat_messages = self.memory_service.get_current_session_history()
            # 转换为兼容格式
            history = []
            for msg in chat_messages:
                role = "human" if msg.role == "user" else "ai"
                history.append({
                    "role": role,
                    "content": msg.content,
                    "timestamp": msg.timestamp,
                    "metadata": msg.metadata
                })
            return history
        except Exception as e:
            self.logger.error("获取对话历史失败", exception=e)
            return []

    def clear_conversation_history(self):
        """清空对话历史"""
        try:
            self.memory_service.clear_current_session()
            self.logger.info("对话历史已清空")
        except Exception as e:
            self.logger.error("清空对话历史失败", exception=e)

    def reset_conversation_session(self) -> str:
        """重置对话会话"""
        try:
            new_session_id = self.memory_service.reset_current_session()
            self.logger.info("对话会话已重置", extra={"new_session_id": new_session_id})
            return new_session_id
        except Exception as e:
            self.logger.error("重置对话会话失败", exception=e)
            return ""

    def save_current_conversation(self) -> bool:
        """保存当前对话"""
        try:
            return self.memory_service.save_current_session()
        except Exception as e:
            self.logger.error("保存当前对话失败", exception=e)
            return False

    def get_conversation_summary(self) -> str:
        """获取对话摘要"""
        try:
            session_info = self.memory_service.get_current_session_info()
            message_count = session_info.get("message_count", 0)

            if message_count == 0:
                return "暂无对话内容"

            user_messages = 0
            assistant_messages = 0

            history = self.get_conversation_history()
            for msg in history:
                if msg["role"] == "human":
                    user_messages += 1
                else:
                    assistant_messages += 1

            return f"本次对话包含 {message_count} 条消息（用户 {user_messages} 条，助手 {assistant_messages} 条）"

        except Exception as e:
            self.logger.error("获取对话摘要失败", exception=e)
            return "获取对话摘要失败"

    def get_service_status(self) -> dict:
        """获取聊天服务状态"""
        try:
            memory_status = self.memory_service.get_service_status()

            return {
                "service_name": "ChatService",
                "status": "active" if self.is_ready() else "not_ready",
                "qa_chain_ready": app_state.qa_chain is not None,
                "vectorstore_ready": app_state.vectorstore is not None,
                "current_model": app_state.current_model,
                "memory_service": memory_status
            }

        except Exception as e:
            self.logger.error("获取服务状态失败", exception=e)
            return {
                "service_name": "ChatService",
                "status": "error",
                "error": str(e)
            }
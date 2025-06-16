"""
语义检索和答案生成模块
负责检索相关文档并生成回答
"""

from typing import List, Dict, Any, Optional
from langchain.schema import Document
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from config import Config
from utils import logger
from indexer import DocumentIndexer
from memory import ConversationManager

class RAGRetriever:
    """RAG检索器"""

    def __init__(self, indexer: DocumentIndexer, memory_manager: ConversationManager):
        self.indexer = indexer
        self.memory_manager = memory_manager
        self.llm = None
        self.qa_chain = None
        self._initialize_llm()
        self._initialize_qa_chain()

    def _initialize_llm(self):
        """初始化大语言模型"""
        try:
            if not Config.validate_config():
                logger.error("配置验证失败，请检查GOOGLE_API_KEY")
                return

            self.llm = ChatGoogleGenerativeAI(
                model=Config.CHAT_MODEL,
                google_api_key=Config.GOOGLE_API_KEY,
                temperature=0.1,
                max_tokens=Config.MAX_TOKENS
            )
            logger.info(f"语言模型初始化成功: {Config.CHAT_MODEL}")

        except Exception as e:
            logger.error(f"语言模型初始化失败: {e}")
            self.llm = None

    def _initialize_qa_chain(self):
        """初始化问答链"""
        try:
            if not self.llm:
                logger.error("语言模型未初始化，无法创建问答链")
                return

            # 创建自定义提示模板
            prompt_template = self._create_prompt_template()

            # 获取向量存储
            vectorstore = self.indexer.get_vectorstore()
            if not vectorstore:
                logger.error("向量数据库不可用，无法创建问答链")
                return

            # 创建检索器
            retriever = vectorstore.as_retriever(
                search_kwargs={"k": Config.SIMILARITY_TOP_K}
            )

            # 创建问答链
            self.qa_chain = RetrievalQA.from_chain_type(
                llm=self.llm,
                chain_type="stuff",
                retriever=retriever,
                chain_type_kwargs={
                    "prompt": prompt_template,
                    "memory": self.memory_manager.memory
                },
                return_source_documents=True
            )

            logger.info("问答链初始化成功")

        except Exception as e:
            logger.error(f"问答链初始化失败: {e}")
            self.qa_chain = None

    def _create_prompt_template(self) -> PromptTemplate:
        """创建RAG提示模板"""
        template = """你是一个专业的AI助手，专门基于提供的文档内容来回答用户问题。

请遵循以下规则：
1. 仅基于提供的上下文内容回答问题
2. 如果上下文中没有相关信息，请明确说明"根据提供的文档内容，我无法找到相关信息"
3. 回答要准确、简洁且有帮助
4. 如果可能，请引用具体的文档内容
5. 使用中文回答

对话历史：
{chat_history}

上下文文档：
{context}

用户问题：{question}

请基于上述文档内容回答用户问题："""

        return PromptTemplate(
            template=template,
            input_variables=["context", "question", "chat_history"]
        )

    def retrieve_docs(self, query: str, k: int = None) -> List[Document]:
        """
        检索相关文档

        Args:
            query: 查询文本
            k: 返回的文档数量

        Returns:
            相关文档列表
        """
        try:
            if not query.strip():
                logger.warning("查询文本为空")
                return []

            # 使用索引器进行相似性搜索
            k = k or Config.SIMILARITY_TOP_K
            documents = self.indexer.search_similar_documents(query, k=k)

            logger.info(f"检索到 {len(documents)} 个相关文档")
            return documents

        except Exception as e:
            logger.error(f"文档检索失败: {e}")
            return []

    def generate_answer(self, query: str, include_sources: bool = True) -> Dict[str, Any]:
        """
        生成基于检索文档的回答

        Args:
            query: 用户查询
            include_sources: 是否包含源文档信息

        Returns:
            包含回答和元数据的字典
        """
        try:
            if not query.strip():
                return {
                    "answer": "请提供有效的问题。",
                    "sources": [],
                    "error": "空查询"
                }

            if not self.qa_chain:
                logger.error("问答链未初始化")
                return {
                    "answer": "系统初始化中，请稍后再试。",
                    "sources": [],
                    "error": "问答链未初始化"
                }

            # 获取对话上下文
            chat_context = self.memory_manager.get_recent_context()

            # 执行问答
            result = self.qa_chain({
                "query": query,
                "chat_history": chat_context
            })

            answer = result.get("result", "抱歉，我无法生成回答。")
            source_docs = result.get("source_documents", [])

            # 添加用户问题到记忆
            self.memory_manager.add_message("human", query)

            # 添加AI回答到记忆
            self.memory_manager.add_message("ai", answer, {
                "source_count": len(source_docs)
            })

            # 格式化源文档信息
            sources = []
            if include_sources and source_docs:
                sources = self._format_source_documents(source_docs)

            logger.info(f"问答完成: 查询='{query[:50]}...', 源文档数={len(source_docs)}")

            return {
                "answer": answer,
                "sources": sources,
                "source_count": len(source_docs),
                "query": query
            }

        except Exception as e:
            logger.error(f"生成回答失败: {e}")
            return {
                "answer": "抱歉，处理您的问题时出现错误，请稍后再试。",
                "sources": [],
                "error": str(e)
            }

    def _format_source_documents(self, documents: List[Document]) -> List[Dict[str, Any]]:
        """格式化源文档信息"""
        sources = []

        for i, doc in enumerate(documents):
            source_info = {
                "index": i + 1,
                "content": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content,
                "metadata": {
                    "source_file": doc.metadata.get("source_file", "未知"),
                    "page": doc.metadata.get("page", "未知"),
                    "chunk_index": doc.metadata.get("chunk_index", "未知")
                }
            }
            sources.append(source_info)

        return sources

    def ask_question(self, question: str) -> Dict[str, Any]:
        """
        简化的问答接口

        Args:
            question: 用户问题

        Returns:
            回答结果
        """
        return self.generate_answer(question, include_sources=True)

    def get_retriever_info(self) -> Dict[str, Any]:
        """获取检索器信息"""
        try:
            vectorstore = self.indexer.get_vectorstore()

            return {
                "llm_model": Config.CHAT_MODEL,
                "max_tokens": Config.MAX_TOKENS,
                "similarity_top_k": Config.SIMILARITY_TOP_K,
                "vectorstore_available": vectorstore is not None,
                "qa_chain_available": self.qa_chain is not None,
                "memory_manager_available": self.memory_manager is not None
            }

        except Exception as e:
            logger.error(f"获取检索器信息失败: {e}")
            return {"error": str(e)}

    def reset_qa_chain(self):
        """重置问答链（例如在更新向量数据库后）"""
        try:
            logger.info("重置问答链...")
            self._initialize_qa_chain()
        except Exception as e:
            logger.error(f"重置问答链失败: {e}")

    def batch_questions(self, questions: List[str]) -> List[Dict[str, Any]]:
        """
        批量处理问题

        Args:
            questions: 问题列表

        Returns:
            回答结果列表
        """
        results = []

        for i, question in enumerate(questions):
            logger.info(f"处理批量问题 {i+1}/{len(questions)}")
            result = self.generate_answer(question)
            results.append(result)

        return results
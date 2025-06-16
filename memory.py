"""
对话记忆和会话管理模块
负责维护对话历史和会话状态
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from langchain.memory import ConversationBufferWindowMemory
from langchain.schema import BaseMessage, HumanMessage, AIMessage
from config import Config
from utils import logger, format_timestamp

class ConversationManager:
    """对话管理器"""

    def __init__(self, max_history_length: int = None):
        self.max_history_length = max_history_length or Config.MAX_HISTORY_LENGTH
        self.memory = ConversationBufferWindowMemory(
            k=self.max_history_length,
            return_messages=True,
            memory_key="chat_history"
        )
        self.session_id = None
        self.session_start_time = None
        self._init_session()

    def _init_session(self):
        """初始化会话"""
        self.session_id = self._generate_session_id()
        self.session_start_time = datetime.now()
        logger.info(f"新会话已创建: {self.session_id}")

    def _generate_session_id(self) -> str:
        """生成会话ID"""
        return f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    def add_message(self, role: str, content: str, metadata: Dict[str, Any] = None) -> None:
        """
        添加消息到对话历史

        Args:
            role: 消息角色 ('human' 或 'ai')
            content: 消息内容
            metadata: 额外的元数据
        """
        try:
            if not content.strip():
                logger.warning("消息内容为空，跳过添加")
                return

            # 创建消息对象
            timestamp = datetime.now()
            message_metadata = {
                "timestamp": format_timestamp(timestamp),
                "session_id": self.session_id,
                **(metadata or {})
            }

            if role.lower() == 'human':
                message = HumanMessage(content=content)
            elif role.lower() == 'ai':
                message = AIMessage(content=content)
            else:
                logger.error(f"不支持的消息角色: {role}")
                return

            # 添加元数据到消息
            if hasattr(message, 'additional_kwargs'):
                message.additional_kwargs.update(message_metadata)

            # 添加到内存
            if role.lower() == 'human':
                self.memory.chat_memory.add_user_message(content)
            else:
                self.memory.chat_memory.add_ai_message(content)

            logger.debug(f"消息已添加: {role} - {content[:50]}...")

        except Exception as e:
            logger.error(f"添加消息失败: {e}")

    def get_history(self, limit: int = None) -> List[Dict[str, Any]]:
        """
        获取对话历史

        Args:
            limit: 限制返回的消息数量

        Returns:
            格式化的对话历史列表
        """
        try:
            # 获取内存中的消息
            messages = self.memory.chat_memory.messages

            # 应用限制
            if limit and limit > 0:
                messages = messages[-limit:]

            # 格式化消息
            formatted_history = []
            for msg in messages:
                formatted_msg = {
                    "role": "human" if isinstance(msg, HumanMessage) else "ai",
                    "content": msg.content,
                    "timestamp": getattr(msg, 'additional_kwargs', {}).get('timestamp', ''),
                    "session_id": self.session_id
                }
                formatted_history.append(formatted_msg)

            return formatted_history

        except Exception as e:
            logger.error(f"获取对话历史失败: {e}")
            return []

    def get_recent_context(self, include_messages: int = 5) -> str:
        """
        获取最近的对话上下文（用于RAG查询）

        Args:
            include_messages: 包含的最近消息数量

        Returns:
            格式化的上下文字符串
        """
        try:
            recent_history = self.get_history(limit=include_messages)

            if not recent_history:
                return ""

            context_parts = []
            for msg in recent_history:
                role = "用户" if msg["role"] == "human" else "助手"
                context_parts.append(f"{role}: {msg['content']}")

            return "\n".join(context_parts)

        except Exception as e:
            logger.error(f"获取对话上下文失败: {e}")
            return ""

    def get_memory_variables(self) -> Dict[str, Any]:
        """获取内存变量（用于LangChain链）"""
        try:
            return self.memory.load_memory_variables({})
        except Exception as e:
            logger.error(f"获取内存变量失败: {e}")
            return {}

    def clear_history(self) -> None:
        """清空对话历史"""
        try:
            self.memory.clear()
            logger.info(f"对话历史已清空: {self.session_id}")
        except Exception as e:
            logger.error(f"清空对话历史失败: {e}")

    def reset_session(self) -> str:
        """重置会话"""
        try:
            # 清空当前对话
            self.clear_history()

            # 创建新会话
            self._init_session()

            logger.info(f"会话已重置: {self.session_id}")
            return self.session_id

        except Exception as e:
            logger.error(f"重置会话失败: {e}")
            return self.session_id

    def get_session_info(self) -> Dict[str, Any]:
        """获取会话信息"""
        try:
            history = self.get_history()

            session_duration = None
            if self.session_start_time:
                duration_seconds = (datetime.now() - self.session_start_time).total_seconds()
                session_duration = round(duration_seconds, 1)

            return {
                "session_id": self.session_id,
                "start_time": format_timestamp(self.session_start_time) if self.session_start_time else None,
                "duration_seconds": session_duration,
                "message_count": len(history),
                "max_history_length": self.max_history_length,
                "memory_type": "ConversationBufferWindowMemory"
            }

        except Exception as e:
            logger.error(f"获取会话信息失败: {e}")
            return {
                "session_id": self.session_id,
                "error": str(e)
            }

    def export_history(self) -> List[Dict[str, Any]]:
        """导出完整对话历史"""
        try:
            history = self.get_history()
            session_info = self.get_session_info()

            return {
                "session_info": session_info,
                "messages": history,
                "export_time": format_timestamp()
            }

        except Exception as e:
            logger.error(f"导出对话历史失败: {e}")
            return {
                "session_info": {"session_id": self.session_id},
                "messages": [],
                "export_time": format_timestamp(),
                "error": str(e)
            }

    def get_conversation_summary(self) -> str:
        """获取对话摘要"""
        try:
            history = self.get_history()

            if not history:
                return "暂无对话内容"

            total_messages = len(history)
            human_messages = len([msg for msg in history if msg["role"] == "human"])
            ai_messages = len([msg for msg in history if msg["role"] == "ai"])

            return f"本次对话包含 {total_messages} 条消息（用户 {human_messages} 条，助手 {ai_messages} 条）"

        except Exception as e:
            logger.error(f"获取对话摘要失败: {e}")
            return "获取对话摘要失败"
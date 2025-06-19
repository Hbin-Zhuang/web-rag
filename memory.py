"""
对话记忆和会话管理模块
负责维护对话历史和会话状态
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from langchain.memory import ConversationBufferWindowMemory
from langchain.schema import BaseMessage, HumanMessage, AIMessage

# 使用新的基础设施服务
from src.infrastructure.config.config_migration_adapter import get_legacy_config
from src.infrastructure.utilities import get_utility_service
from src.infrastructure import get_logger

class ConversationManager:
    """对话管理器"""

    def __init__(self, max_history_length: int = None, config_service=None, logger_service=None, utility_service=None):
        """初始化对话管理器

        Args:
            max_history_length: 最大历史长度
            config_service: 配置服务实例
            logger_service: 日志服务实例
            utility_service: 工具服务实例
        """
        # 获取服务实例 (支持依赖注入)
        self.config = config_service or get_legacy_config()
        self.logger = logger_service or get_logger()
        self.utility = utility_service or get_utility_service()

        self.max_history_length = max_history_length or self.config.MAX_HISTORY_LENGTH
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
        self.logger.info("新会话已创建", extra={
            "session_id": self.session_id,
            "start_time": self.utility.format_timestamp(self.session_start_time)
        })

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
                self.logger.warning("消息内容为空，跳过添加")
                return

            # 创建消息对象
            timestamp = datetime.now()
            message_metadata = {
                "timestamp": self.utility.format_timestamp(timestamp),
                "session_id": self.session_id,
                **(metadata or {})
            }

            if role.lower() == 'human':
                message = HumanMessage(content=content)
            elif role.lower() == 'ai':
                message = AIMessage(content=content)
            else:
                self.logger.error(f"不支持的消息角色: {role}")
                return

            # 添加元数据到消息
            if hasattr(message, 'additional_kwargs'):
                message.additional_kwargs.update(message_metadata)

            # 添加到内存
            if role.lower() == 'human':
                self.memory.chat_memory.add_user_message(content)
            else:
                self.memory.chat_memory.add_ai_message(content)

            self.logger.debug("消息已添加", extra={
                "role": role,
                "content_preview": self.utility.truncate_text(content, 50),
                "session_id": self.session_id
            })

        except Exception as e:
            self.logger.error("添加消息失败", exception=e, extra={
                "role": role,
                "session_id": self.session_id
            })

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
            self.logger.error("获取对话历史失败", exception=e, extra={"session_id": self.session_id})
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
            self.logger.error("获取对话上下文失败", exception=e, extra={"session_id": self.session_id})
            return ""

    def get_memory_variables(self) -> Dict[str, Any]:
        """获取内存变量（用于LangChain链）"""
        try:
            return self.memory.load_memory_variables({})
        except Exception as e:
            self.logger.error("获取内存变量失败", exception=e, extra={"session_id": self.session_id})
            return {}

    def clear_history(self) -> None:
        """清空对话历史"""
        try:
            self.memory.clear()
            self.logger.info("对话历史已清空", extra={"session_id": self.session_id})
        except Exception as e:
            self.logger.error("清空对话历史失败", exception=e, extra={"session_id": self.session_id})

    def reset_session(self) -> str:
        """重置会话"""
        try:
            # 清空当前对话
            self.clear_history()

            # 创建新会话
            old_session_id = self.session_id
            self._init_session()

            self.logger.info("会话已重置", extra={
                "old_session_id": old_session_id,
                "new_session_id": self.session_id
            })
            return self.session_id

        except Exception as e:
            self.logger.error("重置会话失败", exception=e, extra={"session_id": self.session_id})
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
                "start_time": self.utility.format_timestamp(self.session_start_time) if self.session_start_time else None,
                "duration_seconds": session_duration,
                "message_count": len(history),
                "max_history_length": self.max_history_length,
                "memory_type": "ConversationBufferWindowMemory"
            }

        except Exception as e:
            self.logger.error("获取会话信息失败", exception=e, extra={"session_id": self.session_id})
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
                "export_time": self.utility.format_timestamp()
            }

        except Exception as e:
            self.logger.error("导出对话历史失败", exception=e, extra={"session_id": self.session_id})
            return {
                "session_info": {"session_id": self.session_id},
                "messages": [],
                "export_time": self.utility.format_timestamp(),
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
            self.logger.error("获取对话摘要失败", exception=e, extra={"session_id": self.session_id})
            return "获取对话摘要失败"
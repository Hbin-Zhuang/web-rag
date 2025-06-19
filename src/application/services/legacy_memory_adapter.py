"""
旧内存接口兼容适配器
保持与旧 ConversationManager 的向后兼容性
内部委托给新的 MemoryService
"""

from typing import List, Dict, Any, Optional
from datetime import datetime

from .memory_service import MemoryService
from src.infrastructure.external.interfaces import ChatMessage


class ConversationManager:
    """
    旧 ConversationManager 的兼容适配器
    内部委托给新的 MemoryService，保持API兼容性
    """

    def __init__(self, max_history_length: int = None, config_service=None, logger_service=None, utility_service=None):
        """初始化对话管理器（兼容旧接口）"""
        # 内部使用新的 MemoryService
        self._memory_service = MemoryService(
            max_history_length=max_history_length,
            config_service=config_service,
            logger_service=logger_service,
            utility_service=utility_service
        )

    @property
    def memory(self):
        """获取内存对象（兼容旧接口）"""
        return self._memory_service.current_memory

    @property
    def session_id(self):
        """获取会话ID（兼容旧接口）"""
        return self._memory_service.current_session_id

    @property
    def session_start_time(self):
        """获取会话开始时间（兼容旧接口）"""
        return self._memory_service.current_session_start_time

    @property
    def max_history_length(self):
        """获取最大历史长度（兼容旧接口）"""
        return self._memory_service.max_history_length

    def add_message(self, role: str, content: str, metadata: Dict[str, Any] = None) -> None:
        """添加消息到对话历史（兼容旧接口）"""
        # 转换角色格式：human -> user, ai -> assistant
        if role.lower() == 'human':
            role = 'user'
        elif role.lower() == 'ai':
            role = 'assistant'

        self._memory_service.add_message_to_current_session(role, content, metadata)

    def get_history(self, limit: int = None) -> List[Dict[str, Any]]:
        """获取对话历史（兼容旧接口）"""
        chat_messages = self._memory_service.get_current_session_history(limit=limit)

        # 转换为旧格式
        formatted_history = []
        for msg in chat_messages:
            # 转换角色格式：user -> human, assistant -> ai
            role = "human" if msg.role == "user" else "ai"

            formatted_msg = {
                "role": role,
                "content": msg.content,
                "timestamp": msg.timestamp or '',
                "session_id": self.session_id
            }
            formatted_history.append(formatted_msg)

        return formatted_history

    def get_recent_context(self, include_messages: int = 5) -> str:
        """获取最近的对话上下文（兼容旧接口）"""
        return self._memory_service.get_current_session_context(include_messages=include_messages)

    def get_memory_variables(self) -> Dict[str, Any]:
        """获取内存变量（兼容旧接口）"""
        return self._memory_service.get_memory_variables()

    def clear_history(self) -> None:
        """清空对话历史（兼容旧接口）"""
        self._memory_service.clear_current_session()

    def reset_session(self) -> str:
        """重置会话（兼容旧接口）"""
        return self._memory_service.reset_current_session()

    def get_session_info(self) -> Dict[str, Any]:
        """获取会话信息（兼容旧接口）"""
        return self._memory_service.get_current_session_info()

    def export_history(self) -> Dict[str, Any]:
        """导出完整对话历史（兼容旧接口）"""
        try:
            history = self.get_history()
            session_info = self.get_session_info()

            return {
                "session_info": session_info,
                "messages": history,
                "export_time": datetime.now().isoformat()
            }

        except Exception as e:
            return {
                "session_info": {"session_id": self.session_id},
                "messages": [],
                "export_time": datetime.now().isoformat(),
                "error": str(e)
            }

    def get_conversation_summary(self) -> str:
        """获取对话摘要（兼容旧接口）"""
        try:
            history = self.get_history()

            if not history:
                return "暂无对话内容"

            total_messages = len(history)
            human_messages = len([msg for msg in history if msg["role"] == "human"])
            ai_messages = len([msg for msg in history if msg["role"] == "ai"])

            return f"本次对话包含 {total_messages} 条消息（用户 {human_messages} 条，助手 {ai_messages} 条）"

        except Exception as e:
            return "获取对话摘要失败"

    # 新功能的直接委托
    def save_current_session(self) -> bool:
        """保存当前会话"""
        return self._memory_service.save_current_session()

    def load_conversation(self, conversation_id: str) -> List[ChatMessage]:
        """加载对话"""
        return self._memory_service.load_conversation(conversation_id)

    def list_conversations(self) -> List[Dict[str, Any]]:
        """列出所有对话"""
        return self._memory_service.list_conversations()

    def delete_conversation(self, conversation_id: str) -> bool:
        """删除对话"""
        return self._memory_service.delete_conversation(conversation_id)
"""
内存管理服务
负责对话历史管理、会话持久化和内存优化
实现IMemoryService接口，提供现代化的内存管理能力
"""

import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
from langchain.memory import ConversationBufferWindowMemory
from langchain.schema import BaseMessage, HumanMessage, AIMessage

from src.infrastructure.external.interfaces import (
    IMemoryService,
    ChatMessage
)
from src.infrastructure.config.config_migration_adapter import get_legacy_config
from src.infrastructure.utilities import get_utility_service
from src.infrastructure import get_logger


class MemoryService(IMemoryService):
    """内存管理服务实现类"""

    def __init__(self,
                 max_history_length: int = None,
                 storage_dir: str = "./conversations",
                 config_service=None,
                 logger_service=None,
                 utility_service=None):
        """初始化内存管理服务

        Args:
            max_history_length: 最大历史长度
            storage_dir: 会话存储目录
            config_service: 配置服务实例
            logger_service: 日志服务实例
            utility_service: 工具服务实例
        """
        # 获取服务实例 (支持依赖注入)
        if config_service:
            from src.infrastructure.config.config_migration_adapter import ConfigMigrationAdapter
            self.config = ConfigMigrationAdapter(config_service)
        else:
            self.config = get_legacy_config()
        self.logger = logger_service or get_logger()
        self.utility = utility_service or get_utility_service()

        # 配置参数
        self.max_history_length = max_history_length or self.config.MAX_HISTORY_LENGTH
        self.storage_dir = Path(storage_dir)

        # 确保存储目录存在
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # 当前会话管理
        self.current_session_id = None
        self.current_session_start_time = None
        self.current_memory = None

        # 初始化当前会话
        self._init_current_session()

        self.logger.info("MemoryService 初始化完成", extra={
            "max_history_length": self.max_history_length,
            "storage_dir": str(self.storage_dir),
            "session_id": self.current_session_id
        })

    def _init_current_session(self):
        """初始化当前会话"""
        self.current_session_id = self._generate_session_id()
        self.current_session_start_time = datetime.now()
        self.current_memory = ConversationBufferWindowMemory(
            k=self.max_history_length,
            return_messages=True,
            memory_key="chat_history"
        )

        self.logger.info("新会话已创建", extra={
            "session_id": self.current_session_id,
            "start_time": self.utility.format_timestamp(self.current_session_start_time)
        })

    def _generate_session_id(self) -> str:
        """生成会话ID"""
        return f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    def _get_session_file_path(self, conversation_id: str) -> Path:
        """获取会话文件路径"""
        return self.storage_dir / f"{conversation_id}.json"

    def _chat_message_to_dict(self, message: ChatMessage) -> Dict[str, Any]:
        """将ChatMessage转换为字典"""
        return {
            "role": message.role,
            "content": message.content,
            "timestamp": message.timestamp or self.utility.format_timestamp(),
            "metadata": message.metadata or {}
        }

    def _dict_to_chat_message(self, data: Dict[str, Any]) -> ChatMessage:
        """将字典转换为ChatMessage"""
        return ChatMessage(
            role=data["role"],
            content=data["content"],
            timestamp=data.get("timestamp"),
            metadata=data.get("metadata", {})
        )

    def _langchain_message_to_chat_message(self, message: BaseMessage) -> ChatMessage:
        """将LangChain消息转换为ChatMessage"""
        role = "user" if isinstance(message, HumanMessage) else "assistant"
        metadata = getattr(message, 'additional_kwargs', {})

        return ChatMessage(
            role=role,
            content=message.content,
            timestamp=metadata.get('timestamp'),
            metadata=metadata
        )

    def _chat_message_to_langchain_message(self, message: ChatMessage) -> BaseMessage:
        """将ChatMessage转换为LangChain消息"""
        if message.role == "user":
            msg = HumanMessage(content=message.content)
        else:
            msg = AIMessage(content=message.content)

        # 添加元数据
        if hasattr(msg, 'additional_kwargs'):
            msg.additional_kwargs.update({
                "timestamp": message.timestamp,
                "session_id": self.current_session_id,
                **(message.metadata or {})
            })

        return msg

    def save_conversation(self,
                         conversation_id: str,
                         messages: List[ChatMessage]) -> bool:
        """保存对话"""
        try:
            if not conversation_id or not messages:
                self.logger.warning("会话ID或消息列表为空，跳过保存")
                return False

            # 准备保存数据
            conversation_data = {
                "conversation_id": conversation_id,
                "created_time": self.utility.format_timestamp(),
                "updated_time": self.utility.format_timestamp(),
                "message_count": len(messages),
                "messages": [self._chat_message_to_dict(msg) for msg in messages]
            }

            # 保存到文件
            file_path = self._get_session_file_path(conversation_id)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(conversation_data, f, ensure_ascii=False, indent=2)

            self.logger.info("会话已保存", extra={
                "conversation_id": conversation_id,
                "message_count": len(messages),
                "file_path": str(file_path)
            })
            return True

        except Exception as e:
            self.logger.error("保存会话失败", exception=e, extra={
                "conversation_id": conversation_id
            })
            return False

    def load_conversation(self, conversation_id: str) -> List[ChatMessage]:
        """加载对话"""
        try:
            if not conversation_id:
                self.logger.warning("会话ID为空")
                return []

            file_path = self._get_session_file_path(conversation_id)
            if not file_path.exists():
                self.logger.warning("会话文件不存在", extra={
                    "conversation_id": conversation_id,
                    "file_path": str(file_path)
                })
                return []

            with open(file_path, 'r', encoding='utf-8') as f:
                conversation_data = json.load(f)

            messages = [
                self._dict_to_chat_message(msg_data)
                for msg_data in conversation_data.get("messages", [])
            ]

            self.logger.info("会话已加载", extra={
                "conversation_id": conversation_id,
                "message_count": len(messages)
            })
            return messages

        except Exception as e:
            self.logger.error("加载会话失败", exception=e, extra={
                "conversation_id": conversation_id
            })
            return []

    def delete_conversation(self, conversation_id: str) -> bool:
        """删除对话"""
        try:
            if not conversation_id:
                self.logger.warning("会话ID为空")
                return False

            file_path = self._get_session_file_path(conversation_id)
            if file_path.exists():
                file_path.unlink()
                self.logger.info("会话已删除", extra={
                    "conversation_id": conversation_id
                })
                return True
            else:
                self.logger.warning("会话文件不存在", extra={
                    "conversation_id": conversation_id
                })
                return False

        except Exception as e:
            self.logger.error("删除会话失败", exception=e, extra={
                "conversation_id": conversation_id
            })
            return False

    def list_conversations(self) -> List[Dict[str, Any]]:
        """列出所有对话"""
        try:
            conversations = []

            for file_path in self.storage_dir.glob("*.json"):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    conversations.append({
                        "conversation_id": data.get("conversation_id"),
                        "created_time": data.get("created_time"),
                        "updated_time": data.get("updated_time"),
                        "message_count": data.get("message_count", 0),
                        "file_size": file_path.stat().st_size
                    })

                except Exception as e:
                    self.logger.warning("读取会话文件失败", exception=e, extra={
                        "file_path": str(file_path)
                    })
                    continue

            # 按创建时间排序
            conversations.sort(key=lambda x: x.get("created_time", ""), reverse=True)

            self.logger.info("会话列表已获取", extra={
                "conversation_count": len(conversations)
            })
            return conversations

        except Exception as e:
            self.logger.error("获取会话列表失败", exception=e)
            return []

    def cleanup_old_conversations(self, days: int = 30) -> int:
        """清理旧对话"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            deleted_count = 0

            for file_path in self.storage_dir.glob("*.json"):
                try:
                    # 检查文件修改时间
                    file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)

                    if file_mtime < cutoff_date:
                        file_path.unlink()
                        deleted_count += 1

                except Exception as e:
                    self.logger.warning("删除旧会话文件失败", exception=e, extra={
                        "file_path": str(file_path)
                    })
                    continue

            self.logger.info("旧会话清理完成", extra={
                "deleted_count": deleted_count,
                "cutoff_days": days
            })
            return deleted_count

        except Exception as e:
            self.logger.error("清理旧会话失败", exception=e)
            return 0

    # 扩展功能：当前会话管理

    def add_message_to_current_session(self, role: str, content: str, metadata: Dict[str, Any] = None) -> None:
        """添加消息到当前会话"""
        try:
            if not content.strip():
                self.logger.warning("消息内容为空，跳过添加")
                return

            # 创建消息对象
            timestamp = self.utility.format_timestamp()
            message_metadata = {
                "timestamp": timestamp,
                "session_id": self.current_session_id,
                **(metadata or {})
            }

            # 添加到LangChain内存
            if role.lower() == 'user':
                self.current_memory.chat_memory.add_user_message(content)
            elif role.lower() == 'assistant':
                self.current_memory.chat_memory.add_ai_message(content)
            else:
                self.logger.error(f"不支持的消息角色: {role}")
                return

            self.logger.debug("消息已添加到当前会话", extra={
                "role": role,
                "content_preview": self.utility.truncate_text(content, 50),
                "session_id": self.current_session_id
            })

        except Exception as e:
            self.logger.error("添加消息到当前会话失败", exception=e, extra={
                "role": role,
                "session_id": self.current_session_id
            })

    def get_current_session_history(self, limit: int = None) -> List[ChatMessage]:
        """获取当前会话历史"""
        try:
            if not self.current_memory:
                return []

            messages = self.current_memory.chat_memory.messages

            # 应用限制
            if limit and limit > 0:
                messages = messages[-limit:]

            # 转换为ChatMessage格式
            chat_messages = [
                self._langchain_message_to_chat_message(msg)
                for msg in messages
            ]

            return chat_messages

        except Exception as e:
            self.logger.error("获取当前会话历史失败", exception=e, extra={
                "session_id": self.current_session_id
            })
            return []

    def get_current_session_context(self, include_messages: int = 5) -> str:
        """获取当前会话上下文（用于RAG查询）"""
        try:
            recent_history = self.get_current_session_history(limit=include_messages)

            if not recent_history:
                return ""

            context_parts = []
            for msg in recent_history:
                role = "用户" if msg.role == "user" else "助手"
                context_parts.append(f"{role}: {msg.content}")

            return "\n".join(context_parts)

        except Exception as e:
            self.logger.error("获取当前会话上下文失败", exception=e, extra={
                "session_id": self.current_session_id
            })
            return ""

    def save_current_session(self) -> bool:
        """保存当前会话"""
        if not self.current_session_id:
            return False

        current_messages = self.get_current_session_history()
        return self.save_conversation(self.current_session_id, current_messages)

    def clear_current_session(self) -> None:
        """清空当前会话历史"""
        try:
            if self.current_memory:
                self.current_memory.clear()
            self.logger.info("当前会话历史已清空", extra={
                "session_id": self.current_session_id
            })
        except Exception as e:
            self.logger.error("清空当前会话历史失败", exception=e, extra={
                "session_id": self.current_session_id
            })

    def reset_current_session(self) -> str:
        """重置当前会话"""
        try:
            # 保存当前会话
            if self.current_session_id:
                self.save_current_session()

            # 创建新会话
            old_session_id = self.current_session_id
            self._init_current_session()

            self.logger.info("会话已重置", extra={
                "old_session_id": old_session_id,
                "new_session_id": self.current_session_id
            })
            return self.current_session_id

        except Exception as e:
            self.logger.error("重置会话失败", exception=e, extra={
                "session_id": self.current_session_id
            })
            return self.current_session_id

    def get_current_session_info(self) -> Dict[str, Any]:
        """获取当前会话信息"""
        try:
            history = self.get_current_session_history()

            session_duration = None
            if self.current_session_start_time:
                duration_seconds = (datetime.now() - self.current_session_start_time).total_seconds()
                session_duration = round(duration_seconds, 1)

            return {
                "session_id": self.current_session_id,
                "start_time": self.utility.format_timestamp(self.current_session_start_time) if self.current_session_start_time else None,
                "duration_seconds": session_duration,
                "message_count": len(history),
                "max_history_length": self.max_history_length,
                "memory_type": "ConversationBufferWindowMemory"
            }

        except Exception as e:
            self.logger.error("获取当前会话信息失败", exception=e, extra={
                "session_id": self.current_session_id
            })
            return {
                "session_id": self.current_session_id,
                "error": str(e)
            }

    def get_memory_variables(self) -> Dict[str, Any]:
        """获取内存变量（用于LangChain链）"""
        try:
            if not self.current_memory:
                return {}
            return self.current_memory.load_memory_variables({})
        except Exception as e:
            self.logger.error("获取内存变量失败", exception=e, extra={
                "session_id": self.current_session_id
            })
            return {}

    def get_service_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        try:
            conversations = self.list_conversations()
            current_session_info = self.get_current_session_info()

            return {
                "service_name": "MemoryService",
                "status": "active",
                "current_session": current_session_info,
                "total_conversations": len(conversations),
                "storage_dir": str(self.storage_dir),
                "max_history_length": self.max_history_length
            }

        except Exception as e:
            self.logger.error("获取服务状态失败", exception=e)
            return {
                "service_name": "MemoryService",
                "status": "error",
                "error": str(e)
            }
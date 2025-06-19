"""
应用状态管理单例类
替代 app.py 中的全局变量，提供线程安全的状态管理
集成基础设施层的配置和日志服务
"""

import threading
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

from ...infrastructure import (
    IConfigurationService,
    ILoggingService,
    get_config,
    get_logger
)


@dataclass
class FileInfo:
    """上传文件信息"""
    name: str
    upload_time: datetime
    pages: int
    chunks: int
    model: str
    file_hash: Optional[str] = None


class ApplicationState:
    """应用状态管理单例类"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._state_lock = threading.RLock()

        # 基础设施服务
        self._config_service: IConfigurationService = get_config()
        self._logger: ILoggingService = get_logger()

        # 向量存储相关
        self._vectorstore = None
        self._qa_chain = None

        # 模型管理（从配置获取）
        self._current_model = self._config_service.get_value("chat_model")
        self._available_models = self._config_service.get_value("fallback_models")

        # 文件管理
        self._uploaded_files: List[FileInfo] = []

        # 系统状态
        self._system_ready = False
        self._last_update = datetime.now()

        # 应用服务引用（延迟初始化）
        self._memory_service = None
        self._chat_service = None
        self._document_service = None

        self._initialized = True
        self._logger.info("ApplicationState 初始化完成", extra={
            "current_model": self._current_model,
            "available_models_count": len(self._available_models)
        })

    @property
    def vectorstore(self):
        """获取向量存储"""
        with self._state_lock:
            return self._vectorstore

    @vectorstore.setter
    def vectorstore(self, value):
        """设置向量存储"""
        with self._state_lock:
            self._vectorstore = value
            self._last_update = datetime.now()
            self._logger.info("向量存储已更新", extra={
                "vectorstore_type": type(value).__name__ if value else None
            })

    @property
    def qa_chain(self):
        """获取问答链"""
        with self._state_lock:
            return self._qa_chain

    @qa_chain.setter
    def qa_chain(self, value):
        """设置问答链"""
        with self._state_lock:
            self._qa_chain = value
            self._last_update = datetime.now()

    @property
    def current_model(self) -> str:
        """获取当前模型"""
        with self._state_lock:
            return self._current_model

    @current_model.setter
    def current_model(self, value: str):
        """设置当前模型"""
        with self._state_lock:
            if value in self._available_models:
                old_model = self._current_model
                self._current_model = value
                self._last_update = datetime.now()
                self._logger.info("模型已切换", extra={
                    "old_model": old_model,
                    "new_model": value
                })
            else:
                self._logger.error("尝试设置不支持的模型", extra={
                    "requested_model": value,
                    "available_models": self._available_models
                })
                raise ValueError(f"不支持的模型: {value}")

    @property
    def available_models(self) -> List[str]:
        """获取可用模型列表"""
        with self._state_lock:
            return self._available_models.copy()

    def add_uploaded_file(self, file_info: FileInfo):
        """添加上传文件信息"""
        with self._state_lock:
            self._uploaded_files.append(file_info)
            self._last_update = datetime.now()

    def get_uploaded_files(self) -> List[FileInfo]:
        """获取上传文件列表"""
        with self._state_lock:
            return self._uploaded_files.copy()

    def clear_uploaded_files(self):
        """清空上传文件列表"""
        with self._state_lock:
            self._uploaded_files.clear()
            self._last_update = datetime.now()

    @property
    def system_ready(self) -> bool:
        """系统是否就绪"""
        with self._state_lock:
            return self._system_ready

    @system_ready.setter
    def system_ready(self, value: bool):
        """设置系统就绪状态"""
        with self._state_lock:
            self._system_ready = value
            self._last_update = datetime.now()

    # 应用服务管理

    @property
    def memory_service(self):
        """获取内存服务"""
        with self._state_lock:
            if self._memory_service is None:
                try:
                    from ...application.services.memory_service import MemoryService
                    self._memory_service = MemoryService(
                        config_service=self._config_service,
                        logger_service=self._logger
                    )
                    self._logger.info("内存服务已延迟初始化")
                except ImportError as e:
                    self._logger.error("内存服务初始化失败", exception=e)
                    return None
            return self._memory_service

    @memory_service.setter
    def memory_service(self, value):
        """设置内存服务"""
        with self._state_lock:
            self._memory_service = value
            self._last_update = datetime.now()
            self._logger.info("内存服务已更新", extra={
                "service_type": type(value).__name__ if value else None
            })

    @property
    def chat_service(self):
        """获取聊天服务"""
        with self._state_lock:
            if self._chat_service is None:
                try:
                    from ...application.services.chat_service import ChatService
                    self._chat_service = ChatService(
                        memory_service=self.memory_service,
                        config_service=self._config_service,
                        logger_service=self._logger
                    )
                    self._logger.info("聊天服务已延迟初始化")
                except ImportError as e:
                    self._logger.error("聊天服务初始化失败", exception=e)
                    return None
            return self._chat_service

    @chat_service.setter
    def chat_service(self, value):
        """设置聊天服务"""
        with self._state_lock:
            self._chat_service = value
            self._last_update = datetime.now()
            self._logger.info("聊天服务已更新", extra={
                "service_type": type(value).__name__ if value else None
            })

    @property
    def document_service(self):
        """获取文档服务"""
        with self._state_lock:
            if self._document_service is None:
                try:
                    from ...application.services.document_service import DocumentService
                    self._document_service = DocumentService(
                        config_service=self._config_service,
                        logger_service=self._logger
                    )
                    self._logger.info("文档服务已延迟初始化")
                except ImportError as e:
                    self._logger.error("文档服务初始化失败", exception=e)
                    return None
            return self._document_service

    @document_service.setter
    def document_service(self, value):
        """设置文档服务"""
        with self._state_lock:
            self._document_service = value
            self._last_update = datetime.now()
            self._logger.info("文档服务已更新", extra={
                "service_type": type(value).__name__ if value else None
            })

    def get_state_info(self) -> Dict[str, Any]:
        """获取状态信息"""
        with self._state_lock:
            # 获取服务状态
            services_status = {}

            if self._memory_service:
                try:
                    services_status["memory_service"] = self._memory_service.get_service_status()
                except Exception as e:
                    services_status["memory_service"] = {"error": str(e)}

            if self._chat_service:
                try:
                    services_status["chat_service"] = self._chat_service.get_service_status()
                except Exception as e:
                    services_status["chat_service"] = {"error": str(e)}

            if self._document_service:
                try:
                    services_status["document_service"] = self._document_service.get_service_status()
                except Exception as e:
                    services_status["document_service"] = {"error": str(e)}

            return {
                "current_model": self._current_model,
                "available_models": self._available_models.copy(),
                "uploaded_files_count": len(self._uploaded_files),
                "vectorstore_initialized": self._vectorstore is not None,
                "qa_chain_initialized": self._qa_chain is not None,
                "system_ready": self._system_ready,
                "last_update": self._last_update.isoformat(),
                "services": services_status
            }

    def reset_state(self):
        """重置状态（保留配置和服务实例）"""
        with self._state_lock:
            self._vectorstore = None
            self._qa_chain = None
            self._uploaded_files.clear()
            self._system_ready = False
            self._last_update = datetime.now()

            # 重置内存服务的当前会话
            if self._memory_service:
                try:
                    self._memory_service.reset_current_session()
                    self._logger.info("内存服务会话已重置")
                except Exception as e:
                    self._logger.error("重置内存服务会话失败", exception=e)

    def cleanup_resources(self):
        """清理资源（在应用关闭时调用）"""
        with self._state_lock:
            # 保存当前会话
            if self._memory_service:
                try:
                    self._memory_service.save_current_session()
                    self._logger.info("当前会话已保存")
                except Exception as e:
                    self._logger.error("保存当前会话失败", exception=e)

            # 清理旧会话
            if self._memory_service:
                try:
                    cleaned_count = self._memory_service.cleanup_old_conversations(days=30)
                    self._logger.info("旧会话清理完成", extra={"cleaned_count": cleaned_count})
                except Exception as e:
                    self._logger.error("清理旧会话失败", exception=e)

    def get_service_registry(self) -> Dict[str, Any]:
        """获取服务注册表"""
        with self._state_lock:
            return {
                "memory_service": self._memory_service,
                "chat_service": self._chat_service,
                "document_service": self._document_service,
                "config_service": self._config_service,
                "logger_service": self._logger
            }


# 全局状态实例
app_state = ApplicationState()
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

    def get_state_info(self) -> Dict[str, Any]:
        """获取状态信息"""
        with self._state_lock:
            return {
                "current_model": self._current_model,
                "available_models": self._available_models.copy(),
                "uploaded_files_count": len(self._uploaded_files),
                "vectorstore_initialized": self._vectorstore is not None,
                "qa_chain_initialized": self._qa_chain is not None,
                "system_ready": self._system_ready,
                "last_update": self._last_update.isoformat()
            }

    def reset_state(self):
        """重置状态（保留配置）"""
        with self._state_lock:
            self._vectorstore = None
            self._qa_chain = None
            self._uploaded_files.clear()
            self._system_ready = False
            self._last_update = datetime.now()


# 全局状态实例
app_state = ApplicationState()
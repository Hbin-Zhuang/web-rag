"""
配置抽象服务
提供统一的配置管理、环境适配和配置验证能力
"""

import os
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Union, List
from dataclasses import dataclass
from enum import Enum
from dotenv import load_dotenv


class Environment(Enum):
    """运行环境枚举"""
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"
    STAGING = "staging"


@dataclass
class ConfigurationValidationResult:
    """配置验证结果"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]


class IConfigurationService(ABC):
    """配置服务抽象接口"""

    @abstractmethod
    def get_value(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        pass

    @abstractmethod
    def set_value(self, key: str, value: Any) -> None:
        """设置配置值"""
        pass

    @abstractmethod
    def validate_configuration(self) -> ConfigurationValidationResult:
        """验证配置完整性"""
        pass

    @abstractmethod
    def get_environment(self) -> Environment:
        """获取当前运行环境"""
        pass

    @abstractmethod
    def get_all_configs(self) -> Dict[str, Any]:
        """获取所有配置项（安全版本）"""
        pass


class ConfigurationService(IConfigurationService):
    """配置服务实现类"""

    def __init__(self, environment: Optional[Environment] = None):
        """初始化配置服务

        Args:
            environment: 指定运行环境，如果不指定则自动检测
        """
        # 加载环境变量
        load_dotenv()

        # 设置运行环境
        self._environment = environment or self._detect_environment()

        # 内部配置存储
        self._config_cache: Dict[str, Any] = {}

        # 初始化默认配置
        self._init_default_configs()

        # 敏感配置列表（用于安全显示）
        self._sensitive_keys = {
            'google_api_key', 'api_key', 'secret', 'password', 'token'
        }

    def _detect_environment(self) -> Environment:
        """自动检测运行环境"""
        env_str = os.getenv("APP_ENVIRONMENT", "development").lower()

        # 检测特殊环境标识
        if os.getenv("SPACE_ID"):  # Hugging Face Spaces
            return Environment.PRODUCTION

        if env_str == "production":
            return Environment.PRODUCTION
        elif env_str == "testing":
            return Environment.TESTING
        elif env_str == "staging":
            return Environment.STAGING
        else:
            return Environment.DEVELOPMENT

    def _init_default_configs(self) -> None:
        """初始化默认配置"""
        self._default_configs = {
            # Google API 配置
            "google_api_key": None,

            # 模型配置
            "embedding_model": "models/embedding-001",
            "chat_model": "gemini-2.0-flash",
            "fallback_models": [
                "gemini-2.0-flash",
                "gemini-2.0-flash-lite",
                "gemini-1.5-flash",
                "gemini-1.5-pro"
            ],

            # 文本处理配置
            "chunk_size": 1000,
            "chunk_overlap": 200,
            "max_tokens": 1000,

            # 检索配置
            "similarity_top_k": 4,
            "search_similarity_threshold": 0.7,

            # 数据库配置
            "chroma_db_path": "./chroma_db",
            "chroma_collection_name": "documents",

            # 文件上传配置
            "max_file_size_mb": 50,
            "allowed_file_types": [".pdf"],
            "upload_temp_dir": "./uploads",

            # 对话配置
            "max_history_length": 10,
            "conversation_timeout_minutes": 30,

            # 性能配置
            "request_timeout_seconds": 120,
            "max_concurrent_requests": 5,
            "rate_limit_requests_per_minute": 60,

            # UI配置
            "gradio_server_name": "127.0.0.1",
            "gradio_server_port": 7862,
            "gradio_debug": True,

            # 日志配置
            "log_level": "INFO",
            "log_format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "log_file_path": "./logs/app.log",
            "log_max_file_size_mb": 10,
            "log_backup_count": 5,
        }

        # 根据环境调整默认配置
        if self._environment == Environment.PRODUCTION:
            self._default_configs.update({
                "gradio_debug": False,
                "log_level": "WARNING",
                "gradio_server_name": "0.0.0.0",
                "gradio_server_port": 7860,
            })
        elif self._environment == Environment.TESTING:
            self._default_configs.update({
                "log_level": "DEBUG",
                "max_file_size_mb": 10,  # 测试环境限制文件大小
                "chroma_db_path": "./test_chroma_db",
            })

    def get_value(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        # 先检查缓存
        if key in self._config_cache:
            return self._config_cache[key]

        # 转换为环境变量格式
        env_key = key.upper()

        # 从环境变量获取
        env_value = os.getenv(env_key)
        if env_value is not None:
            # 尝试类型转换
            converted_value = self._convert_value(env_value, key)
            self._config_cache[key] = converted_value
            return converted_value

        # 从默认配置获取
        if key in self._default_configs:
            value = self._default_configs[key]
            self._config_cache[key] = value
            return value

        # 返回提供的默认值
        return default

    def set_value(self, key: str, value: Any) -> None:
        """设置配置值"""
        self._config_cache[key] = value

    def _convert_value(self, value: str, key: str) -> Any:
        """根据键名和默认值类型转换环境变量值"""
        # 获取默认值以确定类型
        default_value = self._default_configs.get(key)

        if isinstance(default_value, bool):
            return value.lower() in ('true', '1', 'yes', 'on')
        elif isinstance(default_value, int):
            try:
                return int(value)
            except ValueError:
                return default_value
        elif isinstance(default_value, float):
            try:
                return float(value)
            except ValueError:
                return default_value
        elif isinstance(default_value, list):
            # 支持逗号分隔的列表
            if ',' in value:
                return [item.strip() for item in value.split(',')]
            else:
                return [value]
        else:
            return value

    def validate_configuration(self) -> ConfigurationValidationResult:
        """验证配置完整性"""
        errors = []
        warnings = []

        # 检查必需的配置项
        api_key = self.get_value("google_api_key")
        if not api_key:
            errors.append("Google API Key 未配置")
        elif not api_key.startswith('AIza'):
            warnings.append("Google API Key 格式可能不正确")

        # 检查文件路径配置
        chroma_path = self.get_value("chroma_db_path")
        upload_dir = self.get_value("upload_temp_dir")

        try:
            os.makedirs(os.path.dirname(chroma_path), exist_ok=True)
            os.makedirs(upload_dir, exist_ok=True)
        except Exception as e:
            errors.append(f"无法创建必要目录: {e}")

        # 检查数值配置合理性
        chunk_size = self.get_value("chunk_size")
        if chunk_size <= 0:
            errors.append("chunk_size 必须大于0")

        max_file_size = self.get_value("max_file_size_mb")
        if max_file_size <= 0:
            errors.append("max_file_size_mb 必须大于0")

        # 检查端口配置
        port = self.get_value("gradio_server_port")
        if not (1024 <= port <= 65535):
            warnings.append(f"端口 {port} 可能不在推荐范围内 (1024-65535)")

        return ConfigurationValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    def get_environment(self) -> Environment:
        """获取当前运行环境"""
        return self._environment

    def get_all_configs(self) -> Dict[str, Any]:
        """获取所有配置项（安全版本）"""
        all_configs = {}

        # 合并默认配置和缓存配置
        for key in self._default_configs.keys():
            value = self.get_value(key)

            # 敏感信息脱敏处理
            if any(sensitive in key.lower() for sensitive in self._sensitive_keys):
                if value and len(str(value)) > 8:
                    all_configs[key] = f"{str(value)[:4]}...{str(value)[-4:]}"
                elif value:
                    all_configs[key] = "***已配置***"
                else:
                    all_configs[key] = "***未配置***"
            else:
                all_configs[key] = value

        return all_configs

    def get_model_configs(self) -> Dict[str, Any]:
        """获取模型相关配置"""
        return {
            "chat_model": self.get_value("chat_model"),
            "embedding_model": self.get_value("embedding_model"),
            "fallback_models": self.get_value("fallback_models"),
            "max_tokens": self.get_value("max_tokens"),
            "request_timeout": self.get_value("request_timeout_seconds"),
        }

    def get_gradio_configs(self) -> Dict[str, Any]:
        """获取Gradio相关配置"""
        return {
            "server_name": self.get_value("gradio_server_name"),
            "server_port": self.get_value("gradio_server_port"),
            "debug": self.get_value("gradio_debug"),
            "share": self._environment == Environment.PRODUCTION,
            "show_error": self.get_value("gradio_debug"),
            "inbrowser": False,
        }

    def get_database_configs(self) -> Dict[str, Any]:
        """获取数据库相关配置"""
        return {
            "chroma_db_path": self.get_value("chroma_db_path"),
            "collection_name": self.get_value("chroma_collection_name"),
        }

    def reload_configuration(self) -> None:
        """重新加载配置"""
        self._config_cache.clear()
        load_dotenv(override=True)


# 创建全局配置服务单例
_config_service: Optional[ConfigurationService] = None


def get_config_service() -> ConfigurationService:
    """获取配置服务单例"""
    global _config_service
    if _config_service is None:
        _config_service = ConfigurationService()
    return _config_service


def create_config_service(environment: Optional[Environment] = None) -> ConfigurationService:
    """创建新的配置服务实例（主要用于测试）"""
    return ConfigurationService(environment)
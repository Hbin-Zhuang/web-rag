"""
配置迁移适配器
提供与旧Config类兼容的接口，同时使用新的ConfigurationService
用于渐进式迁移，保持向后兼容性
"""

from typing import Optional, List, Dict, Any
from ..config.configuration_service import ConfigurationService, get_config_service


class ConfigMigrationAdapter:
    """配置迁移适配器 - 提供Config类兼容接口"""

    def __init__(self, config_service: Optional[ConfigurationService] = None):
        """初始化适配器

        Args:
            config_service: 配置服务实例，如果不提供则使用默认实例
        """
        self._config_service = config_service or get_config_service()

    # Google API 配置
    @property
    def GOOGLE_API_KEY(self) -> Optional[str]:
        return self._config_service.get_value("google_api_key")

    # 模型配置
    @property
    def EMBEDDING_MODEL(self) -> str:
        return self._config_service.get_value("embedding_model", "models/embedding-001")

    @property
    def CHAT_MODEL(self) -> str:
        return self._config_service.get_value("chat_model", "gemini-2.0-flash-001")

    # 文本处理配置
    @property
    def CHUNK_SIZE(self) -> int:
        return self._config_service.get_value("chunk_size", 1000)

    @property
    def CHUNK_OVERLAP(self) -> int:
        return self._config_service.get_value("chunk_overlap", 200)

    # 检索配置
    @property
    def SIMILARITY_TOP_K(self) -> int:
        return self._config_service.get_value("similarity_top_k", 4)

    @property
    def MAX_TOKENS(self) -> int:
        return self._config_service.get_value("max_tokens", 1000)

    # 数据库配置
    @property
    def CHROMA_DB_PATH(self) -> str:
        return self._config_service.get_value("chroma_db_path", "./chroma_db")

    # 文件上传配置
    @property
    def MAX_FILE_SIZE_MB(self) -> int:
        return self._config_service.get_value("max_file_size_mb", 50)

    @property
    def ALLOWED_FILE_TYPES(self) -> List[str]:
        return self._config_service.get_value("allowed_file_types", [".pdf"])

    # 对话配置
    @property
    def MAX_HISTORY_LENGTH(self) -> int:
        return self._config_service.get_value("max_history_length", 10)

    def validate_config(self) -> bool:
        """验证配置是否有效"""
        validation_result = self._config_service.validate_configuration()
        return validation_result.is_valid

    def get_config_info(self) -> Dict[str, Any]:
        """获取配置信息（隐藏敏感信息）"""
        # 使用ConfigurationService的安全配置显示
        all_configs = self._config_service.get_all_configs()

        return {
            "embedding_model": all_configs.get("embedding_model"),
            "chat_model": all_configs.get("chat_model"),
            "chunk_size": all_configs.get("chunk_size"),
            "chunk_overlap": all_configs.get("chunk_overlap"),
            "similarity_top_k": all_configs.get("similarity_top_k"),
            "max_tokens": all_configs.get("max_tokens"),
            "max_history_length": all_configs.get("max_history_length"),
            "api_key_configured": bool(all_configs.get("google_api_key")),
            "api_key_display": all_configs.get("google_api_key", "未配置")  # 已经脱敏处理
        }


# 创建全局兼容实例
Config = ConfigMigrationAdapter()


def get_legacy_config() -> ConfigMigrationAdapter:
    """获取兼容性配置实例"""
    return Config
"""
系统配置模块
管理环境变量、系统常量和配置参数
"""

import os
from typing import Optional
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class Config:
    """系统配置类"""

    # Google API 配置
    GOOGLE_API_KEY: Optional[str] = os.getenv("GOOGLE_API_KEY")

    # 模型配置
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "models/embedding-001")
    CHAT_MODEL: str = os.getenv("CHAT_MODEL", "gemini-2.0-flash-001")

    # 文本处理配置
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "1000"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "200"))

    # 检索配置
    SIMILARITY_TOP_K: int = int(os.getenv("SIMILARITY_TOP_K", "4"))
    MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "1000"))

    # 数据库配置
    CHROMA_DB_PATH: str = os.getenv("CHROMA_DB_PATH", "./chroma_db")

    # 文件上传配置
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "50"))
    ALLOWED_FILE_TYPES: list = [".pdf"]

    # 对话配置
    MAX_HISTORY_LENGTH: int = int(os.getenv("MAX_HISTORY_LENGTH", "10"))

    @classmethod
    def validate_config(cls) -> bool:
        """验证配置是否有效"""
        if not cls.GOOGLE_API_KEY:
            return False

        # 检查API key格式（Google API key通常以AIza开头）
        if not cls.GOOGLE_API_KEY.startswith('AIza'):
            print(f"⚠️  警告：API Key格式可能不正确，请确认是Google AI Studio的API Key")

        return True

    @classmethod
    def get_config_info(cls) -> dict:
        """获取配置信息（隐藏敏感信息）"""
        # 安全地显示API key信息（只显示前4位和后4位）
        api_key_display = "未配置"
        if cls.GOOGLE_API_KEY:
            if len(cls.GOOGLE_API_KEY) > 8:
                api_key_display = f"{cls.GOOGLE_API_KEY[:4]}...{cls.GOOGLE_API_KEY[-4:]}"
            else:
                api_key_display = "已配置（格式异常）"

        return {
            "embedding_model": cls.EMBEDDING_MODEL,
            "chat_model": cls.CHAT_MODEL,
            "chunk_size": cls.CHUNK_SIZE,
            "chunk_overlap": cls.CHUNK_OVERLAP,
            "similarity_top_k": cls.SIMILARITY_TOP_K,
            "max_tokens": cls.MAX_TOKENS,
            "max_history_length": cls.MAX_HISTORY_LENGTH,
            "api_key_configured": bool(cls.GOOGLE_API_KEY),
            "api_key_display": api_key_display
        }
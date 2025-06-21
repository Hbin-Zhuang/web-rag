"""
生产环境配置管理
提供生产就绪的配置、安全性和性能优化
"""

import os
import json
import secrets
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib

from ..logging.logging_service import get_logging_service


@dataclass
class SecurityConfig:
    """安全配置"""
    api_key_encryption: bool = True
    rate_limiting_enabled: bool = True
    cors_origins: List[str] = None
    max_file_size_mb: int = 50
    allowed_file_types: List[str] = None
    session_timeout: int = 3600
    csrf_protection: bool = True
    secure_headers: bool = True

    def __post_init__(self):
        if self.cors_origins is None:
            self.cors_origins = ["*"]
        if self.allowed_file_types is None:
            self.allowed_file_types = [".pdf", ".txt", ".docx", ".md"]


@dataclass
class PerformanceConfig:
    """性能配置"""
    max_concurrent_requests: int = 100
    request_timeout: int = 300
    cache_size_mb: int = 512
    thread_pool_size: int = 8
    enable_compression: bool = True
    optimize_embeddings: bool = True
    batch_processing_size: int = 32
    memory_limit_mb: int = 2048
    cpu_cores_limit: int = 4


@dataclass
class MonitoringConfig:
    """监控配置"""
    metrics_enabled: bool = True
    health_check_interval: int = 60
    log_level: str = "INFO"
    error_reporting: bool = True
    performance_tracking: bool = True
    retention_days: int = 30
    alert_thresholds: Dict[str, float] = None

    def __post_init__(self):
        if self.alert_thresholds is None:
            self.alert_thresholds = {
                'cpu_usage': 80.0,
                'memory_usage': 85.0,
                'error_rate': 5.0,
                'response_time': 2.0
            }


@dataclass
class DatabaseConfig:
    """数据库配置"""
    connection_pool_size: int = 20
    connection_timeout: int = 30
    retry_attempts: int = 3
    backup_enabled: bool = True
    backup_interval_hours: int = 24
    vacuum_enabled: bool = True
    vacuum_interval_hours: int = 168  # 一周


@dataclass
class CacheConfig:
    """缓存配置"""
    redis_url: Optional[str] = None
    default_ttl: int = 3600
    max_cache_size_mb: int = 256
    eviction_policy: str = "LRU"
    compression_enabled: bool = True
    distributed: bool = False


class ProductionConfigManager:
    """生产环境配置管理器"""

    def __init__(self, config_dir: str = "config"):
        """初始化配置管理器

        Args:
            config_dir: 配置文件目录
        """
        self._logger = get_logging_service()
        self._config_dir = Path(config_dir)
        self._config_dir.mkdir(exist_ok=True)

        # 配置组件
        self.security = SecurityConfig()
        self.performance = PerformanceConfig()
        self.monitoring = MonitoringConfig()
        self.database = DatabaseConfig()
        self.cache = CacheConfig()

        # 环境变量映射
        self._env_mappings = {
            # 安全配置
            'SECURITY_API_KEY_ENCRYPTION': ('security', 'api_key_encryption', bool),
            'SECURITY_RATE_LIMITING': ('security', 'rate_limiting_enabled', bool),
            'SECURITY_MAX_FILE_SIZE': ('security', 'max_file_size_mb', int),
            'SECURITY_SESSION_TIMEOUT': ('security', 'session_timeout', int),

            # 性能配置
            'PERFORMANCE_MAX_REQUESTS': ('performance', 'max_concurrent_requests', int),
            'PERFORMANCE_REQUEST_TIMEOUT': ('performance', 'request_timeout', int),
            'PERFORMANCE_CACHE_SIZE': ('performance', 'cache_size_mb', int),
            'PERFORMANCE_THREAD_POOL': ('performance', 'thread_pool_size', int),
            'PERFORMANCE_MEMORY_LIMIT': ('performance', 'memory_limit_mb', int),

            # 监控配置
            'MONITORING_LOG_LEVEL': ('monitoring', 'log_level', str),
            'MONITORING_HEALTH_INTERVAL': ('monitoring', 'health_check_interval', int),
            'MONITORING_RETENTION_DAYS': ('monitoring', 'retention_days', int),

            # 数据库配置
            'DATABASE_POOL_SIZE': ('database', 'connection_pool_size', int),
            'DATABASE_TIMEOUT': ('database', 'connection_timeout', int),
            'DATABASE_BACKUP_INTERVAL': ('database', 'backup_interval_hours', int),

            # 缓存配置
            'CACHE_REDIS_URL': ('cache', 'redis_url', str),
            'CACHE_DEFAULT_TTL': ('cache', 'default_ttl', int),
            'CACHE_MAX_SIZE': ('cache', 'max_cache_size_mb', int),
        }

        # 加载配置
        self._load_from_environment()
        self._load_from_files()

        self._logger.info("生产环境配置管理器初始化完成")

    def _load_from_environment(self):
        """从环境变量加载配置"""
        for env_var, (section, field, var_type) in self._env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                try:
                    # 类型转换
                    if var_type == bool:
                        value = value.lower() in ('true', '1', 'yes', 'on')
                    elif var_type == int:
                        value = int(value)
                    elif var_type == float:
                        value = float(value)

                    # 设置配置值
                    config_obj = getattr(self, section)
                    setattr(config_obj, field, value)

                    self._logger.debug(f"从环境变量加载配置: {env_var} = {value}")

                except (ValueError, TypeError) as e:
                    self._logger.warning(f"环境变量 {env_var} 类型转换失败: {e}")

    def _load_from_files(self):
        """从配置文件加载配置"""
        config_files = {
            'security.json': 'security',
            'performance.json': 'performance',
            'monitoring.json': 'monitoring',
            'database.json': 'database',
            'cache.json': 'cache'
        }

        for filename, section in config_files.items():
            config_path = self._config_dir / filename
            if config_path.exists():
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    config_obj = getattr(self, section)

                    # 更新配置对象
                    for key, value in data.items():
                        if hasattr(config_obj, key):
                            setattr(config_obj, key, value)

                    self._logger.info(f"从文件加载配置: {filename}")

                except Exception as e:
                    self._logger.error(f"加载配置文件失败: {filename}", exception=e)

    def save_to_files(self):
        """保存配置到文件"""
        config_objects = {
            'security.json': self.security,
            'performance.json': self.performance,
            'monitoring.json': self.monitoring,
            'database.json': self.database,
            'cache.json': self.cache
        }

        for filename, config_obj in config_objects.items():
            config_path = self._config_dir / filename
            try:
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(asdict(config_obj), f, indent=2, ensure_ascii=False)

                self._logger.info(f"配置保存到文件: {filename}")

            except Exception as e:
                self._logger.error(f"保存配置文件失败: {filename}", exception=e)

    def get_all_config(self) -> Dict[str, Any]:
        """获取所有配置

        Returns:
            完整配置字典
        """
        return {
            'security': asdict(self.security),
            'performance': asdict(self.performance),
            'monitoring': asdict(self.monitoring),
            'database': asdict(self.database),
            'cache': asdict(self.cache)
        }

    def validate_config(self) -> List[str]:
        """验证配置有效性

        Returns:
            验证错误列表
        """
        errors = []

        # 验证安全配置
        if self.security.max_file_size_mb <= 0:
            errors.append("安全配置: 最大文件大小必须大于0")

        if self.security.session_timeout <= 0:
            errors.append("安全配置: 会话超时时间必须大于0")

        # 验证性能配置
        if self.performance.max_concurrent_requests <= 0:
            errors.append("性能配置: 最大并发请求数必须大于0")

        if self.performance.thread_pool_size <= 0:
            errors.append("性能配置: 线程池大小必须大于0")

        if self.performance.memory_limit_mb <= 0:
            errors.append("性能配置: 内存限制必须大于0")

        # 验证监控配置
        valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if self.monitoring.log_level not in valid_log_levels:
            errors.append(f"监控配置: 日志级别必须是 {valid_log_levels} 之一")

        # 验证数据库配置
        if self.database.connection_pool_size <= 0:
            errors.append("数据库配置: 连接池大小必须大于0")

        # 验证缓存配置
        if self.cache.default_ttl <= 0:
            errors.append("缓存配置: 默认TTL必须大于0")

        if errors:
            self._logger.warning(f"配置验证发现 {len(errors)} 个问题")
        else:
            self._logger.info("配置验证通过")

        return errors

    def generate_secret_key(self) -> str:
        """生成安全密钥

        Returns:
            随机生成的密钥
        """
        secret_key = secrets.token_urlsafe(32)
        self._logger.info("生成新的安全密钥")
        return secret_key

    def get_security_headers(self) -> Dict[str, str]:
        """获取安全头配置

        Returns:
            安全头字典
        """
        if not self.security.secure_headers:
            return {}

        return {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            'Content-Security-Policy': "default-src 'self'",
            'Referrer-Policy': 'strict-origin-when-cross-origin'
        }

    def get_cors_config(self) -> Dict[str, Any]:
        """获取CORS配置

        Returns:
            CORS配置字典
        """
        return {
            'origins': self.security.cors_origins,
            'allow_credentials': True,
            'allow_methods': ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
            'allow_headers': ['*']
        }

    def optimize_for_production(self):
        """针对生产环境优化配置"""
        # 安全优化
        self.security.api_key_encryption = True
        self.security.rate_limiting_enabled = True
        self.security.csrf_protection = True
        self.security.secure_headers = True

        # 性能优化
        self.performance.enable_compression = True
        self.performance.optimize_embeddings = True

        # 监控优化
        self.monitoring.metrics_enabled = True
        self.monitoring.error_reporting = True
        self.monitoring.performance_tracking = True
        self.monitoring.log_level = "INFO"

        # 数据库优化
        self.database.backup_enabled = True
        self.database.vacuum_enabled = True

        # 缓存优化
        self.cache.compression_enabled = True

        self._logger.info("配置已针对生产环境优化")

    def get_config_summary(self) -> str:
        """获取配置摘要

        Returns:
            配置摘要字符串
        """
        config_str = json.dumps(self.get_all_config(), sort_keys=True)
        config_hash = hashlib.md5(config_str.encode()).hexdigest()[:8]

        return (
            f"生产环境配置摘要:\n"
            f"- 安全: 加密={self.security.api_key_encryption}, "
            f"限流={self.security.rate_limiting_enabled}\n"
            f"- 性能: 并发={self.performance.max_concurrent_requests}, "
            f"缓存={self.performance.cache_size_mb}MB\n"
            f"- 监控: 级别={self.monitoring.log_level}, "
            f"指标={self.monitoring.metrics_enabled}\n"
            f"- 数据库: 池={self.database.connection_pool_size}, "
            f"备份={self.database.backup_enabled}\n"
            f"- 缓存: TTL={self.cache.default_ttl}s, "
            f"大小={self.cache.max_cache_size_mb}MB\n"
            f"- 配置哈希: {config_hash}"
        )


# 全局配置管理器实例
_production_config_instance: Optional[ProductionConfigManager] = None


def get_production_config() -> ProductionConfigManager:
    """获取生产环境配置管理器单例实例"""
    global _production_config_instance

    if _production_config_instance is None:
        _production_config_instance = ProductionConfigManager()

    return _production_config_instance
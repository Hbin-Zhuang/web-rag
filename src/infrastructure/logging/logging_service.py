"""
日志抽象服务
提供统一的日志管理、结构化日志和监控能力
"""

import os
import sys
import logging
import json
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Union, List
from datetime import datetime
from logging.handlers import RotatingFileHandler
from dataclasses import dataclass, asdict
from enum import Enum


class LogLevel(Enum):
    """日志级别枚举"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class LogEntry:
    """日志条目结构"""
    timestamp: str
    level: str
    logger_name: str
    message: str
    module: Optional[str] = None
    function: Optional[str] = None
    line_number: Optional[int] = None
    extra_data: Optional[Dict[str, Any]] = None
    exception_info: Optional[str] = None


class ILoggingService(ABC):
    """日志服务抽象接口"""

    @abstractmethod
    def debug(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """记录调试信息"""
        pass

    @abstractmethod
    def info(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """记录信息"""
        pass

    @abstractmethod
    def warning(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """记录警告"""
        pass

    @abstractmethod
    def error(self, message: str, exception: Optional[Exception] = None, extra: Optional[Dict[str, Any]] = None) -> None:
        """记录错误"""
        pass

    @abstractmethod
    def critical(self, message: str, exception: Optional[Exception] = None, extra: Optional[Dict[str, Any]] = None) -> None:
        """记录严重错误"""
        pass

    @abstractmethod
    def set_level(self, level: LogLevel) -> None:
        """设置日志级别"""
        pass


class StructuredFormatter(logging.Formatter):
    """结构化日志格式化器"""

    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录"""
        # 创建基础日志条目
        log_entry = LogEntry(
            timestamp=datetime.fromtimestamp(record.created).isoformat(),
            level=record.levelname,
            logger_name=record.name,
            message=record.getMessage(),
            module=record.module,
            function=record.funcName,
            line_number=record.lineno,
        )

        # 添加额外数据
        if hasattr(record, 'extra_data'):
            log_entry.extra_data = record.extra_data

        # 添加异常信息
        if record.exc_info:
            log_entry.exception_info = self.formatException(record.exc_info)

        # 转换为JSON格式
        try:
            return json.dumps(asdict(log_entry), ensure_ascii=False, default=str)
        except Exception:
            # 如果JSON序列化失败，使用普通格式
            return super().format(record)


class HumanReadableFormatter(logging.Formatter):
    """人类可读的日志格式化器"""

    def __init__(self):
        super().__init__(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录"""
        formatted = super().format(record)

        # 添加额外数据
        if hasattr(record, 'extra_data') and record.extra_data:
            extra_str = json.dumps(record.extra_data, ensure_ascii=False)
            formatted += f" [EXTRA: {extra_str}]"

        return formatted


class LoggingService(ILoggingService):
    """日志服务实现类"""

    def __init__(self,
                 name: str = "web_rag",
                 level: LogLevel = LogLevel.INFO,
                 log_file_path: Optional[str] = None,
                 max_file_size_mb: int = 10,
                 backup_count: int = 5,
                 use_structured_logging: bool = False,
                 enable_console_output: bool = True):
        """初始化日志服务

        Args:
            name: 日志器名称
            level: 日志级别
            log_file_path: 日志文件路径
            max_file_size_mb: 日志文件最大大小（MB）
            backup_count: 备份文件数量
            use_structured_logging: 是否使用结构化日志（JSON格式）
            enable_console_output: 是否启用控制台输出
        """
        self.name = name
        self.use_structured_logging = use_structured_logging

        # 创建日志器
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.value))

        # 清除现有处理器
        self.logger.handlers.clear()

        # 选择格式化器
        if use_structured_logging:
            formatter = StructuredFormatter()
        else:
            formatter = HumanReadableFormatter()

        # 添加控制台处理器
        if enable_console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

        # 添加文件处理器
        if log_file_path:
            try:
                # 确保日志目录存在
                os.makedirs(os.path.dirname(log_file_path), exist_ok=True)

                # 创建轮转文件处理器
                file_handler = RotatingFileHandler(
                    log_file_path,
                    maxBytes=max_file_size_mb * 1024 * 1024,
                    backupCount=backup_count,
                    encoding='utf-8'
                )
                file_handler.setFormatter(formatter)
                self.logger.addHandler(file_handler)

            except Exception as e:
                # 如果文件处理器创建失败，记录到控制台
                self.logger.error(f"无法创建日志文件处理器: {e}")

    def _log_with_extra(self, level: int, message: str, extra: Optional[Dict[str, Any]] = None, exception: Optional[Exception] = None) -> None:
        """内部日志方法，支持额外数据"""
        if extra:
            # 创建额外的记录属性
            extra_record = {'extra_data': extra}
        else:
            extra_record = {}

        if exception:
            self.logger.log(level, message, exc_info=exception, extra=extra_record)
        else:
            self.logger.log(level, message, extra=extra_record)

    def debug(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """记录调试信息"""
        self._log_with_extra(logging.DEBUG, message, extra)

    def info(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """记录信息"""
        self._log_with_extra(logging.INFO, message, extra)

    def warning(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """记录警告"""
        self._log_with_extra(logging.WARNING, message, extra)

    def error(self, message: str, exception: Optional[Exception] = None, extra: Optional[Dict[str, Any]] = None) -> None:
        """记录错误"""
        self._log_with_extra(logging.ERROR, message, extra, exception)

    def critical(self, message: str, exception: Optional[Exception] = None, extra: Optional[Dict[str, Any]] = None) -> None:
        """记录严重错误"""
        self._log_with_extra(logging.CRITICAL, message, extra, exception)

    def set_level(self, level: LogLevel) -> None:
        """设置日志级别"""
        self.logger.setLevel(getattr(logging, level.value))

    def get_logger(self) -> logging.Logger:
        """获取底层的logging.Logger实例"""
        return self.logger


class PerformanceLogger:
    """性能监控日志器"""

    def __init__(self, logging_service: ILoggingService):
        """初始化性能日志器

        Args:
            logging_service: 日志服务实例
        """
        self.logging_service = logging_service

    def log_function_performance(self, func_name: str, execution_time: float, **kwargs) -> None:
        """记录函数执行性能

        Args:
            func_name: 函数名称
            execution_time: 执行时间（秒）
            **kwargs: 额外的性能数据
        """
        extra_data = {
            "performance_metric": True,
            "function_name": func_name,
            "execution_time_seconds": execution_time,
            **kwargs
        }

        if execution_time > 5.0:  # 超过5秒记录为警告
            self.logging_service.warning(
                f"函数 {func_name} 执行时间较长: {execution_time:.2f}秒",
                extra=extra_data
            )
        else:
            self.logging_service.info(
                f"函数 {func_name} 执行完成: {execution_time:.2f}秒",
                extra=extra_data
            )

    def log_api_request(self, method: str, url: str, response_time: float, status_code: int, **kwargs) -> None:
        """记录API请求性能

        Args:
            method: HTTP方法
            url: 请求URL
            response_time: 响应时间（秒）
            status_code: HTTP状态码
            **kwargs: 额外的请求数据
        """
        extra_data = {
            "api_metric": True,
            "method": method,
            "url": url,
            "response_time_seconds": response_time,
            "status_code": status_code,
            **kwargs
        }

        if status_code >= 400:
            self.logging_service.error(
                f"API请求失败: {method} {url} - {status_code}",
                extra=extra_data
            )
        elif response_time > 10.0:  # 超过10秒记录为警告
            self.logging_service.warning(
                f"API请求响应慢: {method} {url} - {response_time:.2f}秒",
                extra=extra_data
            )
        else:
            self.logging_service.info(
                f"API请求成功: {method} {url} - {response_time:.2f}秒",
                extra=extra_data
            )


def performance_monitor(logging_service: ILoggingService):
    """性能监控装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            import time
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time

                performance_logger = PerformanceLogger(logging_service)
                performance_logger.log_function_performance(
                    func_name=func.__name__,
                    execution_time=execution_time,
                    success=True
                )

                return result

            except Exception as e:
                execution_time = time.time() - start_time

                performance_logger = PerformanceLogger(logging_service)
                performance_logger.log_function_performance(
                    func_name=func.__name__,
                    execution_time=execution_time,
                    success=False,
                    error=str(e)
                )

                logging_service.error(
                    f"函数 {func.__name__} 执行失败",
                    exception=e,
                    extra={"execution_time": execution_time}
                )

                raise

        return wrapper
    return decorator


# 创建全局日志服务单例
_logging_service: Optional[LoggingService] = None


def get_logging_service() -> LoggingService:
    """获取日志服务单例"""
    global _logging_service
    if _logging_service is None:
        _logging_service = create_default_logging_service()
    return _logging_service


def create_default_logging_service() -> LoggingService:
    """创建默认日志服务"""
    return LoggingService(
        name="web_rag",
        level=LogLevel.INFO,
        log_file_path="./logs/app.log",
        use_structured_logging=False,
        enable_console_output=True
    )


def create_logging_service(config_service) -> LoggingService:
    """根据配置服务创建日志服务"""
    return LoggingService(
        name="web_rag",
        level=LogLevel(config_service.get_value("log_level", "INFO")),
        log_file_path=config_service.get_value("log_file_path"),
        max_file_size_mb=config_service.get_value("log_max_file_size_mb", 10),
        backup_count=config_service.get_value("log_backup_count", 5),
        use_structured_logging=config_service.get_environment().value == "production",
        enable_console_output=True
    )
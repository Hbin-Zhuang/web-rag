"""
通用工具服务
提供文件处理、格式化、错误处理等通用工具功能
集成到基础设施层，支持依赖注入
"""

import os
import hashlib
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
from functools import wraps

from ..logging.logging_service import ILoggingService


class IUtilityService:
    """工具服务抽象接口"""

    def validate_file_type(self, file_path: str, allowed_types: List[str]) -> bool:
        """验证文件类型"""
        pass

    def validate_file_size(self, file_path: str, max_size_mb: int) -> bool:
        """验证文件大小"""
        pass

    def calculate_file_hash(self, file_path: str) -> str:
        """计算文件哈希值"""
        pass

    def format_file_size(self, size_bytes: int) -> str:
        """格式化文件大小显示"""
        pass

    def safe_filename(self, filename: str) -> str:
        """生成安全的文件名"""
        pass

    def truncate_text(self, text: str, max_length: int = 100, suffix: str = "...") -> str:
        """截断文本并添加省略号"""
        pass

    def format_timestamp(self, timestamp: Optional[datetime] = None) -> str:
        """格式化时间戳"""
        pass

    def clean_text(self, text: str) -> str:
        """清理文本内容"""
        pass

    def split_into_batches(self, items: List[Any], batch_size: int) -> List[List[Any]]:
        """将列表分批处理"""
        pass


class UtilityService(IUtilityService):
    """工具服务实现类"""

    def __init__(self, logger: Optional[ILoggingService] = None):
        """初始化工具服务

        Args:
            logger: 日志服务实例
        """
        self._logger = logger

    def validate_file_type(self, file_path: str, allowed_types: List[str]) -> bool:
        """验证文件类型"""
        try:
            file_ext = os.path.splitext(file_path)[1].lower()
            is_valid = file_ext in allowed_types

            if self._logger:
                if is_valid:
                    self._logger.debug(f"文件类型验证通过: {file_path} -> {file_ext}")
                else:
                    self._logger.warning(f"文件类型验证失败: {file_path} -> {file_ext}, 允许类型: {allowed_types}")

            return is_valid
        except Exception as e:
            if self._logger:
                self._logger.error(f"文件类型验证异常: {file_path}", exception=e)
            return False

    def validate_file_size(self, file_path: str, max_size_mb: int) -> bool:
        """验证文件大小"""
        try:
            if not os.path.exists(file_path):
                if self._logger:
                    self._logger.warning(f"文件不存在: {file_path}")
                return False

            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            is_valid = file_size_mb <= max_size_mb

            if self._logger:
                if is_valid:
                    self._logger.debug(f"文件大小验证通过: {file_path} -> {file_size_mb:.2f}MB")
                else:
                    self._logger.warning(f"文件大小超过限制: {file_path} -> {file_size_mb:.2f}MB > {max_size_mb}MB")

            return is_valid
        except OSError as e:
            if self._logger:
                self._logger.error(f"文件大小验证失败: {file_path}", exception=e)
            return False

    def calculate_file_hash(self, file_path: str) -> str:
        """计算文件哈希值"""
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)

            file_hash = hash_md5.hexdigest()
            if self._logger:
                self._logger.debug(f"文件哈希计算完成: {file_path} -> {file_hash[:8]}...")

            return file_hash
        except Exception as e:
            if self._logger:
                self._logger.error(f"计算文件哈希失败: {file_path}", exception=e)
            return ""

    def format_file_size(self, size_bytes: int) -> str:
        """格式化文件大小显示"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024**2:
            return f"{size_bytes/1024:.1f} KB"
        elif size_bytes < 1024**3:
            return f"{size_bytes/(1024**2):.1f} MB"
        else:
            return f"{size_bytes/(1024**3):.1f} GB"

    def safe_filename(self, filename: str) -> str:
        """生成安全的文件名"""
        # 移除或替换不安全的字符
        unsafe_chars = '<>:"/\\|?*'
        safe_name = filename
        for char in unsafe_chars:
            safe_name = safe_name.replace(char, '_')

        # 移除首尾空格
        safe_name = safe_name.strip()

        # 确保不为空
        if not safe_name:
            safe_name = "untitled"

        if self._logger:
            if safe_name != filename:
                self._logger.debug(f"文件名安全化: '{filename}' -> '{safe_name}'")

        return safe_name

    def truncate_text(self, text: str, max_length: int = 100, suffix: str = "...") -> str:
        """截断文本并添加省略号"""
        if len(text) <= max_length:
            return text
        return text[:max_length-len(suffix)] + suffix

    def format_timestamp(self, timestamp: Optional[datetime] = None) -> str:
        """格式化时间戳"""
        if timestamp is None:
            timestamp = datetime.now()
        return timestamp.strftime("%Y-%m-%d %H:%M:%S")

    def clean_text(self, text: str) -> str:
        """清理文本内容"""
        # 移除多余的空白字符
        cleaned = ' '.join(text.split())
        # 移除首尾空格
        cleaned = cleaned.strip()
        return cleaned

    def split_into_batches(self, items: List[Any], batch_size: int) -> List[List[Any]]:
        """将列表分批处理"""
        if batch_size <= 0:
            raise ValueError("batch_size must be greater than 0")

        batches = []
        for i in range(0, len(items), batch_size):
            batches.append(items[i:i + batch_size])

        if self._logger:
            self._logger.debug(f"列表分批处理: {len(items)} 项 -> {len(batches)} 批，每批最多 {batch_size} 项")

        return batches

    def handle_error(self, func: Callable) -> Callable:
        """错误处理装饰器"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if self._logger:
                    self._logger.error(f"函数 {func.__name__} 执行失败", exception=e)
                return None
        return wrapper


class ProgressTracker:
    """进度跟踪器"""

    def __init__(self, total: int, description: str = "处理中", logger: Optional[ILoggingService] = None):
        """初始化进度跟踪器

        Args:
            total: 总项目数
            description: 处理描述
            logger: 日志服务实例
        """
        self.total = total
        self.current = 0
        self.description = description
        self.start_time = datetime.now()
        self._logger = logger

        if self._logger:
            self._logger.info(f"进度跟踪开始: {description}, 总数: {total}")

    def update(self, increment: int = 1):
        """更新进度"""
        self.current += increment
        if self.current > self.total:
            self.current = self.total

        if self._logger and self.current % max(1, self.total // 10) == 0:
            progress = self.get_progress()
            self._logger.info(f"进度更新: {progress['description']} - {progress['percentage']}%")

    def get_progress(self) -> Dict[str, Any]:
        """获取进度信息"""
        percentage = (self.current / self.total) * 100 if self.total > 0 else 0
        elapsed_time = datetime.now() - self.start_time

        return {
            "current": self.current,
            "total": self.total,
            "percentage": round(percentage, 1),
            "description": self.description,
            "elapsed_seconds": elapsed_time.total_seconds(),
            "is_complete": self.current >= self.total
        }


def get_utility_service() -> UtilityService:
    """获取工具服务实例"""
    # 这里可以集成到依赖注入容器中
    return UtilityService()
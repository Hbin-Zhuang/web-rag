"""
通用工具函数模块
提供文件处理、格式化、错误处理等辅助功能
"""

import os
import hashlib
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def validate_file_type(file_path: str, allowed_types: List[str]) -> bool:
    """验证文件类型"""
    file_ext = os.path.splitext(file_path)[1].lower()
    return file_ext in allowed_types

def validate_file_size(file_path: str, max_size_mb: int) -> bool:
    """验证文件大小"""
    try:
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        return file_size_mb <= max_size_mb
    except OSError:
        return False

def calculate_file_hash(file_path: str) -> str:
    """计算文件哈希值"""
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        logger.error(f"计算文件哈希失败: {e}")
        return ""

def format_file_size(size_bytes: int) -> str:
    """格式化文件大小显示"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024**2:
        return f"{size_bytes/1024:.1f} KB"
    elif size_bytes < 1024**3:
        return f"{size_bytes/(1024**2):.1f} MB"
    else:
        return f"{size_bytes/(1024**3):.1f} GB"

def safe_filename(filename: str) -> str:
    """生成安全的文件名"""
    # 移除或替换不安全的字符
    unsafe_chars = '<>:"/\\|?*'
    for char in unsafe_chars:
        filename = filename.replace(char, '_')
    return filename.strip()

def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """截断文本并添加省略号"""
    if len(text) <= max_length:
        return text
    return text[:max_length-len(suffix)] + suffix

def format_timestamp(timestamp: Optional[datetime] = None) -> str:
    """格式化时间戳"""
    if timestamp is None:
        timestamp = datetime.now()
    return timestamp.strftime("%Y-%m-%d %H:%M:%S")

def clean_text(text: str) -> str:
    """清理文本内容"""
    # 移除多余的空白字符
    text = ' '.join(text.split())
    # 移除特殊字符但保留基本标点
    # 这里可以根据需要添加更多清理规则
    return text.strip()

def split_into_batches(items: List[Any], batch_size: int) -> List[List[Any]]:
    """将列表分批处理"""
    batches = []
    for i in range(0, len(items), batch_size):
        batches.append(items[i:i + batch_size])
    return batches

def handle_error(func):
    """错误处理装饰器"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"函数 {func.__name__} 执行失败: {e}")
            return None
    return wrapper

class ProgressTracker:
    """进度跟踪器"""

    def __init__(self, total: int, description: str = "处理中"):
        self.total = total
        self.current = 0
        self.description = description
        self.start_time = datetime.now()

    def update(self, increment: int = 1):
        """更新进度"""
        self.current += increment
        if self.current > self.total:
            self.current = self.total

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
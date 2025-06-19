"""
外部服务抽象接口
为LLM、Embedding和VectorStore等外部依赖提供抽象层
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union, Tuple
from dataclasses import dataclass
from enum import Enum
import asyncio


class ModelStatus(Enum):
    """模型状态枚举"""
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    ERROR = "error"
    RATE_LIMITED = "rate_limited"


@dataclass
class ModelInfo:
    """模型信息"""
    name: str
    provider: str
    status: ModelStatus
    capabilities: List[str]
    context_length: Optional[int] = None
    cost_per_token: Optional[float] = None
    rate_limit: Optional[Dict[str, int]] = None


@dataclass
class ChatMessage:
    """聊天消息"""
    role: str  # "user", "assistant", "system"
    content: str
    timestamp: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ChatResponse:
    """聊天响应"""
    content: str
    model_used: str
    tokens_used: Optional[int] = None
    finish_reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class EmbeddingResult:
    """嵌入结果"""
    vectors: List[List[float]]
    model_used: str
    tokens_used: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class DocumentChunk:
    """文档块"""
    content: str
    metadata: Dict[str, Any]
    chunk_id: Optional[str] = None
    source: Optional[str] = None


@dataclass
class SearchResult:
    """搜索结果"""
    document: DocumentChunk
    score: float
    rank: int


class ILLMService(ABC):
    """大语言模型服务抽象接口"""

    @abstractmethod
    def get_available_models(self) -> List[ModelInfo]:
        """获取可用模型列表"""
        pass

    @abstractmethod
    def chat(self,
             messages: List[ChatMessage],
             model: Optional[str] = None,
             temperature: float = 0.7,
             max_tokens: Optional[int] = None,
             **kwargs) -> ChatResponse:
        """聊天对话"""
        pass

    @abstractmethod
    async def chat_async(self,
                         messages: List[ChatMessage],
                         model: Optional[str] = None,
                         temperature: float = 0.7,
                         max_tokens: Optional[int] = None,
                         **kwargs) -> ChatResponse:
        """异步聊天对话"""
        pass

    @abstractmethod
    def stream_chat(self,
                   messages: List[ChatMessage],
                   model: Optional[str] = None,
                   temperature: float = 0.7,
                   max_tokens: Optional[int] = None,
                   **kwargs):
        """流式聊天对话"""
        pass

    @abstractmethod
    def get_model_status(self, model: str) -> ModelStatus:
        """获取模型状态"""
        pass

    @abstractmethod
    def validate_connection(self) -> bool:
        """验证连接"""
        pass


class IEmbeddingService(ABC):
    """嵌入服务抽象接口"""

    @abstractmethod
    def get_available_models(self) -> List[ModelInfo]:
        """获取可用嵌入模型列表"""
        pass

    @abstractmethod
    def embed_texts(self,
                   texts: List[str],
                   model: Optional[str] = None,
                   **kwargs) -> EmbeddingResult:
        """文本嵌入"""
        pass

    @abstractmethod
    async def embed_texts_async(self,
                               texts: List[str],
                               model: Optional[str] = None,
                               **kwargs) -> EmbeddingResult:
        """异步文本嵌入"""
        pass

    @abstractmethod
    def embed_query(self,
                   query: str,
                   model: Optional[str] = None,
                   **kwargs) -> List[float]:
        """查询嵌入"""
        pass

    @abstractmethod
    def get_embedding_dimension(self, model: Optional[str] = None) -> int:
        """获取嵌入维度"""
        pass

    @abstractmethod
    def validate_connection(self) -> bool:
        """验证连接"""
        pass


class IVectorStoreService(ABC):
    """向量存储服务抽象接口"""

    @abstractmethod
    def create_collection(self,
                         name: str,
                         dimension: int,
                         metadata: Optional[Dict[str, Any]] = None) -> bool:
        """创建集合"""
        pass

    @abstractmethod
    def delete_collection(self, name: str) -> bool:
        """删除集合"""
        pass

    @abstractmethod
    def list_collections(self) -> List[str]:
        """列出所有集合"""
        pass

    @abstractmethod
    def add_documents(self,
                     collection_name: str,
                     documents: List[DocumentChunk],
                     embeddings: List[List[float]],
                     **kwargs) -> bool:
        """添加文档"""
        pass

    @abstractmethod
    def search(self,
              collection_name: str,
              query_embedding: List[float],
              top_k: int = 5,
              filter_conditions: Optional[Dict[str, Any]] = None,
              **kwargs) -> List[SearchResult]:
        """相似性搜索"""
        pass

    @abstractmethod
    def delete_documents(self,
                        collection_name: str,
                        document_ids: List[str]) -> bool:
        """删除文档"""
        pass

    @abstractmethod
    def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """获取集合统计信息"""
        pass

    @abstractmethod
    def validate_connection(self) -> bool:
        """验证连接"""
        pass


class IDocumentProcessorService(ABC):
    """文档处理服务抽象接口"""

    @abstractmethod
    def process_file(self,
                    file_path: str,
                    chunk_size: int = 1000,
                    chunk_overlap: int = 200,
                    **kwargs) -> List[DocumentChunk]:
        """处理文件并分块"""
        pass

    @abstractmethod
    def extract_text(self, file_path: str, **kwargs) -> str:
        """提取文本内容"""
        pass

    @abstractmethod
    def get_supported_formats(self) -> List[str]:
        """获取支持的文件格式"""
        pass

    @abstractmethod
    def validate_file(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """验证文件格式和大小"""
        pass


class IMemoryService(ABC):
    """内存服务抽象接口"""

    @abstractmethod
    def save_conversation(self,
                         conversation_id: str,
                         messages: List[ChatMessage]) -> bool:
        """保存对话"""
        pass

    @abstractmethod
    def load_conversation(self, conversation_id: str) -> List[ChatMessage]:
        """加载对话"""
        pass

    @abstractmethod
    def delete_conversation(self, conversation_id: str) -> bool:
        """删除对话"""
        pass

    @abstractmethod
    def list_conversations(self) -> List[Dict[str, Any]]:
        """列出所有对话"""
        pass

    @abstractmethod
    def cleanup_old_conversations(self, days: int = 30) -> int:
        """清理旧对话"""
        pass


class IRateLimiterService(ABC):
    """限流服务抽象接口"""

    @abstractmethod
    def check_rate_limit(self,
                        key: str,
                        limit: int,
                        window_seconds: int) -> Tuple[bool, int]:
        """检查限流状态

        Returns:
            Tuple[bool, int]: (是否允许请求, 剩余配额)
        """
        pass

    @abstractmethod
    def reset_rate_limit(self, key: str) -> bool:
        """重置限流"""
        pass

    @abstractmethod
    def get_rate_limit_info(self, key: str) -> Dict[str, Any]:
        """获取限流信息"""
        pass


class IHealthCheckService(ABC):
    """健康检查服务抽象接口"""

    @abstractmethod
    def check_service_health(self, service_name: str) -> Dict[str, Any]:
        """检查单个服务健康状态"""
        pass

    @abstractmethod
    def check_all_services_health(self) -> Dict[str, Dict[str, Any]]:
        """检查所有服务健康状态"""
        pass

    @abstractmethod
    def register_health_check(self,
                             service_name: str,
                             check_function: callable) -> bool:
        """注册健康检查"""
        pass


class IMetricsService(ABC):
    """指标服务抽象接口"""

    @abstractmethod
    def record_metric(self,
                     name: str,
                     value: float,
                     tags: Optional[Dict[str, str]] = None) -> None:
        """记录指标"""
        pass

    @abstractmethod
    def increment_counter(self,
                         name: str,
                         tags: Optional[Dict[str, str]] = None) -> None:
        """递增计数器"""
        pass

    @abstractmethod
    def record_histogram(self,
                        name: str,
                        value: float,
                        tags: Optional[Dict[str, str]] = None) -> None:
        """记录直方图"""
        pass

    @abstractmethod
    def get_metrics(self,
                   name_pattern: Optional[str] = None) -> Dict[str, Any]:
        """获取指标数据"""
        pass


# 异常类
class ExternalServiceException(Exception):
    """外部服务异常基类"""
    pass


class LLMServiceException(ExternalServiceException):
    """LLM服务异常"""
    pass


class EmbeddingServiceException(ExternalServiceException):
    """嵌入服务异常"""
    pass


class VectorStoreException(ExternalServiceException):
    """向量存储异常"""
    pass


class RateLimitException(ExternalServiceException):
    """限流异常"""
    pass


class HealthCheckException(ExternalServiceException):
    """健康检查异常"""
    pass
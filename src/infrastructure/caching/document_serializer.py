"""
文档序列化工具
解决Document对象的JSON序列化问题
"""

import json
from typing import List, Dict, Any, Optional
from langchain.schema import Document

from src.infrastructure import get_logger


class DocumentSerializer:
    """文档序列化器

    提供Document对象与JSON之间的安全转换
    """

    def __init__(self):
        self.logger = get_logger()

    def serialize_documents(self, documents: List[Document]) -> str:
        """序列化文档列表为JSON字符串

        Args:
            documents: Document对象列表

        Returns:
            JSON字符串
        """
        try:
            serializable_docs = []

            for doc in documents:
                serializable_doc = {
                    "page_content": doc.page_content,
                    "metadata": self._serialize_metadata(doc.metadata)
                }
                serializable_docs.append(serializable_doc)

            return json.dumps(serializable_docs, ensure_ascii=False, indent=None)

        except Exception as e:
            self.logger.error("文档序列化失败", exception=e)
            return "[]"

    def deserialize_documents(self, json_str: str) -> List[Document]:
        """从JSON字符串反序列化文档列表

        Args:
            json_str: JSON字符串

        Returns:
            Document对象列表
        """
        try:
            if not json_str:
                return []

            data = json.loads(json_str)
            documents = []

            for item in data:
                if isinstance(item, dict) and "page_content" in item:
                    doc = Document(
                        page_content=item["page_content"],
                        metadata=self._deserialize_metadata(item.get("metadata", {}))
                    )
                    documents.append(doc)

            return documents

        except Exception as e:
            self.logger.error("文档反序列化失败", exception=e)
            return []

    def serialize_documents_to_dict(self, documents: List[Document]) -> List[Dict[str, Any]]:
        """序列化文档列表为字典列表

        Args:
            documents: Document对象列表

        Returns:
            字典列表
        """
        try:
            serializable_docs = []

            for doc in documents:
                serializable_doc = {
                    "page_content": doc.page_content,
                    "metadata": self._serialize_metadata(doc.metadata)
                }
                serializable_docs.append(serializable_doc)

            return serializable_docs

        except Exception as e:
            self.logger.error("文档序列化为字典失败", exception=e)
            return []

    def deserialize_documents_from_dict(self, data: List[Dict[str, Any]]) -> List[Document]:
        """从字典列表反序列化文档列表

        Args:
            data: 字典列表

        Returns:
            Document对象列表
        """
        try:
            if not data:
                return []

            documents = []

            for item in data:
                if isinstance(item, dict) and "page_content" in item:
                    doc = Document(
                        page_content=item["page_content"],
                        metadata=self._deserialize_metadata(item.get("metadata", {}))
                    )
                    documents.append(doc)

            return documents

        except Exception as e:
            self.logger.error("从字典反序列化文档失败", exception=e)
            return []

    def _serialize_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """序列化元数据

        Args:
            metadata: 原始元数据

        Returns:
            可序列化的元数据
        """
        if not metadata:
            return {}

        serializable_metadata = {}

        for key, value in metadata.items():
            try:
                # 尝试JSON序列化以检查是否可序列化
                json.dumps(value)
                serializable_metadata[key] = value
            except (TypeError, ValueError):
                # 不可序列化的值转换为字符串
                serializable_metadata[key] = str(value)
                self.logger.debug(f"元数据键 '{key}' 的值不可序列化，已转换为字符串")

        return serializable_metadata

    def _deserialize_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """反序列化元数据

        Args:
            metadata: 序列化的元数据

        Returns:
            反序列化的元数据
        """
        if not metadata:
            return {}

        # 目前直接返回，后续可以添加特殊类型的反序列化逻辑
        return metadata

    def is_serializable(self, obj: Any) -> bool:
        """检查对象是否可JSON序列化

        Args:
            obj: 待检查的对象

        Returns:
            是否可序列化
        """
        try:
            json.dumps(obj)
            return True
        except (TypeError, ValueError):
            return False

    def safe_serialize(self, obj: Any) -> str:
        """安全序列化对象

        Args:
            obj: 待序列化的对象

        Returns:
            JSON字符串
        """
        try:
            if isinstance(obj, list) and obj and isinstance(obj[0], Document):
                # 如果是Document列表，使用专门的序列化方法
                return self.serialize_documents(obj)
            else:
                return json.dumps(obj, ensure_ascii=False, default=str)
        except Exception as e:
            self.logger.error("安全序列化失败", exception=e)
            return json.dumps(str(obj), ensure_ascii=False)

    def safe_deserialize(self, json_str: str, expected_type: Optional[type] = None) -> Any:
        """安全反序列化对象

        Args:
            json_str: JSON字符串
            expected_type: 期望的类型

        Returns:
            反序列化的对象
        """
        try:
            if not json_str:
                return None

            data = json.loads(json_str)

            # 如果期望类型是Document列表
            if expected_type == list and isinstance(data, list) and data:
                if isinstance(data[0], dict) and "page_content" in data[0]:
                    return self.deserialize_documents_from_dict(data)

            return data

        except Exception as e:
            self.logger.error("安全反序列化失败", exception=e)
            return None


# 全局序列化器实例
_serializer_instance: Optional[DocumentSerializer] = None


def get_document_serializer() -> DocumentSerializer:
    """获取文档序列化器单例实例"""
    global _serializer_instance

    if _serializer_instance is None:
        _serializer_instance = DocumentSerializer()

    return _serializer_instance


def serialize_documents(documents: List[Document]) -> str:
    """便捷函数：序列化文档列表"""
    return get_document_serializer().serialize_documents(documents)


def deserialize_documents(json_str: str) -> List[Document]:
    """便捷函数：反序列化文档列表"""
    return get_document_serializer().deserialize_documents(json_str)


def serialize_documents_to_dict(documents: List[Document]) -> List[Dict[str, Any]]:
    """便捷函数：序列化文档列表为字典"""
    return get_document_serializer().serialize_documents_to_dict(documents)


def deserialize_documents_from_dict(data: List[Dict[str, Any]]) -> List[Document]:
    """便捷函数：从字典反序列化文档列表"""
    return get_document_serializer().deserialize_documents_from_dict(data)

"""
语义文本分块器
基于句子边界和段落结构的智能分块，保持语义完整性
"""

import re
import nltk
from typing import List, Optional, Dict, Any
from langchain.text_splitter import TextSplitter
from langchain.schema import Document

# 确保NLTK数据下载
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)

try:
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    nltk.download('punkt_tab', quiet=True)


class SemanticTextSplitter(TextSplitter):
    """
    语义文本分块器

    基于以下策略进行智能分块：
    1. 优先保持段落完整性
    2. 在段落内基于句子边界分割
    3. 避免在句子中间切断
    4. 保持合理的分块大小
    """

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        min_chunk_size: int = 100,
        max_chunk_size: int = 2000,
        keep_separator: bool = True,
        **kwargs
    ):
        """
        初始化语义分块器

        Args:
            chunk_size: 目标分块大小（字符数）
            chunk_overlap: 分块重叠大小
            min_chunk_size: 最小分块大小
            max_chunk_size: 最大分块大小
            keep_separator: 是否保留分隔符
        """
        super().__init__(**kwargs)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.keep_separator = keep_separator

    def split_text(self, text: str) -> List[str]:
        """
        分割文本为语义连贯的片段

        Args:
            text: 待分割的文本

        Returns:
            分割后的文本片段列表
        """
        if not text.strip():
            return []

        # 步骤1：基于段落分割
        paragraphs = self._split_by_paragraphs(text)

        # 步骤2：处理每个段落
        chunks = []
        for paragraph in paragraphs:
            if len(paragraph.strip()) == 0:
                continue

            paragraph_chunks = self._process_paragraph(paragraph)
            chunks.extend(paragraph_chunks)

        # 步骤3：处理重叠
        final_chunks = self._add_overlap(chunks)

        # 步骤4：过滤过小的片段
        final_chunks = [chunk for chunk in final_chunks
                       if len(chunk.strip()) >= self.min_chunk_size]

        return final_chunks

    def _split_by_paragraphs(self, text: str) -> List[str]:
        """基于段落分割文本"""
        # 多种段落分隔符模式
        paragraph_patterns = [
            r'\n\s*\n',  # 双换行
            r'\r\n\s*\r\n',  # Windows双换行
            r'。\s*\n',  # 句号+换行
            r'！\s*\n',  # 感叹号+换行
            r'？\s*\n',  # 问号+换行
        ]

        # 使用正则表达式分割
        paragraphs = re.split('|'.join(paragraph_patterns), text)

        # 清理空段落
        paragraphs = [p.strip() for p in paragraphs if p.strip()]

        return paragraphs

    def _process_paragraph(self, paragraph: str) -> List[str]:
        """处理单个段落"""
        # 如果段落本身就很短，直接返回
        if len(paragraph) <= self.chunk_size:
            return [paragraph]

        # 基于句子分割段落
        sentences = self._split_by_sentences(paragraph)

        chunks = []
        current_chunk = ""

        for sentence in sentences:
            # 如果单个句子就超过最大长度，需要强制分割
            if len(sentence) > self.max_chunk_size:
                # 先处理当前积累的chunk
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""

                # 强制分割长句子
                long_sentence_chunks = self._force_split_long_sentence(sentence)
                chunks.extend(long_sentence_chunks)
                continue

            # 检查添加这个句子是否会超过目标大小
            potential_chunk = current_chunk + " " + sentence if current_chunk else sentence

            if len(potential_chunk) <= self.chunk_size:
                current_chunk = potential_chunk
            else:
                # 当前chunk已满，开始新chunk
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence

        # 处理最后的chunk
        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def _split_by_sentences(self, text: str) -> List[str]:
        """基于句子分割文本"""
        try:
            # 使用NLTK进行句子分割
            sentences = nltk.sent_tokenize(text, language='english')

            # 如果没有检测到句子边界，使用正则表达式备用方案
            if len(sentences) <= 1:
                sentences = self._regex_sentence_split(text)

        except Exception:
            # NLTK失败时的备用方案
            sentences = self._regex_sentence_split(text)

        return [s.strip() for s in sentences if s.strip()]

    def _regex_sentence_split(self, text: str) -> List[str]:
        """正则表达式句子分割（备用方案）"""
        # 中英文句子分割模式
        sentence_patterns = [
            r'[.!?]+\s+',  # 英文句号、感叹号、问号
            r'[。！？]+\s*',  # 中文句号、感叹号、问号
            r'[.:;]\s+',  # 冒号、分号（较弱的分割点）
        ]

        sentences = [text]  # 初始化为整个文本

        for pattern in sentence_patterns:
            new_sentences = []
            for sentence in sentences:
                # 分割并保留分隔符
                parts = re.split(f'({pattern})', sentence)

                current = ""
                for i, part in enumerate(parts):
                    if re.match(pattern, part):
                        # 这是分隔符，添加到当前句子并结束
                        current += part
                        if current.strip():
                            new_sentences.append(current.strip())
                        current = ""
                    else:
                        current += part

                # 添加剩余部分
                if current.strip():
                    new_sentences.append(current.strip())

            sentences = new_sentences

        return sentences

    def _force_split_long_sentence(self, sentence: str) -> List[str]:
        """强制分割过长的句子"""
        chunks = []
        words = sentence.split()
        current_chunk = ""

        for word in words:
            potential_chunk = current_chunk + " " + word if current_chunk else word

            if len(potential_chunk) <= self.chunk_size:
                current_chunk = potential_chunk
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = word

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def _add_overlap(self, chunks: List[str]) -> List[str]:
        """添加分块重叠"""
        if len(chunks) <= 1 or self.chunk_overlap <= 0:
            return chunks

        overlapped_chunks = [chunks[0]]  # 第一个chunk不需要重叠

        for i in range(1, len(chunks)):
            current_chunk = chunks[i]
            previous_chunk = chunks[i-1]

            # 从前一个chunk的末尾提取重叠内容
            overlap_text = self._extract_overlap(previous_chunk, self.chunk_overlap)

            if overlap_text:
                # 将重叠内容添加到当前chunk的开始
                overlapped_chunk = overlap_text + " " + current_chunk
            else:
                overlapped_chunk = current_chunk

            overlapped_chunks.append(overlapped_chunk)

        return overlapped_chunks

    def _extract_overlap(self, text: str, overlap_size: int) -> str:
        """从文本末尾提取指定大小的重叠内容"""
        if len(text) <= overlap_size:
            return text

        # 尝试在句子边界处提取重叠
        sentences = self._split_by_sentences(text)

        overlap_text = ""
        for sentence in reversed(sentences):
            potential_overlap = sentence + " " + overlap_text if overlap_text else sentence

            if len(potential_overlap) <= overlap_size:
                overlap_text = potential_overlap
            else:
                break

        # 如果基于句子的重叠太小，使用字符级重叠
        if len(overlap_text) < overlap_size // 2:
            overlap_text = text[-overlap_size:].strip()

        return overlap_text

    def split_documents(self, documents: List[Document]) -> List[Document]:
        """
        分割文档列表

        Args:
            documents: 待分割的文档列表

        Returns:
            分割后的文档列表
        """
        split_docs = []

        for doc in documents:
            chunks = self.split_text(doc.page_content)

            for i, chunk in enumerate(chunks):
                # 创建新的文档片段，保留原有元数据并添加分块信息
                chunk_metadata = doc.metadata.copy()
                chunk_metadata.update({
                    "chunk_index": i,
                    "chunk_total": len(chunks),
                    "splitter_type": "semantic",
                    "chunk_method": "sentence_boundary"
                })

                split_docs.append(Document(
                    page_content=chunk,
                    metadata=chunk_metadata
                ))

        return split_docs


class AdaptiveSemanticSplitter:
    """
    自适应语义分块器
    根据文档类型和内容特征选择最佳分块策略
    """

    def __init__(self, config=None):
        self.config = config
        self.semantic_splitter = SemanticTextSplitter(
            chunk_size=getattr(config, 'CHUNK_SIZE', 1000),
            chunk_overlap=getattr(config, 'CHUNK_OVERLAP', 200)
        )

        # 备用的传统分块器
        from langchain.text_splitter import RecursiveCharacterTextSplitter
        self.fallback_splitter = RecursiveCharacterTextSplitter(
            chunk_size=getattr(config, 'CHUNK_SIZE', 1000),
            chunk_overlap=getattr(config, 'CHUNK_OVERLAP', 200),
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )

    def split_documents(self, documents: List[Document], use_semantic: bool = True) -> List[Document]:
        """
        自适应文档分割

        Args:
            documents: 待分割的文档列表
            use_semantic: 是否使用语义分块

        Returns:
            分割后的文档列表
        """
        if not use_semantic:
            return self.fallback_splitter.split_documents(documents)

        try:
            # 尝试语义分块
            return self.semantic_splitter.split_documents(documents)
        except Exception as e:
            # 语义分块失败时回退到传统方法
            print(f"语义分块失败，回退到传统分块: {str(e)}")
            return self.fallback_splitter.split_documents(documents)
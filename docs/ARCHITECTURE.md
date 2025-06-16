# 系统架构设计

## 项目概述

基于 LangChain 和 Gemini 的轻量级 RAG 系统，支持本地 PDF 文档读取、Web UI 展示，并可部署到 Hugging Face Spaces。

## 技术架构

### 核心技术栈
- **框架**: LangChain (文档处理、检索链)
- **LLM**: Google Gemini (langchain-google-genai)
- **向量数据库**: ChromaDB (本地存储)
- **Web界面**: Gradio (HF Spaces 原生支持)
- **PDF处理**: PyPDFLoader + RecursiveCharacterTextSplitter
- **嵌入模型**: GoogleGenerativeAIEmbeddings

### 目录结构
```
web-rag/
├── app.py                    # Gradio Web UI 主程序
├── pdf_loader.py            # PDF 文档加载和分块处理
├── indexer.py               # 文档向量化和索引管理
├── retriever.py             # 语义检索和答案生成
├── memory.py                # 对话记忆和会话管理
├── config.py                # 系统配置和常量定义
├── utils.py                 # 通用工具函数
├── requirements.txt         # Python 依赖包列表
├── README.md                # 项目文档和部署说明
├── .env.example             # 环境变量示例文件
├── .gitignore               # Git 忽略规则
├── chroma_db/               # Chroma 向量数据库存储目录
├── images/                  # 项目截图和图片资源
└── docs/                    # 项目文档目录
    ├── ARCHITECTURE.md      # 技术架构和模块规范
    ├── CONFIGURATION.md     # 详细配置和性能调优指南
    └── DEVELOPMENT_LOG.md   # 开发进度和任务跟踪记录
```

## 模块设计

### 1. config.py - 配置管理
- 环境变量读取和验证
- 系统常量定义
- 开发/生产环境切换

### 2. pdf_loader.py - PDF处理
**类**: `PDFLoader`
- `load_pdf(file_path: str) -> List[Document]`
- `split_documents(documents: List[Document]) -> List[Document]`

### 3. indexer.py - 向量化索引
**类**: `DocumentIndexer`
- `create_embeddings(documents: List[Document]) -> VectorStore`
- `add_documents(documents: List[Document]) -> None`
- `get_vectorstore() -> Chroma`

### 4. retriever.py - 检索生成
**类**: `RAGRetriever`
- `retrieve_docs(query: str, k: int = 4) -> List[Document]`
- `generate_answer(query: str, chat_history: List) -> str`

### 5. memory.py - 对话记忆
**类**: `ConversationManager`
- `add_message(role: str, content: str) -> None`
- `get_history(limit: int = 10) -> List[Dict]`
- `clear_history() -> None`

### 6. app.py - Web界面
- PDF 文件上传组件
- 聊天界面（用户输入/AI回复）
- 文档处理状态显示
- 系统配置面板

## 数据流

```
1. 文档上传 → PDF解析 → 文本分块
2. 文本向量化 → 存储到向量数据库
3. 用户查询 → 查询向量化 → 相似性检索
4. 检索结果 + 对话历史 → Gemini生成回答
5. 回答返回 + 更新对话记忆
```

## API接口设计

### 模块间接口

#### PDFLoader接口
```python
class PDFLoader:
    def load_documents(self, file_path: str) -> List[Document]
    def validate_file(self, file) -> bool
    def get_file_stats(self, file_path: str) -> Dict[str, Any]
```

#### Indexer接口
```python
class DocumentIndexer:
    def create_vector_store(self, documents: List[Document]) -> Chroma
    def add_documents(self, documents: List[Document]) -> bool
    def get_vector_count(self) -> int
    def clear_index(self) -> bool
```

#### Retriever接口
```python
class RAGRetriever:
    def get_response(self, query: str, session_id: str) -> str
    def search_documents(self, query: str, k: int = 4) -> List[Document]
    def get_retrieval_chain(self) -> RetrievalQA
```

#### Memory接口
```python
class ConversationManager:
    def get_session_memory(self, session_id: str) -> ConversationBufferWindowMemory
    def add_message(self, session_id: str, role: str, content: str) -> None
    def clear_session(self, session_id: str) -> bool
    def get_active_sessions(self) -> List[str]
```

### 数据模型

#### Document结构
```python
@dataclass
class DocumentMetadata:
    source: str
    page: int
    chunk_id: str
    timestamp: datetime
    size: int
```

#### Session管理
```python
@dataclass
class SessionInfo:
    session_id: str
    created_at: datetime
    last_activity: datetime
    message_count: int
```

## 扩展点说明

### 1. 文档格式扩展
在`pdf_loader.py`中添加新的文档处理器：
```python
class DocumentLoader:
    def load_pdf(self, file_path: str) -> List[Document]
    def load_word(self, file_path: str) -> List[Document]  # 扩展点
    def load_markdown(self, file_path: str) -> List[Document]  # 扩展点
```

### 2. 向量存储扩展
可替换Chroma为其他向量数据库：
```python
# 当前实现
vectorstore = Chroma(...)

# 扩展示例
vectorstore = Pinecone(...)  # 云端向量数据库
vectorstore = FAISS(...)     # Facebook向量搜索
```

### 3. 模型扩展
支持其他LLM提供商：
```python
# 当前实现
llm = ChatGoogleGenerativeAI(...)

# 扩展示例
llm = ChatOpenAI(...)        # OpenAI GPT
llm = ChatAnthropic(...)     # Anthropic Claude
llm = ChatBedrock(...)       # AWS Bedrock
```

### 4. 界面扩展
Gradio组件的自定义和增强：
```python
# 当前界面组件
with gr.Tabs():
    with gr.TabItem("文档上传"):
        # 文件上传组件
    with gr.TabItem("智能问答"):
        # 聊天界面
    with gr.TabItem("系统状态"):
        # 状态监控

# 扩展示例
    with gr.TabItem("文档管理"):  # 新增功能
        # 文档列表、删除、重新索引
    with gr.TabItem("分析报告"):  # 新增功能
        # 使用统计、性能分析
```

### 5. 检索策略扩展
自定义检索和排序算法：
```python
class AdvancedRetriever(RAGRetriever):
    def hybrid_search(self, query: str) -> List[Document]:
        # 混合搜索：语义 + 关键词
        pass

    def rerank_results(self, docs: List[Document], query: str) -> List[Document]:
        # 结果重排序
        pass
```

## 性能考量

### 内存管理
- 文档分块策略优化
- 向量缓存机制
- 会话内存限制

### 响应时间优化
- 异步处理模式
- 批量向量化
- 索引预加载

### 扩展性设计
- 模块化架构
- 配置驱动的功能开关
- 插件化扩展机制

## 部署配置

### Hugging Face Spaces
```yaml
---
title: Web RAG System
emoji: 📚
colorFrom: blue
colorTo: green
sdk: gradio
sdk_version: 4.0.0
app_file: app.py
pinned: false
license: mit
---
```

### 环境变量
详细的配置参数和性能调优指南请参见 [CONFIGURATION.md](CONFIGURATION.md)

## 技术决策

### 为什么选择 Chroma？
- 零配置，文件存储
- 适合原型开发和演示
- 无需额外服务

### 为什么选择 Gradio？
- HF Spaces 原生支持
- ChatGPT 风格界面
- 快速开发迭代

### 为什么选择轻量化架构？
- 部署简单
- 开发速度快
- 调试友好
- 适合原型验证
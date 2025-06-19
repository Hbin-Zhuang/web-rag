# 系统架构设计 (v2.0 重构版)

## 项目概述

基于 LangChain 和 Gemini 的轻量级 RAG 系统，采用**分层架构设计**，大幅提升了可维护性和扩展性。支持本地 PDF 文档读取、Web UI 展示，并可部署到 Hugging Face Spaces。

## 架构重构升级 (v2.0)

### 重构目标
- ✅ **消除全局变量**: 从4个全局变量改为线程安全的状态管理
- ✅ **分离关注点**: UI层与业务逻辑完全解耦
- ✅ **服务化设计**: 按功能域拆分为专门的服务类
- ✅ **并发安全**: 支持多用户同时访问

### 技术架构

#### 核心技术栈
- **框架**: LangChain (文档处理、检索链)
- **LLM**: Google Gemini (langchain-google-genai)
- **向量数据库**: ChromaDB (本地存储)
- **Web界面**: Gradio (HF Spaces 原生支持)
- **PDF处理**: PyPDFLoader + RecursiveCharacterTextSplitter
- **嵌入模型**: GoogleGenerativeAIEmbeddings
- **架构模式**: 分层架构 + 服务模式 + 单例状态管理

### 分层架构设计

#### 架构层次
```
┌─────────────────────────────────────┐
│         表示层 (Presentation)        │
│         app.py - Gradio UI          │
├─────────────────────────────────────┤
│         应用层 (Application)         │
│    src/application/services/        │
│  ├─ DocumentService (文档处理)       │
│  ├─ ChatService (聊天问答)          │
│  └─ ModelService (模型管理)         │
├─────────────────────────────────────┤
│          共享层 (Shared)            │
│     src/shared/state/              │
│  └─ ApplicationState (状态管理)     │
├─────────────────────────────────────┤
│        基础设施层 (Infrastructure)   │
│  ├─ config.py (配置管理)            │
│  ├─ memory.py (记忆管理)            │
│  ├─ utils.py (工具函数)             │
│  ├─ indexer.py (索引器)             │
│  ├─ pdf_loader.py (PDF加载器)       │
│  └─ retriever.py (检索器)           │
└─────────────────────────────────────┘
```

#### 目录结构 (重构后)
```
web-rag/
├── app.py                       # Gradio Web UI 主程序 (重构版)
├── app_original_backup.py       # 原始版本备份
├── src/                         # 重构后的源代码目录
│   ├── __init__.py
│   ├── application/             # 应用服务层
│   │   ├── __init__.py
│   │   └── services/            # 核心业务服务
│   │       ├── __init__.py
│   │       ├── document_service.py    # 文档处理服务
│   │       ├── chat_service.py        # 聊天问答服务
│   │       └── model_service.py       # 模型管理服务
│   └── shared/                  # 共享模块
│       ├── __init__.py
│       └── state/               # 状态管理
│           ├── __init__.py
│           └── application_state.py   # 应用状态管理
├── pdf_loader.py               # PDF 文档加载和分块处理
├── indexer.py                  # 文档向量化和索引管理
├── retriever.py                # 语义检索和答案生成
├── memory.py                   # 对话记忆和会话管理
├── config.py                   # 系统配置和常量定义
├── utils.py                    # 通用工具函数
├── requirements.txt            # Python 依赖包列表
├── README.md                   # 项目文档和部署说明
├── .env.example                # 环境变量示例文件
├── .gitignore                  # Git 忽略规则
├── STAGE1_COMPLETION_REPORT.md # 阶段1重构报告
├── chroma_db/                  # Chroma 向量数据库存储目录
├── images/                     # 项目截图和图片资源
└── docs/                       # 项目文档目录
    ├── ARCHITECTURE.md         # 技术架构和模块规范
    ├── CONFIGURATION.md        # 详细配置和性能调优指南
    └── DEVELOPMENT_LOG.md      # 开发进度和任务跟踪记录
```

## 模块设计

### 重构后的服务层设计

#### 1. ApplicationState - 应用状态管理 (新增)
**文件**: `src/shared/state/application_state.py`

**功能**: 线程安全的全局状态管理，替代原本的全局变量
- 单例模式设计，确保状态一致性
- RLock 线程锁保护，支持并发访问
- 向量存储、QA链、模型配置统一管理
- 文件信息跟踪和状态变更时间戳

**主要接口**:
```python
class ApplicationState:
    @property
    def vectorstore(self) -> Optional[Any]
    @property
    def qa_chain(self) -> Optional[Any]
    @property
    def current_model(self) -> str

    def add_uploaded_file(self, file_info: FileInfo) -> None
    def get_state_info(self) -> Dict[str, Any]
    def reset_state(self) -> None
```

#### 2. DocumentService - 文档处理服务 (新增)
**文件**: `src/application/services/document_service.py`

**功能**: 封装PDF文档处理逻辑
- PDF处理和向量化
- 向量存储创建/更新
- 文件状态管理
- 系统状态获取

**主要接口**:
```python
class DocumentService:
    def process_pdf(self, file) -> str
    def process_pdf_and_update_status(self, file, selected_model: str) -> Tuple[str, str, str, str]
    def get_uploaded_files_count(self) -> int
    def clear_uploaded_files(self) -> None
```

#### 3. ChatService - 聊天服务 (新增)
**文件**: `src/application/services/chat_service.py`

**功能**: 封装聊天问答逻辑
- 聊天对话管理
- QA链创建和管理
- LLM模型创建
- 提示模板管理

**主要接口**:
```python
class ChatService:
    def chat_with_pdf(self, message: str, history: List[List[str]]) -> Tuple[str, List[List[str]]]
    def reset_qa_chain(self) -> None
    def is_ready(self) -> bool
    def get_conversation_history(self) -> List[dict]
```

#### 4. ModelService - 模型服务 (新增)
**文件**: `src/application/services/model_service.py`

**功能**: 封装AI模型管理逻辑
- 模型切换和验证
- 模型状态获取
- 模型兼容性检查
- 模型选择信息

**主要接口**:
```python
class ModelService:
    def switch_model(self, model_name: str) -> Tuple[bool, str]
    def get_model_status(self) -> str
    def validate_model_compatibility(self, model_name: str) -> Tuple[bool, str]
    def get_recommended_models(self) -> List[str]
```

### 基础设施层模块

#### 5. config.py - 配置管理
- 环境变量读取和验证
- 系统常量定义
- 开发/生产环境切换

#### 6. pdf_loader.py - PDF处理
**类**: `PDFLoader`
- `load_pdf(file_path: str) -> List[Document]`
- `split_documents(documents: List[Document]) -> List[Document]`

#### 7. indexer.py - 向量化索引
**类**: `DocumentIndexer`
- `create_embeddings(documents: List[Document]) -> VectorStore`
- `add_documents(documents: List[Document]) -> None`
- `get_vectorstore() -> Chroma`

#### 8. retriever.py - 检索生成
**类**: `RAGRetriever`
- `retrieve_docs(query: str, k: int = 4) -> List[Document]`
- `generate_answer(query: str, chat_history: List) -> str`

#### 9. memory.py - 对话记忆
**类**: `ConversationManager`
- `add_message(role: str, content: str) -> None`
- `get_history(limit: int = 10) -> List[Dict]`
- `clear_history() -> None`

### 表示层

#### 10. app.py - Web界面 (重构版)
- **重构改进**: 从642行减少到300行 (减少53%)
- **架构优化**: UI层与业务逻辑完全分离
- **事件处理**: 简化为服务调用包装器
- **组件**:
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
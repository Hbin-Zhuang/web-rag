# 系统架构设计 (v4.0 重构版)

## 项目概述

基于 LangChain 和 Gemini 的现代化 RAG 系统，采用**分层架构设计**，经过重构，实现了专业的可维护性、可扩展性和可靠性。支持多种文档格式（PDF、Word、Excel、PPT、Markdown、文本）处理、Web UI 展示，并可部署到 Hugging Face Spaces。

## 架构重构升级 (v4.0)

### 重构目标 (已完成)
- ✅ **消除全局变量**: 从4个全局变量改为线程安全的状态管理
- ✅ **分离关注点**: UI层与业务逻辑完全解耦
- ✅ **服务化设计**: 按功能域拆分为专门的服务类
- ✅ **并发安全**: 支持多用户同时访问
- ✅ **基础设施现代化**: 配置管理、日志服务、依赖注入
- ✅ **内存管理集成**: 会话持久化、现代化内存服务

### 技术架构

#### 核心技术栈
- **框架**: LangChain (文档处理、检索链)
- **LLM**: Google Gemini (langchain-google-genai)
- **向量数据库**: ChromaDB (本地存储)
- **Web界面**: Gradio (HF Spaces 原生支持)
- **文档处理**: Unstructured (多格式文档处理) + SemanticTextSplitter (语义分块) + RecursiveCharacterTextSplitter (传统分块备用)
- **嵌入模型**: GoogleGenerativeAIEmbeddings
- **架构模式**: 分层架构 + 服务模式 + 依赖注入 + 状态管理

### 分层架构设计 (v4.0)

#### 架构层次
```
┌─────────────────────────────────────────────┐
│              表示层 (Presentation)           │
│         app.py - Gradio UI                  │
│    src/presentation/controllers/            │
├─────────────────────────────────────────────┤
│              应用层 (Application)            │
│          src/application/services/          │
│  ├─ DocumentService (文档处理)               │
│  ├─ SemanticTextSplitter (语义分块)        │
│  ├─ ChatService (聊天问答)                  │
│  ├─ ModelService (模型管理)                 │
│  ├─ MemoryService (内存管理)                │
│  └─ LegacyMemoryAdapter (向后兼容)          │
├─────────────────────────────────────────────┤
│               共享层 (Shared)               │
│            src/shared/state/                │
│  └─ ApplicationState (状态管理)             │
├─────────────────────────────────────────────┤
│            基础设施层 (Infrastructure)       │
│          src/infrastructure/                │
│  ├─ config/ (配置管理)                     │
│  │   ├─ ConfigurationService               │
│  │   └─ ConfigMigrationAdapter             │
│  ├─ logging/ (日志服务)                    │
│  │   └─ LoggingService                     │
│  ├─ di/ (依赖注入)                         │
│  │   └─ DependencyContainer                │
│  ├─ utilities/ (工具服务)                  │
│  │   └─ UtilityService                     │
│  ├─ external/ (外部接口)                   │
│  │   └─ interfaces.py                      │
│  └─ factories/ (工厂模式)                  │
│      └─ InfrastructureFactory              │
└─────────────────────────────────────────────┘
```

#### 目录结构 (v4.0 完整版)
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
│   │       ├── document_service.py       # 文档处理服务
│   │       ├── semantic_text_splitter.py # 语义文本分块器
│   │       ├── chat_service.py           # 聊天问答服务
│   │       ├── model_service.py          # 模型管理服务
│   │       ├── memory_service.py         # 内存管理服务
│   │       └── legacy_memory_adapter.py  # 向后兼容适配器
│   ├── presentation/            # 表示层
│   │   ├── __init__.py
│   │   ├── components/          # UI组件
│   │   ├── controllers/         # UI控制器
│   │   └── handlers/            # 事件处理器
│   ├── shared/                  # 共享模块
│   │   ├── __init__.py
│   │   └── state/               # 状态管理
│   │       ├── __init__.py
│   │       └── application_state.py     # 应用状态管理
│   └── infrastructure/          # 基础设施层
│       ├── __init__.py
│       ├── config/              # 配置管理
│       │   ├── __init__.py
│       │   ├── configuration_service.py
│       │   └── config_migration_adapter.py
│       ├── logging/             # 日志服务
│       │   ├── __init__.py
│       │   └── logging_service.py
│       ├── di/                  # 依赖注入
│       │   ├── __init__.py
│       │   └── container.py
│       ├── utilities/           # 工具服务
│       │   ├── __init__.py
│       │   └── utility_service.py
│       ├── external/            # 外部接口
│       │   ├── __init__.py
│       │   └── interfaces.py
│       └── factories/           # 工厂模式
│           ├── __init__.py
│           └── infrastructure_factory.py
├── conversations/               # 会话持久化存储
├── uploads/                     # 上传文件临时目录
├── logs/                        # 日志文件目录
├── requirements.txt             # Python 依赖包列表
├── requirements-dev.txt         # 开发依赖
├── requirements_lock.txt        # 锁定版本依赖
├── README.md                    # 项目文档和部署说明
├── env.example                  # 环境变量示例文件
├── .gitignore                   # Git 忽略规则
├── runtime.txt                  # Python版本指定
├── activate_env.sh              # 环境激活脚本
├── images/                      # 项目截图和图片资源
└── docs/                        # 项目文档目录
    ├── README.md                # 文档导航
    ├── architecture/            # 架构文档
    │   ├── ARCHITECTURE.md      # 技术架构和模块规范
    │   ├── CONFIGURATION.md     # 详细配置和性能调优指南
    │   └── DEVELOPMENT_LOG.md   # 开发进度和任务跟踪记录
    └── refactor/                # 重构文档
        ├── STAGE1_COMPLETION_REPORT.md  # 阶段1重构报告
        ├── STAGE2_COMPLETION_REPORT.md  # 阶段2重构报告
        ├── STAGE3_COMPLETION_REPORT.md  # 阶段3重构报告
        ├── STAGE4_COMPLETION_REPORT.md  # 阶段4重构报告
        └── STAGE5_COMPLETION_REPORT.md  # 阶段5重构报告
```

## 模块设计 (v4.0)

### 应用服务层

#### 1. MemoryService - 内存管理服务 (新增)
**文件**: `src/application/services/memory_service.py`

**功能**: 现代化内存管理和会话持久化
- 实现IMemoryService接口规范
- 会话持久化存储（JSON文件后端）
- 当前会话管理和历史跟踪
- 对话上下文获取和格式化
- 会话生命周期管理（创建、保存、删除、清理）
- 支持依赖注入和现代化配置

**主要接口**:
```python
class MemoryService(IMemoryService):
    # IMemoryService接口实现
    def save_conversation(self, conversation_id: str, messages: List[ChatMessage]) -> bool
    def load_conversation(self, conversation_id: str) -> List[ChatMessage]
    def delete_conversation(self, conversation_id: str) -> bool
    def list_conversations(self) -> List[Dict[str, Any]]
    def cleanup_old_conversations(self, days: int = 30) -> int

    # 当前会话管理扩展
    def add_message_to_current_session(self, role: str, content: str, metadata: Dict[str, Any] = None) -> None
    def get_current_session_history(self, limit: int = None) -> List[ChatMessage]
    def get_current_session_context(self, include_messages: int = 5) -> str
    def reset_current_session(self) -> str
    def get_current_session_info(self) -> Dict[str, Any]
```

#### 2. LegacyMemoryAdapter - 向后兼容适配器 (新增)
**文件**: `src/application/services/legacy_memory_adapter.py`

**功能**: 完全兼容旧ConversationManager API
- 内部委托给新MemoryService实现
- 角色格式转换（human/ai ↔ user/assistant）
- 数据格式适配和接口桥接
- 新功能的直接委托访问

#### 3. DocumentService - 文档处理服务 (增强 + 语义分块)
**文件**: `src/application/services/document_service.py`

**功能**: 封装多种文档格式处理逻辑
- 多格式文档处理（PDF、Word、Excel、PPT、Markdown、文本）和向量化
- **智能语义分块**: 基于句子边界和段落结构的语义感知分割
- **自适应分块策略**: 根据文档特征自动选择最优分块方法
- **向后兼容性**: 保留传统RecursiveCharacterTextSplitter作为备用
- 向量存储创建/更新
- 文件状态管理
- 系统状态获取
- 集成新的基础设施服务

**语义分块特性**:
- `SemanticTextSplitter`: 核心语义分块算法，保持语义完整性
- `AdaptiveSemanticSplitter`: 自适应分块器，支持配置驱动和错误回退
- 智能重叠处理和长文本强制分割
- 运行时可配置的分块策略切换

#### 4. ChatService - 聊天服务 (增强)
**文件**: `src/application/services/chat_service.py`

**功能**: 封装聊天问答逻辑
- 集成新的MemoryService
- 增强RAG查询的对话上下文支持
- 定期自动保存会话
- QA链创建和管理
- LLM模型创建
- 提示模板管理

**主要接口**:
```python
class ChatService:
    def chat_with_pdf(self, message: str, history: List[List[str]]) -> Tuple[str, List[List[str]]]
    def reset_conversation_session(self) -> str
    def save_current_conversation(self) -> bool
    def get_conversation_summary(self) -> str
    def get_service_status(self) -> dict
```

#### 5. ModelService - 模型服务
**文件**: `src/application/services/model_service.py`

**功能**: 封装AI模型管理逻辑
- 模型切换和验证
- 模型状态获取
- 模型兼容性检查
- 模型选择信息

### 共享层

#### 6. ApplicationState - 应用状态管理 (增强)
**文件**: `src/shared/state/application_state.py`

**功能**: 线程安全的全局状态管理
- 延迟服务初始化机制
- 服务注册表和状态管理
- 统一的服务状态报告
- 资源清理和会话管理集成
- 线程安全的服务访问

**新增属性**:
```python
@property
def memory_service(self) -> MemoryService
def chat_service(self) -> ChatService
def document_service(self) -> DocumentService
```

### 基础设施层 (v4.0 完整版)

#### 7. ConfigurationService - 配置管理
**文件**: `src/infrastructure/config/configuration_service.py`

**功能**: 现代化配置管理
- 环境变量读取和验证
- 类型安全的配置项访问
- 配置验证和默认值
- 环境切换支持

#### 8. ConfigMigrationAdapter - 配置兼容适配器
**文件**: `src/infrastructure/config/config_migration_adapter.py`

**功能**: 向后兼容性保证
- 提供与旧Config类完全兼容的接口
- 内部委托给ConfigurationService
- 属性映射和方法兼容

#### 9. LoggingService - 日志服务
**文件**: `src/infrastructure/logging/logging_service.py`

**功能**: 结构化日志管理
- 多级别日志支持
- 结构化日志输出
- 性能监控和指标
- 日志轮转和管理

#### 10. UtilityService - 工具服务
**文件**: `src/infrastructure/utilities/utility_service.py`

**功能**: 通用工具函数集合
- 文件操作工具
- 格式化工具
- 文本处理工具
- 进度跟踪器

#### 11. DependencyContainer - 依赖注入容器
**文件**: `src/infrastructure/di/container.py`

**功能**: 依赖注入管理
- 服务生命周期管理
- 自动装配支持
- 作用域控制
- 服务解析

### 表示层

#### 12. app.py - Web界面 (重构版)
- **重构改进**: 从642行减少到178行 (减少72%)
- **架构优化**: UI层与业务逻辑完全分离
- **事件处理**: 简化为服务调用包装器
- **依赖注入**: 使用基础设施工厂模式

## 数据流

```
1. 文档上传 → PDF解析 → 文本分块
2. 文本向量化 → 存储到向量数据库
3. 用户查询 → 查询向量化 → 相似性检索
4. 检索结果 + 对话历史 → Gemini生成回答
5. 回答返回 + 更新对话记忆 + 会话持久化
```

## 核心特性 (v4.0)

### 🔧 现代化架构
- **分层架构**: 表示层、应用层、共享层、基础设施层
- **依赖注入**: 全面支持构造函数依赖注入
- **服务抽象**: 接口驱动设计，易于测试和扩展
- **状态管理**: 线程安全的统一状态管理

### 🧠 智能文档处理
- **语义分块**: 基于句子边界和段落结构的智能分割
- **自适应策略**: 根据文档特征自动选择最优分块方法
- **语义完整性**: 避免在句子中间切断，保持语义连贯
- **向后兼容**: 完全保留传统分块器功能

### 💾 持久化存储
- **会话持久化**: JSON文件存储会话历史
- **自动清理**: 定期清理过期会话
- **数据完整性**: 结构化数据格式和元数据

### 🔄 向后兼容
- **完全兼容**: 旧代码无需修改即可工作
- **渐进迁移**: 支持新旧API同时使用
- **透明代理**: 旧接口内部使用新服务实现

### 🚀 性能优化
- **延迟加载**: 服务按需初始化
- **内存缓存**: 当前会话保持在内存中
- **批量保存**: 定期批量持久化
- **结构化日志**: 高效的日志记录和查询

### 🛡️ 可靠性
- **错误处理**: 全面的异常捕获和恢复
- **健康检查**: 服务状态监控
- **资源管理**: 自动清理和内存优化
- **线程安全**: 多用户并发访问支持

## 扩展点说明

### 1. 服务扩展
添加新的应用服务：
```python
class NewService:
    def __init__(self, config_service=None, logger_service=None):
        # 标准依赖注入模式
        pass
```

### 2. 基础设施扩展
添加新的基础设施服务：
```python
class NewInfrastructureService(INewService):
    # 实现接口
    pass
```

### 3. 持久化后端扩展
替换存储后端：
```python
class DatabaseMemoryService(IMemoryService):
    # 数据库存储实现
    pass
```

### 4. 界面组件扩展
添加新的UI组件：
```python
# src/presentation/components/new_component.py
class NewComponent:
    def build(self):
        # Gradio组件实现
        pass
```

## 部署配置

### Hugging Face Spaces
```yaml
---
title: Web RAG System v4.0
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

## 重构历程

| 阶段 | 状态 | 重构内容 | 主要成果 |
|------|------|----------|----------|
| 阶段1 | ✅ 完成 | 核心服务抽取与状态管理重构 | 分层架构建立 |
| 阶段2 | ✅ 完成 | UI控制器分离与表示层重构 | 组件化UI架构 |
| 阶段3 | ✅ 完成 | 基础设施层抽象与依赖注入实现 | 现代化基础设施 |
| 阶段4 | ✅ 完成 | 配置和工具模块重组优化 | 统一配置管理 |
| 阶段5 | ✅ 完成 | 内存管理服务集成优化 | 会话持久化 |
| 阶段6 | ✅ 完成 | 目录结构最终整理与文档完善 | - |
| 阶段7 | ✅ 完成 | 性能优化与扩展性增强 | - |

**当前版本**: v4.0 (内存管理服务优化完成)

## 技术决策

### 为什么选择分层架构？
- 清晰的职责分离
- 便于测试和维护
- 支持独立演进
- 符合企业开发标准

### 为什么使用依赖注入？
- 降低模块耦合
- 便于单元测试
- 支持配置驱动
- 提高代码可维护性

### 为什么实现向后兼容？
- 平滑迁移路径
- 降低升级风险
- 保护已有投资
- 渐进式重构

### 为什么选择JSON存储？
- 轻量级，无需额外依赖
- 便于调试和查看
- 支持结构化数据
- 易于备份和迁移
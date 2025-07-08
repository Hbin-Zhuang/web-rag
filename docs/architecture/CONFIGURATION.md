# 系统配置指南

本文档详细介绍Web RAG系统的所有配置选项、环境变量和性能调优参数。

## 🔧 环境变量配置

### 必需配置

| 变量名 | 说明 | 示例值 |
|--------|------|--------|
| `GOOGLE_API_KEY` | Google Gemini API密钥 | `your_api_key_here` |

### 可选配置

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `EMBEDDING_MODEL` | `models/embedding-001` | 嵌入模型名称 |
| `CHAT_MODEL` | `gemini-2.5-flash-preview-05-20` | 聊天模型名称 |
| `CHUNK_SIZE` | `1000` | 文档分块大小（字符数）|
| `CHUNK_OVERLAP` | `200` | 文档分块重叠（字符数）|
| `USE_SEMANTIC_CHUNKING` | `true` | 是否启用语义分块 |
| `SEMANTIC_MIN_CHUNK_SIZE` | `100` | 语义分块最小大小（字符数）|
| `SEMANTIC_MAX_CHUNK_SIZE` | `2000` | 语义分块最大大小（字符数）|
| `FALLBACK_TO_TRADITIONAL` | `true` | 语义分块失败时是否回退到传统方法 |
| `SIMILARITY_TOP_K` | `4` | 检索返回的相关文档数量 |
| `MAX_TOKENS` | `1000` | 模型回复的最大token数 |
| `MAX_HISTORY_LENGTH` | `10` | 对话历史保留的消息数量 |
| `MAX_FILE_SIZE_MB` | `50` | 允许上传的最大文件大小（MB）|
| `ALLOWED_FILE_TYPES` | `[".pdf", ".docx", ".xlsx", ".pptx", ".txt", ".md"]` | 支持的文档格式列表 |
| `CHROMA_DB_PATH` | `./chroma_db` | 向量数据库存储路径 |

### LLM重排序配置

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `USE_RERANK` | `true` | 是否启用LLM重排序功能 |
| `RERANK_INITIAL_K` | `8` | 初始检索文档数量（扩大检索范围）|
| `RERANK_FINAL_K` | `4` | 最终返回文档数量 |
| `RERANK_SCORE_THRESHOLD` | `0.6` | 相关性评分阈值（0-1之间）|
| `RERANK_CACHE_TTL` | `3600` | 重排序结果缓存时间（秒）|
| `RERANK_TEMPERATURE` | `0.1` | 重排序LLM温度参数 |
| `RERANK_MAX_RETRIES` | `3` | 重排序失败重试次数 |

### 多样性检索配置

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `USE_DIVERSITY_RETRIEVAL` | `true` | 是否启用多样性感知检索 |
| `DIVERSITY_MAX_PER_SOURCE` | `3` | 每个文档源最多返回的片段数 |
| `DIVERSITY_MIN_SOURCES` | `2` | 最少文档源数量 |

### 文件名匹配配置

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `ENABLE_FILENAME_SEARCH` | `true` | 是否启用文件名搜索 |
| `FILENAME_SEARCH_WEIGHT` | `0.3` | 文件名匹配权重（0-1之间）|
| `SEMANTIC_SEARCH_WEIGHT` | `0.7` | 语义搜索权重（0-1之间）|
| `MIN_FILENAME_SCORE` | `0.2` | 文件名匹配最低分数阈值 |

### 开发调试配置

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `DEBUG` | `false` | 启用调试模式 |
| `LOG_LEVEL` | `INFO` | 日志级别 (DEBUG/INFO/WARNING/ERROR) |

## ⚙️ 配置文件设置

### 1. 本地开发配置

```bash
# 复制环境变量模板
cp .env_example .env

# 编辑配置文件
vim .env
```

**基本配置示例:**
```env
# 必需配置
GOOGLE_API_KEY=your_actual_api_key_here

# 性能优化配置
CHUNK_SIZE=800
CHUNK_OVERLAP=150
SIMILARITY_TOP_K=6
MAX_TOKENS=1500

# 语义分块配置
USE_SEMANTIC_CHUNKING=true
SEMANTIC_MIN_CHUNK_SIZE=100
SEMANTIC_MAX_CHUNK_SIZE=1800

# LLM重排序配置
USE_RERANK=true
RERANK_INITIAL_K=8
RERANK_FINAL_K=4

# 调试配置
DEBUG=true
LOG_LEVEL=DEBUG
```

### 2. 生产环境配置

**高性能配置示例:**
```env
GOOGLE_API_KEY=your_production_api_key

# 生产优化参数
CHUNK_SIZE=1200
CHUNK_OVERLAP=200
SIMILARITY_TOP_K=4
MAX_TOKENS=1000
MAX_HISTORY_LENGTH=15

# 语义分块生产配置
USE_SEMANTIC_CHUNKING=true
SEMANTIC_MIN_CHUNK_SIZE=150
SEMANTIC_MAX_CHUNK_SIZE=2000
FALLBACK_TO_TRADITIONAL=true

# LLM重排序生产配置
USE_RERANK=true
RERANK_INITIAL_K=8
RERANK_FINAL_K=4
RERANK_SCORE_THRESHOLD=0.6
USE_DIVERSITY_RETRIEVAL=true

# 生产环境设置
DEBUG=false
LOG_LEVEL=INFO
MAX_FILE_SIZE_MB=100
```

### 3. Hugging Face Spaces配置

在HF Spaces中通过Secrets设置：
- `GOOGLE_API_KEY`: 您的API密钥
- 其他配置可通过代码中的默认值处理

## 🚀 性能调优指南

### 文档处理优化

**大文档处理:**
```env
CHUNK_SIZE=1500
CHUNK_OVERLAP=300
MAX_FILE_SIZE_MB=200
```

**小文档处理:**
```env
CHUNK_SIZE=500
CHUNK_OVERLAP=100
SIMILARITY_TOP_K=6
USE_SEMANTIC_CHUNKING=true
SEMANTIC_MIN_CHUNK_SIZE=50
```

### 语义分块优化

**提高语义质量:**
```env
USE_SEMANTIC_CHUNKING=true
SEMANTIC_MIN_CHUNK_SIZE=100
SEMANTIC_MAX_CHUNK_SIZE=1500
FALLBACK_TO_TRADITIONAL=true
```

**传统分块（兼容模式）:**
```env
USE_SEMANTIC_CHUNKING=false
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
```

### 对话质量优化

**提高回答准确性:**
```env
SIMILARITY_TOP_K=6
MAX_TOKENS=1500
MAX_HISTORY_LENGTH=8
```

**提高响应速度:**
```env
SIMILARITY_TOP_K=3
MAX_TOKENS=800
MAX_HISTORY_LENGTH=5
```

### 内存使用优化

**低内存环境:**
```env
CHUNK_SIZE=600
SIMILARITY_TOP_K=3
MAX_HISTORY_LENGTH=5
MAX_FILE_SIZE_MB=20
```

**高内存环境:**
```env
CHUNK_SIZE=1500
SIMILARITY_TOP_K=8
MAX_HISTORY_LENGTH=20
MAX_FILE_SIZE_MB=200
```

## 📊 模型配置详解

### 支持的Gemini模型

| 模型名称 | 特点 | 适用场景 |
|----------|------|----------|
| `gemini-2.5-flash-preview-05-20` | 最新预览版，支持长上下文(100万tokens)，多模态能力强 | 复杂文档分析、长文本处理、多轮对话 |
| `gemini-2.0-flash` | 响应速度快，推理能力均衡，稳定性好 | 实时对话、快速问答、生产环境 |
| `gemini-2.0-flash-lite` | 轻量化设计，延迟极低，成本最优 | 简单查询、高频调用、资源受限环境 |

### 嵌入模型选择

| 模型名称 | 特点 | 语言支持 |
|----------|------|----------|
| `models/embedding-001` | 通用嵌入模型 | 多语言支持 |
| `models/text-embedding-004` | 最新版本，性能更好 | 多语言支持 |

## 🔍 配置验证

### 检查配置状态

启动应用后，在"系统状态"页面可以查看：
- API配置状态
- 模型连接状态
- 数据库配置
- 当前参数设置

### 常见配置问题

1. **API密钥错误**
   ```
   错误: 配置验证失败，请检查GOOGLE_API_KEY
   解决: 确认API密钥正确且有效
   ```

2. **模型不可用**
   ```
   错误: 语言模型初始化失败
   解决: 检查模型名称和API访问权限
   ```

3. **内存不足**
   ```
   错误: 文档处理失败
   解决: 降低CHUNK_SIZE或MAX_FILE_SIZE_MB
   ```

## 🛡️ 安全配置

### API密钥安全

- **本地开发**: 使用`.env`文件，确保文件不被提交到Git
- **生产部署**: 使用环境变量或密钥管理服务
- **HF Spaces**: 使用Secrets功能，避免硬编码

### 文件安全

```env
# 限制文件大小和类型
MAX_FILE_SIZE_MB=50
ALLOWED_FILE_TYPES=".pdf,.docx,.xlsx,.pptx,.txt,.md"
# 文档类型验证在代码中处理
```

### 访问控制

```env
# 日志级别控制
LOG_LEVEL=INFO  # 生产环境避免DEBUG级别

# 调试模式控制
DEBUG=false     # 生产环境必须关闭
```

## 📈 监控配置

### 日志配置

```python
# 在utils.py中的日志配置
LOG_LEVEL=DEBUG    # 详细调试信息
LOG_LEVEL=INFO     # 一般运行信息
LOG_LEVEL=WARNING  # 警告信息
LOG_LEVEL=ERROR    # 仅错误信息
```

### 性能监控

系统会自动记录：
- 文档处理时间
- API调用耗时
- 内存使用情况
- 错误率统计

---

**💡 提示**: 配置更改后需要重启应用才能生效。建议在测试环境中验证配置后再应用到生产环境。
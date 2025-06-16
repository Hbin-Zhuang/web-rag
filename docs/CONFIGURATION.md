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
| `CHAT_MODEL` | `gemini-2.0-flash-001` | 聊天模型名称 |
| `CHUNK_SIZE` | `1000` | 文档分块大小（字符数）|
| `CHUNK_OVERLAP` | `200` | 文档分块重叠（字符数）|
| `SIMILARITY_TOP_K` | `4` | 检索返回的相关文档数量 |
| `MAX_TOKENS` | `1000` | 模型回复的最大token数 |
| `MAX_HISTORY_LENGTH` | `10` | 对话历史保留的消息数量 |
| `MAX_FILE_SIZE_MB` | `50` | 允许上传的最大文件大小（MB）|
| `CHROMA_DB_PATH` | `./chroma_db` | 向量数据库存储路径 |

### 开发调试配置

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `DEBUG` | `false` | 启用调试模式 |
| `LOG_LEVEL` | `INFO` | 日志级别 (DEBUG/INFO/WARNING/ERROR) |

## ⚙️ 配置文件设置

### 1. 本地开发配置

```bash
# 复制环境变量模板
cp env_example.txt .env

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
| `gemini-2.0-flash-001` | 快速响应，成本较低 | 一般问答、原型开发 |
| `gemini-1.5-pro-latest` | 高质量输出，推理能力强 | 复杂分析、生产环境 |
| `gemini-1.5-flash-latest` | 平衡性能和质量 | 大多数应用场景 |

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
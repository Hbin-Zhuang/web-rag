# 🚀 Hugging Face Spaces 部署指南

本文档提供详细的 Web RAG 系统部署到 Hugging Face Spaces 的完整指南。

## 📋 部署前准备

### 1. 环境要求
- ✅ GitHub 账户（用于代码仓库）
- ✅ Hugging Face 账户（用于创建 Space）
- ✅ Google API Key（用于 Gemini 模型）

### 2. 项目准备
确认项目包含以下必要文件：
- ✅ `README.md` - 包含 HF Spaces 元数据配置
- ✅ `app.py` - 主应用文件，已适配 HF Spaces 环境
- ✅ `requirements.txt` - Python 依赖清单
- ✅ `runtime.txt` - Python 版本声明
- ✅ `env.example` - 环境变量配置模板

## 🎯 部署方式选择

### 方式 1: GitHub 集成部署（推荐）

**优点**：
- 🔄 自动同步代码更新
- 📊 版本控制和历史记录
- 🚀 CI/CD 集成
- 🔒 安全的 Secrets 管理

**适用场景**：
- 团队协作项目
- 需要持续更新的应用
- 希望保持代码和部署同步

### 方式 2: 直接文件上传

**优点**：
- 🚀 快速部署
- 🎯 简单直接
- 📦 无需外部依赖

**适用场景**：
- 快速原型验证
- 一次性演示
- 私有项目部署

## 📖 详细部署步骤

### 方式 1: GitHub 集成部署

#### 步骤 1: 准备 GitHub 仓库
```bash
# 确保代码已推送到 GitHub
git add .
git commit -m "准备 HF Spaces 部署"
git push origin main
```

#### 步骤 2: 创建 Hugging Face Space
1. 访问 [Hugging Face Spaces](https://huggingface.co/new-space)
2. 填写 Space 信息：
   - **Space name**: `web-rag-system` (或您喜欢的名称)
   - **License**: `MIT`
   - **SDK**: `Gradio`
   - **Visibility**: `Public` (推荐) 或 `Private`
3. 选择 **"Connect to GitHub repository"**
4. 授权 Hugging Face 访问您的 GitHub 账户
5. 选择您的 `web-rag` 仓库
6. 点击 **"Create Space"**

#### 步骤 3: 配置环境变量
1. 进入您的 Space 页面
2. 点击 **"Settings"** 标签
3. 滚动到 **"Repository secrets"** 部分
4. 添加以下 Secret：
   - **Name**: `GOOGLE_API_KEY`
   - **Value**: 您的 Google Gemini API Key
5. 点击 **"Add secret"**

#### 步骤 4: 等待部署完成
- HF Spaces 会自动检测 `app.py` 并开始构建
- 构建过程通常需要 3-5 分钟
- 可以在 **"Logs"** 标签查看构建进度

#### 步骤 5: 验证部署
1. 构建完成后，Space 会自动启动
2. 您将看到应用界面
3. 测试文档上传和问答功能

### 方式 2: 直接文件上传

#### 步骤 1: 创建新 Space
1. 访问 [Hugging Face Spaces](https://huggingface.co/new-space)
2. 填写基本信息（同上）
3. 选择 **"Create Space"**

#### 步骤 2: 上传项目文件
1. 在 Space 页面点击 **"Files"** 标签
2. 依次上传以下文件：
   ```
   app.py
   requirements.txt
   runtime.txt
   config.py
   memory.py
   utils.py
   indexer.py
   pdf_loader.py
   retriever.py
   ```

#### 步骤 3: 更新 README.md
在 Space 的文件编辑器中，确保 `README.md` 包含正确的元数据：
```yaml
---
title: Web RAG System
emoji: 📚
colorFrom: blue
colorTo: green
sdk: gradio
sdk_version: 4.44.0
app_file: app.py
pinned: false
license: mit
short_description: 基于 LangChain 和 Gemini 的轻量级 RAG 系统
---
```

#### 步骤 4: 配置 Secrets
按照方式 1 的步骤 3 配置环境变量。

## 🔧 部署后配置

### 1. 自定义域名（可选）
如果您有 Pro 账户，可以配置自定义域名：
1. 在 Space Settings 中找到 **"Custom domain"**
2. 输入您的域名
3. 按照提示配置 DNS 记录

### 2. 性能优化
根据使用情况调整硬件配置：
- **CPU Basic**: 免费，适合轻量使用
- **CPU Upgrade**: 付费，更好性能
- **GPU**: 如需加速推理（本项目暂不需要）

### 3. 访问控制（可选）
如果需要限制访问：
1. 在 Settings 中设置 **"Visibility"** 为 Private
2. 或配置 **"Access token"** 进行认证

## 📍 获取访问地址

部署成功后，您的应用访问地址格式为：
```
https://huggingface.co/spaces/[您的用户名]/[Space名称]
```

例如：
```
https://huggingface.co/spaces/username/web-rag-system
```

## 🐛 常见问题排除

### 1. 构建失败
**症状**: Space 显示构建错误
**解决方案**:
- 检查 `requirements.txt` 中的依赖版本
- 查看 Logs 标签中的错误信息
- 确认 `app.py` 语法正确

### 2. API Key 错误
**症状**: 应用启动但无法使用 Gemini 功能
**解决方案**:
- 确认 `GOOGLE_API_KEY` 已正确添加到 Secrets
- 验证 API Key 格式（应以 `AIza` 开头）
- 检查 API Key 是否有效且有配额

### 3. 内存不足
**症状**: 应用运行时崩溃或响应缓慢
**解决方案**:
- 升级到 CPU Upgrade 硬件
- 优化代码中的内存使用
- 减少文档处理的批次大小

### 4. 网络超时
**症状**: 文档处理或问答时超时
**解决方案**:
- 检查网络连接
- 增加超时时间配置
- 使用更快的 Gemini 模型

## 🔄 更新部署

### GitHub 集成方式
代码更新会自动同步到 Space：
```bash
git add .
git commit -m "更新功能"
git push origin main
```

### 直接上传方式
需要手动重新上传修改的文件。

## 📊 监控和分析

### 1. 使用统计
在 Space 页面可以查看：
- 访问量统计
- 用户交互数据
- 性能指标

### 2. 日志查看
在 **"Logs"** 标签可以查看：
- 应用运行日志
- 错误信息
- 性能数据

## 🎉 部署完成

恭喜！您的 Web RAG 系统已成功部署到 Hugging Face Spaces。

**下一步建议**：
1. 📢 分享您的 Space 链接
2. 📝 收集用户反馈
3. 🔧 根据使用情况优化性能
4. 📈 监控使用统计和性能指标

---

## 📞 技术支持

如果在部署过程中遇到问题：
1. 查看 [Hugging Face Spaces 文档](https://huggingface.co/docs/hub/spaces)
2. 检查项目的 GitHub Issues
3. 参考本文档的故障排除部分
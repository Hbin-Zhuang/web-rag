# 📚 项目文档目录

本目录包含Web RAG系统的完整技术文档，按内容类型分类组织。

## 📁 目录结构

### 🏗️ architecture/ - 架构与配置文档
包含系统架构设计、技术规范、配置指南等核心技术文档。

- **[ARCHITECTURE.md](architecture/ARCHITECTURE.md)** - 系统架构设计文档
  - 分层架构设计 (v2.0 重构版)
  - 模块接口规范
  - 技术栈说明
  - 扩展点设计

- **[CONFIGURATION.md](architecture/CONFIGURATION.md)** - 配置管理指南
  - 环境变量配置
  - 性能调优参数
  - 部署配置选项
  - 开发环境设置

- **[DEVELOPMENT_LOG.md](architecture/DEVELOPMENT_LOG.md)** - 开发进度日志
  - 项目开发历程
  - 重构阶段记录
  - 版本更新说明
  - 任务跟踪记录

### 🔄 refactor/ - 重构专项文档
包含架构重构过程的详细记录、阶段报告、技术决策等。

- **[STAGE1_COMPLETION_REPORT.md](refactor/STAGE1_COMPLETION_REPORT.md)** - 阶段1重构报告
  - 核心服务抽取与状态管理重构
  - 分层架构建立
  - 代码质量改进
  - 验证结果和性能指标

## 📖 文档导航

### 🚀 快速开始
如果你是新用户，建议按以下顺序阅读：
1. 📋 [主README](../README.md) - 项目概述和快速开始
2. 🏗️ [ARCHITECTURE.md](architecture/ARCHITECTURE.md) - 了解系统架构
3. ⚙️ [CONFIGURATION.md](architecture/CONFIGURATION.md) - 配置和部署

### 🔧 开发者指南
如果你要参与开发，推荐阅读：
1. 🏗️ [ARCHITECTURE.md](architecture/ARCHITECTURE.md) - 技术架构详解
2. 📋 [DEVELOPMENT_LOG.md](architecture/DEVELOPMENT_LOG.md) - 开发进度和规划
3. 🔄 [重构报告](refactor/) - 了解重构历程和设计决策

### 📊 重构历程
如果你想了解重构过程：
1. 🔄 [STAGE1_COMPLETION_REPORT.md](refactor/STAGE1_COMPLETION_REPORT.md) - 阶段1重构详情
2. 📋 [DEVELOPMENT_LOG.md](architecture/DEVELOPMENT_LOG.md) - 完整开发日志

## 🔄 重构阶段概览

本项目正在进行**7阶段架构重构**，从单体应用升级为分层架构：

| 阶段 | 状态 | 重构内容 | 文档 |
|------|------|----------|------|
| 阶段1 | ✅ 已完成 | 核心服务抽取与状态管理重构 | [报告](refactor/STAGE1_COMPLETION_REPORT.md) |
| 阶段2 | 🔄 规划中 | UI控制器分离与表示层重构 | - |
| 阶段3 | 📋 待开始 | 基础设施层抽象与依赖注入实现 | - |
| 阶段4 | 📋 待开始 | 配置和工具模块重组优化 | - |
| 阶段5 | 📋 待开始 | 内存管理服务集成优化 | - |
| 阶段6 | 📋 待开始 | 目录结构最终整理与文档完善 | - |
| 阶段7 | 📋 待开始 | 性能优化与扩展性增强 | - |

## 📝 文档维护

- **更新频率**: 每完成一个重构阶段更新一次
- **维护原则**: 保持文档与代码同步，记录重要技术决策
- **版本控制**: 重要变更通过git commit记录

---

**💡 提示**: 如果在阅读过程中发现文档不清楚或有遗漏，欢迎提出改进建议！
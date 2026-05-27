# AI Chat 项目介绍

AI Chat 是一个基于 FastAPI 的本地 AI 工作台，提供多供应商模型调用、工具执行、MCP 协议、RAG 检索等能力。

## 核心功能

### 多模型支持

AI Chat 支持多种 LLM 供应商，包括 OpenAI、Anthropic、Google、Ollama 等。通过统一的模型接口，用户可以在不同供应商之间无缝切换，无需修改应用代码。

模型配置存储在数据库中，支持动态增删。API Key 使用 Fernet 加密保存，确保密钥安全。系统还内置了 token 计数和费用计算功能，帮助用户监控使用成本。

### RAG 检索增强

RAG（Retrieval-Augmented Generation）模块提供本地文档索引和语义检索能力。用户可以将文档目录索引到向量数据库，在聊天时自动检索相关内容注入上下文。

RAG 管线包含文件加载、文本切割、向量嵌入和相似度检索四个阶段。文件加载支持 TXT、Markdown、PDF、DOCX、图片等多种格式，通过 Unstructured 和 RapidOCR 实现高质量内容提取。

### 工具系统

工具系统采用 Registry + Handler 模式，所有工具统一注册到 ToolRegistry。内置工具包括网页搜索、代码执行、文件操作等。MCP 协议支持与外部工具服务通信，扩展系统能力边界。

## 技术架构

### 分层设计

项目采用严格的分层架构：API 层负责 HTTP 入口，Service 层协调业务逻辑，Core 层提供核心能力，Storage 层管理数据持久化。依赖方向严格控制，禁止跨层直接调用。

### 模块结构

核心模块包括模型子系统、工具子系统、提示词管理、记忆管理和 RAG 管线。每个子系统遵循 Registry + Strategy 模式，通过注册表路由到具体实现策略。

## 开发指南

### 环境搭建

项目使用 uv 管理依赖，Python >= 3.13。克隆仓库后运行 `uv sync` 安装依赖，配置 `.env` 文件设置基本参数，运行 `uv run python main.py` 启动服务。

### 编码规范

所有自定义异常必须继承 BaseExceptions。配置统一通过 config/settings.py 管理，禁止业务代码直接调用 os.getenv()。API 路由只做参数校验，业务逻辑放在 service 层。

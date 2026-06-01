# AI Chat

基于 LangChain 生态的多提供商 AI 工作台，提供 CLI 和 FastAPI 双入口。

## 功能特性

- **多 LLM 提供商** — 支持 OpenAI、Anthropic Claude、Google Gemini、Ollama（本地）、Minimax、阿里通义千问
- **智能代理** — 基于 LangGraph 的 ReAct 代理，支持工具调用和上下文自动管理
- **RAG 检索增强生成** — 多格式文档加载、多种文本分块策略、ChromaDB 向量存储、检索问答
- **对话记忆** — 文件持久化、自动记忆提取与摘要、语义搜索、会话管理
- **上下文管理** — 自动组装系统提示、记忆注入、工具描述，支持压缩策略
- **MCP 集成** — 连接外部 MCP 工具服务器，或将内置工具暴露为 MCP 服务
- **技能系统** — 基于 Markdown 的插件式斜杠命令，支持自定义系统提示词和工具绑定
- **定时任务** — 基于 cron 表达式的任务调度，支持一次性任务和循环任务
- **内置工具** — 文件操作、目录管理、内容搜索、Shell 命令、Web 请求、待办管理、计划管理等
- **API Key 加密** — Fernet 对称加密保护敏感凭证，数据库中不存明文
- **TUI 控制台** — Rich 终端仪表盘，可视化管理会话

## 快速开始

### 环境要求

- Python >= 3.13
- [uv](https://docs.astral.sh/uv/) 包管理器

### 安装

```bash
git clone https://github.com/mhwssad/ai-chat
cd ai-chat
uv sync
```

### 配置

在项目根目录创建 `.env` 文件，填入需要的 API Key：

```env
# Chat 模型
CHAT_MODEL_MODEL_KEY=gpt-4o
CHAT_MODEL_API_KEY=sk-xxx

# Embedding 模型（RAG 使用）
EMBEDDING_MODEL_MODEL_KEY=text-embedding-3-small

# LLM 提供商（按需配置）
ANTHROPIC_API_KEY=sk-ant-xxx
GOOGLE_API_KEY=xxx
QWEN_API_KEY=sk-xxx
MINMAX_API_KEY=sk-cp-xxx
OLLAMA_BASE_URL=http://localhost:11434

# API Key 加密密钥（通过 ai-chat generate-key 生成）
ENCRYPTION_KEY=

# MCP（可选）
MCP_ENABLED=true
```

### 运行

```bash
# CLI — 启动 FastAPI 服务
uv run python main.py serve --reload

# CLI — 交互式对话（记忆 + 工具调用）
uv run python main.py chat

# CLI — Agent 模式（自主任务执行）
uv run python main.py agent "分析项目结构并生成文档"

# CLI — TUI 控制台仪表盘
uv run python main.py dashboard

# CLI — 生成加密密钥
uv run python main.py generate-key
```

#### 管理子命令

```bash
# 工具管理
uv run python main.py manage tools list

# 记忆管理
uv run python main.py manage memory list

# 定时任务管理
uv run python main.py manage scheduler list

# 对话管理
uv run python main.py manage chat list
```

#### CLI 对话内置命令

进入 `chat` 模式后，支持以下斜杠命令：

```text
/help              显示帮助
/quit              退出对话
/memory            查看记忆列表
/memory search Q   搜索记忆
/memory rebuild    重建记忆索引
/skills            列出可用技能
/stats             显示统计
/clear             清空当前会话
```

同时支持技能斜杠命令，如 `/translate`、`/summarize`、`/code-review`。

## 项目结构

```text
src/ai/
├── api/            # FastAPI 应用（路由、schema、服务）
├── cli/            # CLI 入口（Typer + Rich TUI）
│   ├── commands/     # 管理子命令（tools/memory/scheduler/chat）
│   ├── tabs/         # TUI 选项卡
│   ├── utils/        # 格式化、主题
│   └── widgets/      # TUI 组件（确认框、输入框、状态栏）
├── config/         # 配置管理（pydantic-settings）
├── core/
│   ├── agent/        # Agent 编排器（ReAct 循环、状态管理）
│   ├── callbacks/    # LLM 回调（审计日志）
│   ├── context/      # 上下文组装（收集器 + 压缩策略）
│   │   ├── collectors/  # 系统/用户/记忆/RAG/工具上下文收集
│   │   └── strategies/  # 压缩策略
│   ├── mcp/          # MCP 客户端 + 服务端
│   ├── memory/       # 对话记忆（提取、搜索、持久化）
│   ├── models/       # LLM 提供商抽象层（注册表 + DI 容器）
│   ├── prompts/      # 提示词模板（Jinja2 渲染 + 数据库存储）
│   ├── rag/          # RAG 管线
│   │   ├── loaders/    # 文档加载器（文本/OCR/Unstructured/链式加载）
│   │   └── splitters/  # 文本分块器（递归/Markdown/代码/Token）
│   ├── scheduler/    # 定时任务调度器（cron + 一次性任务）
│   ├── skills/       # 技能插件系统（加载/匹配/渲染/解析）
│   └── tools/        # 工具注册中心 + 内置工具
│       └── builtins/   # 文件/搜索/Shell/Web/计划/待办等工具
├── exception/      # 分层异常体系
├── security/       # 安全模块（API Key 加密）
├── storage/        # SQLModel 存储层（数据库/仓库）
└── utils/          # 工具函数（缓存/Token 计算/哈希/脱敏/HTTP 客户端）
    └── http/         # HTTP 客户端（含请求转换器）
```

## 支持的 LLM 提供商

| 提供商    | 聊天模型    | Embedding              |
| --------- | ----------- | ---------------------- |
| OpenAI    | GPT-4o 等   | text-embedding-3-small |
| Anthropic | Claude 系列 | -                      |
| Google    | Gemini 系列 | -                      |
| Ollama    | 本地模型    | nomic-embed-text       |
| Minimax   | M2.7        | -                      |
| 通义千问  | Qwen 系列   | -                      |

## 内置工具

| 分类     | 工具                                                           |
| -------- | -------------------------------------------------------------- |
| 文件     | 读取、按行读取、覆盖写入、追加写入、精确替换、正则替换         |
| 目录     | 列出目录、查看路径信息、创建目录、按 glob 查找文件             |
| 搜索     | 在项目目录内按文本搜索文件内容                                 |
| Shell    | 通过白名单执行只读 PowerShell 查询命令                         |
| Web      | HTTP GET/POST 请求                                             |
| 交互     | 用户确认、用户输入提示                                         |
| 笔记     | 笔记本读写操作                                                 |
| 计划     | 任务计划创建与管理                                             |
| 待办     | 待办事项管理                                                   |
| 调度     | 定时任务创建与管理                                             |
| 工作树   | 工作树信息查询                                                 |

说明：

- 所有内置工具默认限制在项目根目录及其子目录内运行
- `shell` 工具仅用于只读查询，不是通用 shell

## 上下文管理

上下文系统自动为每次对话组装完整的提示：

- **收集器** — 系统指令、用户消息、对话历史、相关记忆、RAG 检索结果、可用工具描述
- **压缩策略** — 当消息超过阈值时自动压缩旧消息，保留近期上下文
- **恢复** — 会话中断后可从历史文件恢复上下文

## 依赖注入

基于 `dependency-injector` 的分层 DI 容器：

- **AppContainer** — 应用级容器，组合所有子容器
- **ModelContainer** — LLM 实例管理
- **StorageContainer** — 数据库连接与仓库
- **MemoryContainer** — 记忆服务
- **ContextContainer** — 上下文服务
- **ToolContainer** — 工具管理
- **SkillContainer** — 技能服务
- **MCPContainer** — MCP 管理
- **RagContainer** — RAG 服务
- **SchedulerContainer** — 调度器
- **PromptContainer** — 提示词服务

## 设计模式

- **策略模式** — 所有 Provider 均基于 ABC 接口，可自由替换实现
- **装饰器自动注册** — `@register_tool` 等导入即注册
- **分层 DI 容器** — 通过 `dependency-injector` 管理所有服务实例
- **仓库模式** — 存储层通过 Repository 抽象数据访问
- **门面模式** — 各模块提供 Service 门面类，简化调用接口
- **收集器管道** — 上下文通过多个 Collector 组装，按优先级聚合

## 开发

```bash
# 安装依赖
uv sync

# 代码检查
ruff check src/
ruff format src/

# 类型检查
mypy src/

# 编译检查
uv run python -m compileall -q src\ai main.py

# 运行测试
uv run pytest
```

## 依赖

核心依赖：`langchain` / `langgraph` / `langchain-openai` / `langchain-anthropic` / `langchain-google-genai` / `langchain-ollama` / `langchain-mcp-adapters` / `mcp` / `sqlmodel` / `jinja2` / `fastapi` / `pydantic-settings` / `tenacity` / `pybreaker` / `typer` / `rich` / `dependency-injector` / `croniter` / `cryptography` / `chromadb` / `tiktoken` / `magika`

开发依赖：`pytest` / `pytest-asyncio` / `ruff` / `mypy`

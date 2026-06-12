# AI Chat

基于 **LangChain / LangGraph** 生态的本地 AI 工作台，提供多 LLM 提供商统一接入、智能 Agent 编排、RAG 检索增强生成、对话记忆管理、MCP 工具集成、定时任务调度等完整能力。

全栈架构：**Python (FastAPI)** + **Vue 3 (Vite + Element Plus)**。

## 功能特性

- **多 LLM 提供商** — OpenAI / Anthropic Claude / Google Gemini / Ollama / Minimax / 通义千问
- **智能 Agent** — LangGraph ReAct 循环、并行工具调用、Plan Mode、反思恢复、断点续传、多 Agent 协作
- **RAG 检索增强** — 多格式加载 (PDF/DOCX/MD/HTML/...)、多策略分块、ChromaDB+BM25 混合检索、增量索引
- **对话记忆** — 自动记忆提取摘要、向量语义搜索、会话历史、工作记忆、上下文压缩
- **上下文组装** — 多源收集器管道 (系统/记忆/RAG/MCP/工具)、自动压缩、会话恢复
- **MCP 集成** — 连接外部 MCP 工具服务器，或将内置工具暴露为 MCP 服务
- **技能系统** — Markdown 插件式斜杠命令，支持自定义提示词和工具绑定
- **定时任务** — cron 表达式调度，支持一次性/循环、并发控制、超时、重试
- **图像生成** — 支持 DALL·E 等模型文生图
- **语音合成** — Edge-TTS 文本转语音
- **内置工具** — 文件读写、搜索、Shell（白名单）、HTTP 请求、待办/计划管理等 14 个工具
- **安全** — Fernet 加密保护 API Key、沙箱执行、路径校验
- **Web 前端** — Vue 3 + Element Plus 管理后台，聊天/配置/工具/记忆/RAG 可视化操作

## 技术栈

| 层级 | 技术 |
|------|------|
| **后端框架** | Python 3.13 + FastAPI + Uvicorn |
| **LLM 框架** | LangChain 1.3+ / LangGraph 1.2+ |
| **向量数据库** | ChromaDB |
| **关系数据库** | SQLite (SQLModel ORM) |
| **配置管理** | pydantic-settings |
| **DI 容器** | dependency-injector |
| **前端框架** | Vue 3 (Composition API) |
| **构建工具** | Vite 8 |
| **UI 组件** | Element Plus + Tailwind CSS 4 |
| **状态管理** | Pinia |
| **路由** | Vue Router |
| **包管理** | uv (Python) / pnpm (前端) |

## 快速开始

### 环境要求

- Python >= 3.13
- [uv](https://docs.astral.sh/uv/) 包管理器
- Node.js >= 20.19.0（仅前端开发需要）
- [pnpm](https://pnpm.io/)（仅前端开发需要）

### 安装

```bash
git clone https://github.com/mhwssad/ai-chat
cd ai-chat

# 安装 Python 依赖
uv sync

# 安装前端依赖
cd src/front/ai-chat && pnpm install && cd ../../..
```

### 配置

在项目根目录创建 `.env` 文件，填入需要的 API Key：

```env
# 加密密钥（通过 python main.py 生成）
ENCRYPTION_KEY=

# Chat 模型默认配置
CHAT_MODEL_MODEL_KEY=qwen-turbo
CHAT_MODEL_BACKEND=openai
CHAT_MODEL_API_KEY=sk-xxx
CHAT_MODEL_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1

# Embedding 模型（RAG 使用）
EMBEDDING_MODEL_MODEL_KEY=bge-m3:latest
EMBEDDING_MODEL_BACKEND=ollama
EMBEDDING_MODEL_BASE_URL=http://127.0.0.1:11434

# 其他 LLM 提供商（按需配置）
OPENAI_API_KEY=sk-xxx
ANTHROPIC_API_KEY=sk-ant-xxx
GOOGLE_API_KEY=xxx
QWEN_API_KEY=sk-xxx
MINMAX_API_KEY=sk-cp-xxx
OLLAMA_BASE_URL=http://localhost:11434

# MCP（可选）
MCP_ENABLED=true
```

### 运行

```bash
# 仅启动后端 API
uv run python main.py --reload

# 同时启动前后端（后端 8000 + 前端 5173）
uv run python main.py --front --reload

# 自定义端口
uv run python main.py --port 8080 --front --front-port 3000
```

访问：
- **前端**：http://localhost:5173 （管理后台 + 聊天界面）
- **API 文档**：http://localhost:8000/docs （Swagger UI）

#### 前端单独开发

```bash
cd src/front/ai-chat
pnpm dev          # 启动 Vite 开发服务器
pnpm build        # 生产构建（产物输出到 dist/）
pnpm preview      # 预览构建产物
pnpm lint         # 代码检查（Oxlint + ESLint）
pnpm format       # 格式化
```

## 项目结构

```text
ai-chat/
├── main.py                    # 统一入口 (uivcorn + 前端 Vite 启动)
├── pyproject.toml             # Python 项目配置 (uv)
├── .env                       # 环境变量
├── .mcp.json                  # MCP 客户端配置
├── mcp_servers.json           # MCP 服务端注册表
│
├── src/
│   ├── ai/                    # Python 后端
│   │   ├── api/               # FastAPI 路由 + Schema
│   │   │   ├── routes/        # 14 个路由模块
│   │   │   └── schemas/       # Pydantic 请求/响应模型
│   │   ├── config/            # 配置管理 (pydantic-settings)
│   │   ├── core/              # 核心能力层
│   │   │   ├── agent/         # Agent 编排 (LangGraph ReAct/反思/移交/团队)
│   │   │   ├── callbacks/     # LLM 回调 (审计日志/链路追踪)
│   │   │   ├── context/       # 上下文组装 (收集器管道 + 压缩策略)
│   │   │   ├── mcp/           # MCP 客户端 + 服务端
│   │   │   ├── memory/        # 对话记忆 (提取/搜索/向量存储/工作记忆)
│   │   │   ├── models/        # LLM 提供商抽象 (注册表 + 构建器)
│   │   │   ├── prompts/       # 提示词模板 (Jinja2 + 数据库存储)
│   │   │   ├── rag/           # RAG 管线 (加载器/分块器/混合检索)
│   │   │   ├── scheduler/     # 定时任务调度 (cron + 一次性)
│   │   │   ├── skills/        # 技能插件系统
│   │   │   └── tools/         # 工具注册中心 + 14 个内置工具
│   │   ├── service/           # 共享服务层 (14 个 Service 门面)
│   │   ├── storage/           # 存储层 (SQLModel + SQLite + 仓库模式)
│   │   ├── exception/         # 分层异常体系
│   │   ├── security/          # 安全模块 (Fernet 加密)
│   │   └── utils/             # 工具函数 (缓存/Token计算/哈希/脱敏/HTTP)
│   │
│   └── front/ai-chat/         # Vue 3 前端
│       ├── src/
│       │   ├── api/           # Axios 客户端 + 14 个 API 模块
│       │   ├── components/    # 组件 (聊天/通用)
│       │   ├── layouts/       # 布局 (ChatLayout / AdminLayout)
│       │   ├── router/        # 路由配置
│       │   ├── stores/        # Pinia 状态管理
│       │   └── views/         # 页面 (聊天 + 12 个管理视图)
│       ├── vite.config.js     # Vite 配置 (代理到后端)
│       └── package.json
│
├── tests/                     # 测试
├── skills/                    # 自定义技能 (code-review/summarize/translate)
├── data/                      # 运行数据 (SQLite + ChromaDB + 记忆文件)
├── docs/                      # 文档 (需求/架构/数据模型/示例)
├── scripts/                   # 工具脚本
└── output/                    # 产物输出 (音频/图片)
```

## 系统架构

```
┌──────────────────────────────────────────────────────┐
│                  交互层 (Interaction)                 │
│   Vue 3 SPA (管理后台 + 聊天) + FastAPI REST/SSE      │
├──────────────────────────────────────────────────────┤
│                 共享服务层 (Service)                   │
│   Chat / Agent / Image / TTS / Memory / Prompt        │
│   RAG / Skill / Tool / Scheduler / Session / System   │
├──────────────────────────────────────────────────────┤
│                 核心能力层 (Core)                      │
│   Agent 编排  │  上下文组装  │  模型注册表             │
│   工具系统    │  对话记忆    │  RAG 管线               │
│   MCP 集成    │  技能系统    │  定时任务               │
├──────────────────────────────────────────────────────┤
│                  存储层 (Storage)                     │
│   SQLite (SQLModel)  │  ChromaDB (向量)  │  文件系统  │
├──────────────────────────────────────────────────────┤
│                基础设施层 (Infrastructure)             │
│   线程池  │  HTTP 客户端  │  配置  │  加密  │  日志   │
└──────────────────────────────────────────────────────┘
```

## API 路由

| 前缀 | 说明 |
|------|------|
| `/api/chat` | 对话（非流式 / SSE 流式 / OpenAI 兼容接口） |
| `/api/agent` | Agent 编排执行 |
| `/api/models` | LLM 模型配置管理 |
| `/api/tools` | 工具列表 / 注册 / 执行 |
| `/api/skills` | 技能发现与调用 |
| `/api/sessions` | 会话 CRUD |
| `/api/memory` | 记忆管理 / 搜索 / 重建 |
| `/api/rag` | 文档索引 / 检索 / 管理 |
| `/api/prompts` | 提示词模板管理 |
| `/api/image` | 图像生成 |
| `/api/tts` | 语音合成 |
| `/api/scheduler` | 定时任务创建 / 管理 / 日志 |
| `/api/system` | 系统状态 / 信息 |

## 支持的 LLM 提供商

| 提供商 | Chat | Embedding | Image | TTS |
|--------|------|-----------|-------|-----|
| OpenAI | GPT-4o 等 | text-embedding-3-small | DALL·E | ✓ |
| Anthropic | Claude 系列 | - | - | - |
| Google | Gemini 系列 | - | - | - |
| Ollama | 本地模型 | nomic-embed-text 等 | - | - |
| Minimax | M2.7 | - | - | - |
| 通义千问 | Qwen 系列 | - | - | - |

## 内置工具

| 分类 | 工具 |
|------|------|
| 文件 | 读取、按行读取、覆盖写入、追加写入、精确替换、正则替换 |
| 目录 | 列出目录、查看路径信息、创建目录、Glob 查找 |
| 搜索 | 项目目录内文本搜索文件内容 |
| Shell | 白名单 PowerShell 只读查询 |
| Web | HTTP GET / POST 请求 |
| 交互 | 用户确认、用户输入 |
| 笔记 | 笔记本读写 |
| 计划 | 任务计划创建与管理 |
| 待办 | 待办事项管理 |
| 调度 | 定时任务创建与管理 |
| 工作树 | 工作树信息查询 |
| 图像 | 图像生成与处理 |
| TTS | 文本转语音 |

> 所有内置工具默认限制在项目根目录内运行，shell 工具仅用于只读查询。

## 核心设计

### 依赖注入

基于 `dependency-injector` 的分层 DI 容器，从配置 → 基础设施 → 子容器 → 共享服务逐层装配：

```
AppContainer
├── Settings (配置)
├── ThreadPool / ModelContainer / ChatLLM
├── StorageContainer / PromptContainer
├── MemoryContainer / RagContainer / ContextContainer
├── ToolContainer / SkillContainer / MCPContainer
├── SchedulerContainer / AgentContainer
└── ServiceContainer (14 个 Service 门面)
```

### 设计模式

| 模式 | 应用场景 |
|------|----------|
| **策略模式** | 所有 Provider 基于 ABC 接口，可替换实现 |
| **门面模式** | 各模块通过 Service 门面简化调用 |
| **仓库模式** | Storage 层通过 Repository 抽象数据访问 |
| **注册表模式** | ModelFactoryRegistry / ToolRegistry |
| **构建器模式** | LLM Builder 统一模型实例创建 |
| **收集器管道** | 上下文通过多 Collector 按优先级聚合 |
| **装饰器注册** | `@register_tool` 导入即注册 |

### 上下文管理

每次对话自动组装完整上下文：

1. **收集** — 系统指令 + 用户消息 + 对话历史 + 相关记忆 + RAG 检索 + 工具描述
2. **压缩** — 超阈值时自动压缩旧消息（MicroCompact / FullCompact 策略）
3. **恢复** — 会话中断后从历史文件恢复上下文

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
uv run python -m compileall -q src/ai main.py

# 运行测试
uv run pytest
```

## 核心依赖

**Python**: `langchain` / `langgraph` / `langchain-openai` / `langchain-anthropic` / `langchain-google-genai` / `langchain-ollama` / `langchain-mcp-adapters` / `mcp` / `fastapi` / `sqlmodel` / `chromadb` / `jinja2` / `pydantic-settings` / `dependency-injector` / `croniter` / `cryptography` / `tiktoken` / `tenacity` / `pybreaker` / `edge-tts` / `pillow` / `rank-bm25` / `jieba`

**前端**: `vue` / `vite` / `element-plus` / `pinia` / `vue-router` / `axios` / `tailwindcss` / `markdown-it`

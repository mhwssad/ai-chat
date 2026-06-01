# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概览

AI Chat — 基于 FastAPI 的本地 AI 工作台，提供多供应商模型调用、工具执行、MCP 协议、RAG 检索等能力。Python >= 3.13，使用 uv 管理依赖。

## 必读文档

开始任何实现前，先阅读并遵守：

- `docs/README.md`
- `docs/project-structure-standards.md`
- `docs/coding-standards.md`
- `docs/architecture-constraints.md`
- `docs/data.sql`

其中 `docs/architecture-constraints.md` 是硬约束。若实现需求和该文档冲突，先更新约束文档并说明原因，再改代码。

## 常用命令

```bash
# 安装依赖
uv sync

# 运行 FastAPI
uv run python main.py

# 编译检查
uv run python -m compileall -q src/ai main.py

# 数据库 schema 验证
sqlite3 :memory: ".read docs/data.sql" "PRAGMA foreign_key_check;"

# 代码检查
ruff check src/
ruff format src/

# 类型检查
mypy src/

# 运行测试
python -m pytest tests/
```

FastAPI 启动后访问 `http://127.0.0.1:8000/`

## 代码搜索规范

项目已安装 `python-lsp-server`（pylsp），**默认使用 LSP 进行代码搜索和导航**，而非纯文本搜索。

### 优先级

1. **LSP 符号搜索**（首选）— 按函数名、类名、变量名精确查找定义和引用
2. **Grep 文本搜索**（次选）— 仅用于搜索注释、字符串字面量、配置值等非符号内容
3. **Glob 文件搜索** — 仅用于按文件名模式查找文件

### 使用场景

| 需求 | 使用方式 |
|------|---------|
| 查找函数/类定义 | LSP symbol search |
| 查找变量在哪里被引用 | LSP references |
| 查看函数签名和参数 | LSP hover |
| 跳转到类型定义 | LSP type definition |
| 搜索日志/错误信息文本 | Grep |
| 查找配置文件、测试文件 | Glob |

### LSP 启动

```bash
# stdio 模式（编辑器集成）
uv run pylsp

# TCP 模式（调试/远程）
uv run pylsp --tcp --port 2087
```

## 分层架构

```text
src/ai/
├── api/            → FastAPI 入口：路由(routes/)、schema(schemas/)、服务层(services/)、页面、静态资源
├── cli.py          → CLI 补充入口（Typer）
├── config/         → 启动期最小配置（BaseSettingsConfig + 分域 Settings）
├── core/
│   ├── models/     → 模型子系统：Client、Registry、Resolver、Provider、遥测、定价
│   │   └── providers/  → 具体供应商实现（httpx_openai、langchain_chat 等）
│   ├── tools/      → 工具子系统：Registry、内置工具(builtins)、执行器
│   ├── mcp/        → MCP 协议：Client、Manager、工具适配器
│   ├── prompts/    → 提示词模板管理（Service + Renderer + 持久化）
│   ├── memory/     → 记忆子系统（MEMORY.md 索引 + 文件存储、DB 辅助索引、相关性检索）
│   └── skills/     → 技能插件（SKILL.md 文件驱动、渐进式披露）
├── rag/            → RAG 管线：文件加载、文本切分、Embedding、相似度检索
├── storage/        → SQLModel ORM、Repository、数据库连接管理
├── security/       → 加密（Fernet API Key 加密/解密）
├── exception/      → 统一异常体系（所有自定义异常集中管理：LLM、Tool、MCP、Loader、Prompt、Skill、Memory、RAG、HTTP）
└── utils/          → 工具函数（字符串、HTTP 客户端、缓存、脱敏、token 计算）
```

## 核心设计模式

### 分层调用链

典型聊天请求的数据流：

```text
API Route → api/services/<name>_service.py
  → ModelClient.chat(ChatRequest)
    → ModelResolver.resolve(session, request)     # 从 DB 解析 Provider + Model
    → ModelProviderRegistry.get(capability, req_type)  # 查找 Provider 策略
    → ModelProvider.request(provider, model, req)      # 执行实际 API 调用
    → PricingCalculator.calculate(usage, model)        # 计算费用
    → ModelTelemetryRecorder.record_*()                # 遥测记录
    → 返回 ModelResponse
```

### Registry + Strategy（模型子系统）

- `ModelProvider`（ABC）定义统一接口，具体供应商（httpx_openai、langchain_chat 等）实现策略
- `ModelProviderRegistry` 按 `(capability, request_type)` 元组路由到 Provider 实例
- `ModelResolver` 从数据库解析 model_id / provider_key+model_key → 具体 Provider+Model
- `ModelClient` 是门面类，编排解析→分发→定价→遥测全流程

### Registry + Handler（工具子系统）

- `ToolRegistry` 维护 name → `ToolDefinition` 映射
- 每个内置工具是 `ToolDefinition`（含 JSON schema、权限标签、async handler）
- MCP 工具通过 `MCPManager` → `MCPClient` 与外部服务通信

### Repository Pattern（存储层）

- 所有数据库访问通过 Repository 类（`ProviderRepository`、`ModelRepository` 等）
- ORM 模型使用 SQLModel（`Provider`、`Model`、`PromptTemplate` 等）
- `get_session()` 上下文管理器自动管理事务（commit/rollback）

### 模块级单例

| 单例 | 位置 | 用途 |
| --- | --- | --- |
| `settings` | `config/settings.py` | 分域全局配置 |
| `provider_registry` | `core/models/registry.py` | 模型 Provider 注册表 |
| `tool_registry` | `core/tools/registry.py` | 工具注册表 |
| `mcp_manager` | `core/mcp/manager.py` | MCP 服务器管理 |
| `prompt_service` | `core/prompts/service.py` | 提示词模板服务 |
| `memory_service` | `core/memory/service.py` | 记忆管理服务 |
| `rag_service` | `rag/service.py` | RAG 检索服务 |

## 硬性开发规则

- 禁止新增 `src/ai_chat`。
- MCP 模块位于 `src/ai/core/mcp/`，禁止将其迁移到其他位置。
- 禁止 API 路由直接写业务逻辑——路由只做参数校验和调用 service。
- 禁止绕过 `core/models` 调用模型。
- 禁止绕过 `core/tools` 调用工具。
- 禁止 RAG 自建模型 provider。
- 禁止业务代码直接 `os.getenv()`，配置统一通过 `config/settings.py`。
- 禁止新增裸 `Exception` 子类，自定义异常必须继承 `BaseExceptions`。
- ORM/schema 变化必须同步 `docs/data.sql`。
- API Key 必须加密保存（Fernet），禁止明文入库。

## 编码规范要点

- 注释和文档字符串使用中文，类名/函数名/文件名使用英文
- 所有新增函数必须补充参数和返回值类型标注
- 使用现代类型语法：`list[str]`、`X | None`（Python 3.13）
- 公共类和函数必须有中文 docstring
- 配置统一通过 `config/settings.py` 管理
- 抛出项目领域异常（如 `ModelNotSupportedException`），不抛裸 `Exception`
- 异步优先设计，同步包装注意事件循环处理

## 新增功能落位

| 新增内容 | 放置位置 |
|---------|---------|
| FastAPI 路由 | `src/ai/api/routes/<name>.py` |
| API schema | `src/ai/api/schemas/<name>.py` |
| API service | `src/ai/api/services/<name>_service.py` |
| HTML 页面 | `src/ai/api/templates/` |
| 静态资源 | `src/ai/api/static/` |
| 模型 provider | `src/ai/core/models/providers/<name>.py`，继承 `ModelProvider` ABC |
| 工具 | `src/ai/core/tools/builtins.py` 添加 `ToolDefinition` |
| MCP | `src/ai/core/mcp/` |
| RAG | `src/ai/rag/` |
| ORM / Repository | `src/ai/storage/<name>_models.py` + `<name>_repository.py` |
| 提示词模板 | 通过 `PromptService` 管理，持久化到 DB |
| 记忆 | `src/ai/core/memory/`，MEMORY.md 索引 + 文件存储，DB 辅助索引 |

## 环境配置

根目录 `.env` 文件。配置通过 pydantic `BaseSettings` 自动加载，分三个域：

- `LLMSettings` — 模型名、超时、上下文管理
- `MemorySettings` — 记忆后端、摘要设置
- `MCPSettings` — MCP 客户端/服务端配置

API Key 和 base_url 存储在数据库 `Provider` 表（加密），不再在 `.env` 中配置。

## 验证要求

每次代码修改后，根据影响面运行最小验证：

- Python 编译：`uv run python -m compileall -q src/ai main.py`
- 数据库 schema：`sqlite3 :memory: ".read docs/data.sql" "PRAGMA foreign_key_check;"`
- FastAPI 路由：使用 `TestClient` 做 smoke test
- RAG、工具、模型 provider：至少跑一条端到端最小路径

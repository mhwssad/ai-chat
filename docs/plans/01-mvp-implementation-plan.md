# 第一期 MVP 实施计划

## 1. 计划目标

第一期目标是把当前已完成的 FastAPI、模型、工具、MCP、skills、prompt、memory、RAG 和 storage 底座收敛成一个可用的本地 AI 工作台。

本计划以 `docs/requirements` 为需求来源，以当前 `src/ai` 代码结构为实施基线。第一期不再从旧代码兼容出发，而是继续沿用当前重构后的目录、依赖方向和数据库优先原则。

## 2. 当前代码基线

当前项目已经具备以下基础模块：

- `src/ai/api`：FastAPI 应用、路由、schemas、services、HTML 模板和静态资源。
- `src/ai/storage`：数据库初始化、ORM、Repository、运行态数据、模型配置、MCP、prompt、RAG 等存储边界。
- `src/ai/core/models`：统一模型请求模块，支持 provider registry、chat、embedding、streaming、usage 和 pricing 边界。
- `src/ai/core/tools`：统一工具注册、执行、内置工具、MCP 工具适配和审计入口。
- `src/ai/core/skils`：本地 Skill 发现、数据库同步、Jinja 渲染和 Skill 工具挂载。
- `src/ai/core/prompts`：数据库提示词模板、版本管理和 Jinja 渲染。
- `src/ai/core/memory`：本地记忆文件、记忆扫描、相关性查找、prompt 构建和数据库索引。
- `src/ai/rag`：文件加载、文本切分、embedding、向量存储和检索服务。
- `docs/data.sql`：当前目标 SQLite schema 的权威文档。

第一期后续工作重点不是重新搭底座，而是补齐可用闭环、API 管理入口、页面交互、CLI 补充入口和最小验证。

## 3. 实施原则

- 需求以 `docs/requirements` 为准，计划以当前代码状态为准。
- FastAPI 是主入口，CLI 只做补充和诊断。
- 业务配置以 SQLite 为 source of truth。
- 所有数据库操作继续放在 `src/ai/storage`。
- 模型调用必须经过 `src/ai/core/models`。
- 工具、MCP 和 Skill 调用必须经过 `src/ai/core/tools`。
- Prompt 必须通过 `src/ai/core/prompts` 使用数据库和 Jinja2 渲染。
- RAG embedding 必须优先复用 `core/models`。
- 新增 ORM 或表字段必须同步更新 `docs/data.sql`。
- 所有自定义异常必须继承 `BaseExceptions`。

## 4. 第一期交付范围

### 4.1 Web 聊天闭环

Web 应能完成会话创建、消息发送、流式回复、模型切换、历史消息查看和错误展示。

后续实现重点：

- 打通聊天页面与 `api/routes/chat.py`。
- 确认流式输出在页面中实时追加。
- 保存用户消息、助手消息、状态、错误和模型记录。
- 支持历史会话加载和继续对话。
- 增加停止生成的接口预留。

### 4.2 模型与供应商管理

模型和供应商应通过数据库管理，并对 Web 和 CLI 共享。

后续实现重点：

- 完善供应商和模型 CRUD API。
- 增加默认模型设置和校验。
- 增加 provider/model 健康检查。
- 页面展示可用模型并支持选择。
- CLI 支持列出、检查和发起一次性请求。

### 4.3 工具、MCP 和 Skills 管理

工具能力应通过统一工具注册表暴露。MCP 和 Skills 不应绕过工具层。

后续实现重点：

- 增加 Skills API：发现、列表、启用、禁用、查看工具定义。
- 增加 MCP server 管理 API：列表、创建、更新、禁用、连接检查、工具发现。
- 工具调用入口补齐最小权限策略和审计记录。
- Web 页面展示工具、MCP、Skill 的注册状态和错误。

### 4.4 Prompt 管理

提示词模板应通过数据库和 Jinja2 管理，不在业务代码中硬编码大段提示词。

后续实现重点：

- 增加 Prompt API：模板列表、创建、更新、发布版本、渲染预览。
- 聊天上下文组装接入 PromptService。
- 页面提供最小提示词管理入口或诊断入口。

### 4.5 Memory 管理

第一期以会话内记忆和长期记忆边界为主。

后续实现重点：

- 聊天上下文组装包含会话历史、工具摘要和必要系统状态。
- 增加 Memory API：列表、写入、搜索、删除、加载 memory prompt。
- 默认不自动写入长期记忆。
- 记忆写入和检索记录审计信息。

### 4.6 RAG 知识库闭环

RAG 已有底座，第一期应打通文件入库、分块、向量计算、存储和检索。

后续实现重点：

- 完善 RAG API 的文件摄取、文档列表、检索和删除。
- 聊天接口增加显式 `use_rag` 或同等开关。
- 检索结果进入聊天上下文前必须可控、可审计。
- 页面提供最小文件上传和检索验证入口。

### 4.7 审计、用量和价格

第一期需要能追踪模型调用和工具调用。

后续实现重点：

- 模型调用记录 prompt tokens、completion tokens、总 token、耗时、状态和错误。
- 价格计算使用统一 pricing 工具，不放在模型请求模块中。
- 工具调用记录来源、输入摘要、输出摘要、耗时、权限决策和错误。
- 增加 usage 查询 API 和页面/CLI 诊断入口。

### 4.8 CLI 补充入口

CLI 不替代 FastAPI，但应满足开发和诊断需求。

后续实现重点：

- 启动服务。
- 一次性聊天请求。
- 查看供应商和模型列表。
- 检查数据库配置。
- 列出工具注册表。
- 触发 RAG 摄取或检索 smoke test。

## 5. 非目标

第一期不实现以下内容：

- 多用户账号系统。
- 云端同步和团队空间。
- 完整 Agent 编排运行时。
- 后台任务队列和长任务恢复。
- 完整 MCP 管理面板。
- Skill 市场、远程安装和复杂版本管理。
- 自动长期记忆提取。
- 完整安全沙箱。

## 6. 验收标准

第一期完成时应满足：

- Web 可以完成一次流式聊天。
- 至少两个模型或两个供应商可以通过同一模型接口调用。
- 用户可以在 Web 中切换模型，切换只影响后续消息。
- 会话刷新后可以重新加载历史消息。
- CLI 可以列出模型并发起一次聊天请求。
- 工具注册表可以列出内置工具、MCP 工具和 Skill 工具。
- RAG 可以摄取文件、切分文本、计算向量、存储并检索。
- 聊天可以显式开启 RAG 增强。
- Prompt 模板可以从数据库读取并用 Jinja2 渲染。
- 模型调用、工具调用、权限决策和关键错误有审计记录。
- API Key 不会明文保存到数据库或日志。

## 7. 验证命令

每次完成第一期任务后至少运行：

```powershell
uv run python -m compileall -q src\ai main.py
sqlite3 :memory: ".read docs/data.sql" "PRAGMA foreign_key_check;"
```

涉及具体模块时增加最小 smoke test：

- 模型：通过测试配置发起一次 chat 或 embedding 请求。
- 工具：注册并执行一个低风险工具。
- Skill：创建临时 `SKILL.md`，发现、同步、挂载并执行。
- RAG：摄取临时文本文件并检索命中。
- Prompt：创建模板版本并渲染。
- Memory：写入临时记忆并构建 memory prompt。

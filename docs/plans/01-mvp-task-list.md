# 第一期 MVP 任务清单

## 1. 状态说明

- `done`：当前代码已经有对应底座或主要实现。
- `todo`：第一期需要继续补齐。
- `later`：进入第二期或后续阶段。

## 2. 基础架构

| 状态 | 任务 | 说明 |
| --- | --- | --- |
| done | FastAPI 主入口 | 已有 `src/ai/api/app.py`、lifespan、errors、dependencies、routes、schemas、services。 |
| done | 前后端同项目结构 | HTML 在 `api/templates`，CSS/JS 在 `api/static`。 |
| done | 启动期配置边界 | 已有 `src/ai/config/base_config.py`。业务配置继续走数据库。 |
| done | 统一异常基类 | 已有 `src/ai/exception/base_exception.py`，新增异常必须继承它。 |
| todo | 检查 routes 业务逻辑 | 确认 `api/routes` 只做参数接收和 service 调用。 |
| todo | API 错误结构统一 | 确认所有 route/service 抛出的异常都能通过 `api/errors.py` 输出一致结构。 |

## 3. 数据库与配置

| 状态 | 任务 | 说明 |
| --- | --- | --- |
| done | SQLite 目标 schema | 已有 `docs/data.sql`。 |
| done | 数据库集中目录 | ORM、Repository 和数据库初始化位于 `src/ai/storage`。 |
| done | API Key 加密保存 | 已有 `src/ai/security/crypto.py`。 |
| done | 供应商和模型表 | 已有模型注册和配置相关 storage。 |
| todo | 配置校验服务 | 校验默认模型、启用供应商、凭据、重复 key 和 schema 必填字段。 |
| todo | 数据库路径统一到根目录 data | 确认运行态 SQLite、memory、RAG 文件都默认落在项目根目录 `data/`。 |
| todo | schema 与 ORM 对齐检查 | 新增或调整字段时同步 `docs/data.sql`。 |

## 4. 模型调用

| 状态 | 任务 | 说明 |
| --- | --- | --- |
| done | 通用模型模块 | 已有 `src/ai/core/models`。 |
| done | Provider registry | 已有 provider 注册和 resolver。 |
| done | LangChain 优先请求 | 已有 LangChain chat provider。 |
| done | httpx fallback | 已有 OpenAI-compatible httpx provider。 |
| done | Streaming 支持 | 已有流式响应边界。 |
| done | Token 和价格边界 | usage 与 pricing 已拆出模型请求单一职责。 |
| todo | 模型 CRUD API 完善 | 补齐供应商、模型、默认模型的增删改查和校验。 |
| todo | 模型健康检查 | 对启用供应商和模型提供最小诊断接口。 |
| todo | 统一错误映射 | 认证、限流、网络、模型不存在、响应格式异常需要统一错误类型。 |

## 5. 聊天与会话

| 状态 | 任务 | 说明 |
| --- | --- | --- |
| done | Chat route/service 初始结构 | 已有 `api/routes/chat.py` 和 `api/services/chat_service.py`。 |
| todo | Web 流式聊天闭环 | 页面发消息、实时接收、保存消息和错误。 |
| todo | 会话列表和历史加载 | 支持创建、打开、继续历史会话。 |
| todo | 聊天模型切换 | Web 和 API 支持选择模型，历史消息保留原模型记录。 |
| todo | 上下文组装服务 | 统一整合历史消息、系统 prompt、工具摘要、memory 和可选 RAG。 |
| todo | 停止生成接口预留 | Web 可发送取消意图，后续再接完整取消机制。 |

## 6. Tools、MCP 和 Skills

| 状态 | 任务 | 说明 |
| --- | --- | --- |
| done | 统一工具模块 | 已有 `src/ai/core/tools`。 |
| done | MCP 合并到 tools | MCP 位于 `src/ai/core/tools/mcp`。 |
| done | Skill 挂载 | 已有 `src/ai/core/skils` 发现、同步、渲染和工具挂载。 |
| todo | Skills API | 增加发现、列表、启用、禁用、工具定义查询。 |
| todo | MCP 管理 API | 增加 server CRUD、连接检查、工具发现。 |
| todo | 权限策略执行 | 工具执行入口需要根据权限声明允许、拒绝或标记需要确认。 |
| todo | 工具审计补齐 | 记录来源、输入摘要、输出摘要、耗时、状态和错误。 |
| todo | Web 工具状态展示 | 页面展示内置工具、MCP 工具和 Skill 工具的状态。 |

## 7. Prompt

| 状态 | 任务 | 说明 |
| --- | --- | --- |
| done | Prompt 核心模块 | 已有 `src/ai/core/prompts`。 |
| done | Prompt storage | 已有 prompt ORM 和 repository。 |
| done | Jinja2 渲染 | Prompt 和 Skill 渲染都使用 Jinja2。 |
| todo | Prompt API | 增加模板列表、创建、更新、发布版本、渲染预览。 |
| todo | 聊天接入 PromptService | 系统提示、上下文提示和 RAG 提示通过数据库模板渲染。 |
| todo | Prompt 页面入口 | 提供最小管理或预览页面。 |

## 8. Memory

| 状态 | 任务 | 说明 |
| --- | --- | --- |
| done | Memory 核心模块 | 已有 `src/ai/core/memory`。 |
| done | 本地 memory 路径和扫描 | 已有路径解析、frontmatter 扫描和 prompt 构建。 |
| todo | Memory API | 增加列表、写入、搜索、删除、加载 prompt。 |
| todo | 聊天上下文接入 | 会话内记忆和工具摘要进入上下文组装。 |
| todo | 审计记忆行为 | 记录写入、删除、搜索命中和 prompt 组装来源。 |
| later | 自动长期记忆提取 | 第一阶段默认不自动写入长期记忆。 |

## 9. RAG

| 状态 | 任务 | 说明 |
| --- | --- | --- |
| done | RAG 基础模块 | 已有 loaders、splitters、embeddings、service。 |
| done | RAG storage | 已有 rag ORM 和 repository。 |
| done | Embedding 复用 models | RAG embedding 优先走 `core/models`。 |
| todo | RAG API 完善 | 文件摄取、文档列表、检索、删除和错误展示。 |
| todo | Web 文件入口 | 提供最小上传、摄取状态和检索测试。 |
| todo | 聊天显式 use_rag | 只有用户开启时才把检索结果加入上下文。 |
| todo | RAG smoke test | 临时文本摄取、分块、向量存储和检索命中。 |

## 10. Usage、审计和诊断

| 状态 | 任务 | 说明 |
| --- | --- | --- |
| done | Usage route/service 初始结构 | 已有 `api/routes/usage.py` 和 usage service。 |
| done | 模型 usage 提取 | 已有 usage 类型和提取逻辑。 |
| todo | 模型调用审计完整字段 | token、价格、耗时、状态、错误、供应商和模型。 |
| todo | 工具调用审计完整字段 | 工具来源、权限决策、输入摘要、输出摘要、耗时和错误。 |
| todo | Usage 查询接口 | 支持按时间、模型、供应商、会话查询。 |
| todo | 敏感信息脱敏检查 | 确认日志和审计不保存明文 API Key。 |

## 11. Web 和 CLI

| 状态 | 任务 | 说明 |
| --- | --- | --- |
| done | Web 静态资源结构 | 已有 `index.html`、`app.css`、`app.js`。 |
| todo | Web 聊天主体验 | 完成会话、模型选择、流式输出、错误展示。 |
| todo | Web 管理入口 | 模型、工具、RAG、Prompt、Memory 提供最小入口。 |
| todo | CLI 启动服务 | CLI 可启动 FastAPI。 |
| todo | CLI 一次性聊天 | CLI 可指定模型并发起请求。 |
| todo | CLI 配置检查 | 检查数据库、供应商、模型、凭据和默认模型。 |
| todo | CLI 工具诊断 | 列出工具注册表和权限声明。 |

## 12. 第一批执行顺序

建议按以下顺序推进，保证每一步都能形成可验证闭环：

1. 配置校验和模型 CRUD。
2. Web 流式聊天闭环。
3. 会话历史和模型切换。
4. PromptService 接入聊天上下文。
5. Tool/MCP/Skill API 和审计补齐。
6. RAG API、Web 文件入口和 `use_rag` 聊天增强。
7. Memory API 和会话内上下文接入。
8. CLI 诊断和一次性聊天。
9. Usage 查询、价格统计和敏感信息脱敏复查。

## 13. 每次任务完成后的验证

通用验证：

```powershell
uv run python -m compileall -q src\ai main.py
sqlite3 :memory: ".read docs/data.sql" "PRAGMA foreign_key_check;"
```

按模块增加 smoke test：

- 模型：一次 chat 或 embedding 请求。
- 工具：注册并执行一个低风险工具。
- Skill：临时 `SKILL.md` 发现、同步、挂载和执行。
- RAG：临时文本摄取、切分、embedding 和检索。
- Prompt：模板创建、版本发布和 Jinja2 渲染。
- Memory：写入、扫描、搜索和 prompt 构建。


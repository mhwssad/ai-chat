# AI Chat 架构约束

本文档是项目硬约束。后续实现、重构和自动化代码生成必须遵守这些规则。若确实需要违反，必须先修改本文档并说明原因。

## 1. 目录红线

- 禁止新增 `src/ai_chat`。
- 禁止新增 `src/ai/core/mcp`，MCP 必须在 `src/ai/core/tools/mcp`。
- 禁止把业务逻辑放入 `main.py`。
- 禁止把业务逻辑放入 `api/routes`。
- 禁止把具体领域流程放入 `utils`。
- 禁止在 `core`、`rag`、`api` 中新增 ORM 或 Repository。

## 2. 依赖方向

允许：

```text
api -> core/rag/storage/config
core -> storage/config/security/utils
rag -> core/models/storage/utils
storage -> config
utils -> config/exception
```

禁止：

```text
core -> api
storage -> core/api/rag
utils -> core/api/storage
models provider -> rag/tools/api
```

## 3. 模型调用约束

- 禁止绕过 `core/models` 直接调用模型 SDK。
- 禁止在 RAG、API、工具中直接实现供应商模型请求。
- 新模型能力必须通过 `ModelCapability`、request/response 类型和 provider registry 扩展。
- chat、embedding、image、audio、video 后续都必须走同一个模型模块边界。

## 4. 工具调用约束

- 禁止绕过 `core/tools` 执行工具。
- 内置工具、MCP 工具、Skill 工具必须进入统一工具注册表。
- 工具调用必须经过 `ToolExecutor`，并记录工具调用或审计日志。
- 高风险工具后续必须接权限策略，不允许在工具内部私自确认或绕过。
- Skill 不允许绕过工具注册表直接进入 Agent。
- Skill 数据库配置必须写入 `skills` 表。

## 5. RAG 约束

- RAG 不允许自建模型 provider。
- RAG embedding 必须优先复用 `core/models`。
- RAG fallback embedding 只能用于本地开发和无模型配置场景。
- RAG 检索结果进入聊天上下文必须显式开启，不能默认污染全部聊天。

## 6. 数据库约束

- 业务配置以数据库为 source of truth。
- ORM 表变更必须同步 `docs/data.sql`。
- `docs/data.sql` 是当前目标 schema 的权威文档。
- Repository 不允许写业务编排。
- 所有 ORM、Repository、数据库配置读取必须放在 `src/ai/storage`。
- 禁止明文保存 API Key、token、credential。

## 6.1 提示词约束

- 提示词领域能力放在 `src/ai/core/prompts`。
- 提示词模板和历史版本必须存数据库。
- 提示词渲染必须使用 Jinja2。
- 提示词 ORM 和 Repository 必须放在 `src/ai/storage`。
- 业务代码不得硬编码大段提示词，应通过 `PromptService` 读取和渲染。

## 7. 配置和密钥约束

- 业务代码禁止直接 `os.getenv()`。
- 启动期配置只能通过 `get_bootstrap_settings()` 等配置入口读取。
- API Key 必须加密保存。
- 缺少加密 key 时必须失败。

## 8. 异常约束

- 所有自定义异常必须继承 `BaseExceptions`。
- 禁止新增裸 `Exception` 子类。
- 异常必须提供可定位上下文。
- FastAPI 统一通过 `api/errors.py` 输出错误。

## 9. FastAPI 约束

- `routes` 不写业务逻辑。
- `schemas` 不导出 ORM。
- `services` 是 API 到 core/storage 的协调层。
- HTML 放 `api/templates`。
- CSS/JS 放 `api/static`。
- CLI 是补充入口，不替代 FastAPI 主入口。

## 10. 文件职责约束

- 禁止将多个领域能力堆在一个文件。
- 禁止为了快而创建无边界的 `common.py`、`utils.py`、`helper.py`。
- 当文件同时出现请求类型、provider、仓库、路由、业务流程时必须拆分。

## 11. 变更检查清单

每次新增功能必须确认：

1. 目录落位是否符合结构规范。
2. 依赖方向是否符合本文档。
3. 是否需要更新 `docs/data.sql`。
4. 是否需要更新 API schema。
5. 是否复用已有模型、工具、存储边界。
6. 是否有最小验证命令或 smoke test。

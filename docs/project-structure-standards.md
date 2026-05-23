# AI Chat 项目结构规范

本文档定义当前 `ai-chat` 的目录职责和新增代码落位规则。项目已经进入以 FastAPI 为主入口、CLI 为补充入口的重构阶段，所有新代码以 `src/ai` 为准，不再参考旧 `src/ai_chat` 结构。

## 1. 总体结构

```text
ai-chat/
├─ docs/                         # 需求、计划、规范、数据库 schema
│  ├─ requirements/              # 产品和模块需求
│  ├─ plans/                     # 实施计划
│  ├─ data.sql                   # 目标数据库 schema
│  ├─ project-structure-standards.md
│  ├─ coding-standards.md
│  └─ architecture-constraints.md
├─ data/                         # 本地 SQLite、索引和运行数据
├─ src/
│  └─ ai/
│     ├─ api/                    # FastAPI 应用层，前后端一体入口
│     ├─ core/                   # 核心业务能力
│     ├─ rag/                    # RAG 索引、切分、向量和检索
│     ├─ storage/                # SQLModel ORM、Repository、数据库连接
│     ├─ config/                 # 启动期配置、日志、基础配置类
│     ├─ security/               # 加密、安全相关能力
│     ├─ exception/              # 统一异常体系
│     ├─ utils/                  # 无业务状态的通用工具
│     └─ cli.py                  # CLI 补充入口
├─ main.py                       # FastAPI 启动入口
└─ pyproject.toml
```

## 2. `src/ai/api`

FastAPI 应用层，负责 HTTP、HTML 页面、Pydantic schema 和服务编排。

```text
api/
├─ app.py                 # create_app() 和 app 实例
├─ lifespan.py            # 启动/关闭生命周期
├─ dependencies.py        # FastAPI Depends
├─ errors.py              # HTTP 异常处理
├─ routes/                # HTTP 路由
├─ schemas/               # Pydantic 请求/响应模型
├─ services/              # 面向 API 的服务层
├─ templates/             # Jinja2 HTML 页面
└─ static/                # CSS/JS/图片等静态资源
```

规则：

- `routes/` 只处理 HTTP 参数、响应和状态码。
- `services/` 负责调用 `core`、`rag`、`storage`，但不直接实现底层能力。
- `schemas/` 只放 API 入参/出参，不复用 ORM 作为公网 API schema。
- `templates/` 放前后端一体 HTML 页面。
- `static/` 放页面 CSS、JS 和静态资源。
- API 层可以依赖 `core`、`rag`、`storage`，反向依赖禁止。

## 3. `src/ai/core`

核心业务能力层。这里的模块应能被 FastAPI、CLI、未来 Agent 共同复用。

当前子模块：

- `core/models`：通用多供应商多类型模型请求，包括 chat、embedding，后续扩展 image/audio/video。
- `core/tools`：统一工具注册、执行、审计入口。MCP 已合并到 `core/tools/mcp`。
- `core/memory`：会话记忆和长期记忆边界，当前预留。
- `core/prompts`：提示词存储和 Jinja2 渲染的领域入口。
- `core/skils`：Skill 发现、渲染和挂载入口。目录名沿用当前项目拼写。

规则：

- `core` 不依赖 FastAPI。
- 模型请求必须走 `core/models`。
- 工具调用必须走 `core/tools`。
- MCP 工具属于工具体系，放在 `core/tools/mcp`。
- `core/models` 只处理请求与响应，不负责 RAG、记忆、业务编排。
- `core/prompts` 不定义 ORM/Repository，只通过 `storage` 访问数据库。
- Skill 可被转换为 `ToolDefinition`，必须通过 `core/tools` 暴露给 Agent 或聊天流程。

## 4. `src/ai/rag`

RAG 知识库能力层，负责文件内容识别、文本切分、向量生成、向量存储和检索上下文组装。

当前职责：

- `loaders.py`：文件加载与内容识别。
- `splitters.py`：文本切分。
- `embeddings.py`：调用 `core/models` 的 embedding 能力，必要时使用本地 fallback。
- `models.py`：RAG ORM 表。
- `repository.py`：RAG 数据仓库。
- `service.py`：索引、搜索、上下文构建。

规则：

- RAG 不自建模型请求体系，embedding 统一复用 `core/models`。
- RAG 存储表变更必须同步 `docs/data.sql`。
- RAG 不直接参与聊天请求，聊天增强通过 API/service 显式启用。
- RAG ORM 和 Repository 必须放在 `storage`。

## 5. `src/ai/storage`

数据库存储层。

职责：

- `database.py`：数据库引擎、Session、初始化。
- `*_models.py`：SQLModel ORM。
- `*_repository.py`：数据访问。
- `prompt_models.py` / `prompt_repository.py`：提示词模板和版本存储。
- `rag_models.py` / `rag_repository.py`：RAG 文档、切片和向量存储。
- `__init__.py`：稳定导出。

规则：

- `storage` 不依赖 `api` 或 `core`。
- Repository 只做 CRUD 和查询，不写业务流程。
- 新增 ORM 表必须同步 `docs/data.sql`。
- API Key 等敏感信息不得明文入库。

## 6. `src/ai/config`

配置层只保留启动期最小配置，例如数据库路径、数据库 URL、加密 key。

规则：

- 业务配置以数据库为准。
- 业务模块不得散落调用 `os.getenv()`。
- 启动期配置通过 `base_config.py` 的 `BootstrapSettings` 获取。

## 7. `src/ai/security`

安全相关能力，例如 API Key 加密、密钥生成和解密。

规则：

- API Key 入库前必须加密。
- 缺少加密 key 时应失败，不自动降级为明文。

## 8. `src/ai/exception`

统一异常体系。

规则：

- 所有自定义异常继承 `BaseExceptions`。
- 各领域异常可以在本模块或领域模块定义，但必须使用统一基类。

## 9. `src/ai/utils`

无业务状态的通用工具。

适合放：

- HTTP 客户端封装。
- token 计数工具。
- pricing 计费工具。
- 文本脱敏、字符串处理、hashing。

不适合放：

- 数据库访问。
- 模型请求。
- 工具执行。
- RAG 索引流程。

## 10. CLI

CLI 是补充入口，不是主入口。

规则：

- CLI 复用 `api/services` 或 `core` 能力。
- CLI 不重新实现模型请求、工具执行、RAG 索引等业务流程。
- `main.py` 默认服务 FastAPI。

## 11. 新增功能落位

| 功能 | 位置 |
| --- | --- |
| FastAPI 路由 | `src/ai/api/routes/<name>.py` |
| API schema | `src/ai/api/schemas/<name>.py` |
| API 服务 | `src/ai/api/services/<name>_service.py` |
| HTML 页面 | `src/ai/api/templates/` |
| 静态资源 | `src/ai/api/static/` |
| 模型 provider | `src/ai/core/models/providers/` |
| 工具 | `src/ai/core/tools/` |
| MCP 能力 | `src/ai/core/tools/mcp/` |
| Skill 能力 | `src/ai/core/skils/` |
| 提示词能力 | `src/ai/core/prompts/` |
| RAG 能力 | `src/ai/rag/` |
| ORM 表 | `src/ai/storage/*_models.py` |
| Repository | `src/ai/storage/*_repository.py` |

## 12. 判断标准

新增代码前先问三件事：

1. 这是 HTTP 入口、业务能力、存储访问，还是通用工具？
2. 它是否绕过了现有 `core/models`、`core/tools`、`storage` 边界？
3. 它的数据库变化是否同步到了 `docs/data.sql`？

如果答案不清楚，先调整设计再写代码。

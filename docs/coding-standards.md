# AI Chat 编码规范

本文档约束当前 `src/ai` 架构下的编码方式。目标是减少重构漂移，让 FastAPI、core、tools、RAG、storage 能长期保持清晰边界。

## 1. 基本原则

- 单一职责：一个模块只承担一个明确职责。
- 文档优先：需求、schema、规范变更应同步文档。
- 数据库优先：业务配置和运行态数据以 SQLite 表为 source of truth。
- 复用现有边界：模型走 `core/models`，工具走 `core/tools`，存储走 `storage`。
- 不保留旧兼容：当前重构不要求兼容旧 `src/ai_chat`。

## 2. Python 规范

- Python 版本按 `pyproject.toml`：`>=3.13`。
- 使用现代类型语法：`list[str]`、`dict[str, Any]`、`X | None`。
- 新增函数和方法必须标注参数和返回值类型。
- 公共模块、公共类、公共函数必须写中文 docstring。
- 文件编码统一 UTF-8。
- 类名使用 `PascalCase`，函数、变量、文件名使用 `snake_case`。
- 常量使用大写下划线。

## 3. 导入规范

- 使用绝对导入，例如 `from src.ai.core.models import ModelClient`。
- 标准库、第三方、本地模块分组。
- 禁止 `from x import *`。
- 避免在 `__init__.py` 中执行复杂逻辑。
- 延迟导入只用于避免循环依赖、可选依赖或启动性能问题。

## 4. FastAPI 编码规范

- `routes/` 只处理 HTTP 层，不写业务逻辑。
- `services/` 负责调用 `core`、`rag`、`storage`。
- `schemas/` 使用 Pydantic，不直接暴露 ORM。
- 页面放 `templates/`，静态资源放 `static/`。
- 异常处理统一在 `api/errors.py`。
- 路由返回结构必须稳定，避免直接返回不可控第三方对象。

## 5. Core 编码规范

### 5.1 模型

- 所有模型请求统一走 `src/ai/core/models`。
- `core/models` 只负责请求和接收，不做 RAG、记忆、业务编排。
- token 统计和价格计算放独立工具模块。
- 新能力通过 `ModelCapability`、request/response 类型、provider registry 扩展。
- 新 provider 放 `core/models/providers/`。

### 5.2 工具

- 所有工具统一走 `src/ai/core/tools`。
- 内置工具、MCP 工具、未来 Skill 工具都必须进入统一注册表。
- 工具执行统一走 `ToolExecutor`，不能绕过审计。
- MCP 只放在 `core/tools/mcp`，不再新增 `core/mcp`。

### 5.3 Skill

- Skill 能力放在 `core/skils`。
- Skill 发现结果写入数据库 `skills` 表。
- Skill 挂载必须转换为 `ToolDefinition` 并进入统一工具注册表。
- Skill prompt 渲染使用 Jinja2。

### 5.4 RAG

- RAG 文件加载、切分、存储、检索放 `src/ai/rag`。
- RAG embedding 必须优先复用 `core/models`。
- 本地 hash embedding 只能作为 fallback，不能成为新的模型请求体系。
- RAG 表变更必须同步 `docs/data.sql`。

## 6. Storage 编码规范

- ORM 使用 SQLModel。
- Repository 继承 `BaseRepository`，只做数据访问。
- `database.py` 负责引擎、Session、初始化。
- 新 ORM 必须确保被 `init_database()` 导入注册。
- 数据库 schema 变更必须同步 `docs/data.sql` 和相关需求文档。
- 不在 storage 层写模型请求、工具执行、RAG 检索等业务流程。
- 所有 ORM 和 Repository 必须放在 `storage`，禁止放在 `core`、`rag`、`api`。

## 7. Prompt 编码规范

- 提示词领域能力放在 `core/prompts`。
- 提示词模板使用数据库保存，表定义在 `storage/prompt_models.py`。
- 提示词渲染使用 Jinja2，入口为 `PromptService`。
- 业务代码不得硬编码大段 prompt。
- Prompt 表变更必须同步 `docs/data.sql`。

## 8. 配置规范

- 启动期最小配置放 `config/base_config.py`。
- 业务配置存数据库，例如 providers、models、mcp_servers、skills、security_policies。
- 业务代码禁止直接 `os.getenv()`。
- API Key 必须加密保存，禁止明文入库。
- 缺失加密 key 应明确失败。

## 9. 异常规范

- 所有自定义异常必须继承 `BaseExceptions`。
- 禁止新增裸 `Exception` 子类。
- 异常必须提供可定位的 message 和 context。
- FastAPI 通过 `api/errors.py` 统一转换异常响应。

推荐：

```python
raise LLMException("模型不存在", context={"model_id": model_id})
```

禁止：

```python
raise Exception("error")
```

## 10. 工具函数规范

- `utils/` 只能放无业务状态的通用工具。
- 领域能力不要为了“复用”过早放进 `utils/`。
- token、pricing、http、redaction 这类跨领域基础能力可以放 `utils/`。
- 文件加载、RAG 分割、工具执行不属于 utils。

## 11. 文件大小和职责

- 文件出现多个不相关职责时必须拆分。
- Provider、Repository、Service、Schema、Route 分文件维护。
- 单文件不断增长时优先拆出类型、适配器、仓库、服务。
- 不创建 `misc.py`、`helper.py`、`common2.py` 这类无边界文件。

## 12. 测试和验证

改动后至少按影响面运行：

- Python 编译：`uv run python -m compileall -q src\ai main.py`
- SQL schema：`sqlite3 :memory: ".read docs/data.sql" "PRAGMA foreign_key_check;"`
- FastAPI 路由用 `TestClient` 验证。
- RAG、工具、模型 provider 这类能力至少写或运行一条端到端 smoke 测试。

## 13. 提交前自查

提交前检查：

1. 是否放在正确目录。
2. 是否绕过了 `core/models` 或 `core/tools`。
3. 是否新增了裸异常。
4. 是否直接读取环境变量。
5. 是否改了 ORM 但没改 `docs/data.sql`。
6. 是否 API 路由写了业务逻辑。
7. 是否一个文件承担了多个职责。

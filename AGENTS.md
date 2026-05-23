# 代码库指南

## 项目结构与模块组织

本仓库是一个基于 FastAPI 构建的 Python 3.13 AI 工作台。主应用代码位于 `src/ai`。HTTP 路由、schema、服务、模板和静态文件位于 `src/ai/api`；模型抽象位于 `src/ai/core/models`；工具和 MCP 集成位于 `src/ai/core/tools`；RAG 代码位于 `src/ai/rag`；SQLModel 存储位于 `src/ai/storage`；启动配置位于 `src/ai/config`；共享辅助函数位于 `src/ai/utils`。使用 `main.py` 作为本地应用入口点。项目文档和 schema 引用位于 `docs/`，特别是 `docs/data.sql`。`tests/` 目录存在但目前没有已提交的测试文件。

## 构建、测试和开发命令

- `uv sync` 从 `pyproject.toml` 和 `uv.lock` 安装运行时和开发依赖。
- `uv run python main.py` 启动 FastAPI 应用，地址为 `http://127.0.0.1:8000/`，启用热重载。
- `uv run python -m compileall -q src\ai main.py` 执行快速语法/导入编译检查。
- `uv run pytest` 在添加测试文件后运行测试。
- `sqlite3 :memory: ".read docs/data.sql" "PRAGMA foreign_key_check;"` 验证数据库 schema 一致性。

## 编码风格与命名规范

遵循 `docs/coding-standards.md` 中的标准。使用 UTF-8 编码文件和绝对导入，如 `from src.ai...`，以及现代类型提示（`list[str]`、`dict[str, Any]`、`X | None`）。类名使用 `PascalCase`，函数/文件/变量使用 `snake_case`，常量使用 `UPPER_SNAKE_CASE`。公共模块、类和函数应包含简洁的中文文档字符串。保持路由精简：HTTP 处理属于 `api/routes`，业务编排属于 `api/services`，模型调用属于 `core/models`，工具执行属于 `core/tools`。

## 测试指南

在 `tests/` 下使用 `pytest` 添加测试；文件命名为 `test_<feature>.py`，测试函数命名为 `test_<behavior>()`。对于 API 变更，优先使用 FastAPI `TestClient` 冒烟测试。对于存储或 ORM 变更，更新 `docs/data.sql` 并运行 SQLite 验证命令。对于 RAG、模型提供者和工具，至少覆盖一个最小端到端路径，或记录外部凭证阻止测试的原因。

## 提交与 Pull Request 指南

近期提交历史使用 Conventional Commit 前缀，如 `feat:`、`fix:`、`docs:`、`refactor:` 和 `chore:`。保持提交聚焦和祈使语气，例如 `fix: handle empty chat session id`。Pull request 应包含简短摘要、关联的 issue 或需求、运行的验证命令、UI 变更的截图，以及 schema/配置更新的说明。

## 安全与配置提示

不要提交 `.env`、`data/`、凭证或生成的缓存。业务代码不能直接调用 `os.getenv()`；使用配置/存储抽象。API 密钥必须在持久化前加密，schema 变更必须与 `docs/data.sql` 保持同步。
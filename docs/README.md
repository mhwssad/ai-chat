# AI Chat 文档索引

本目录保存项目需求、计划、数据库 schema 和工程规范。后续开发优先阅读本文档索引，再进入具体需求或实现。

## 1. 必读规范

- [项目结构规范](./project-structure-standards.md)
- [编码规范](./coding-standards.md)
- [架构约束](./architecture-constraints.md)
- [数据库 Schema](./data.sql)

## 2. 需求文档

- [MVP 范围](./requirements/01-mvp-scope.md)
- [聊天与模型](./requirements/02-chat-and-models.md)
- [工具、MCP 与 Skills](./requirements/03-tools-mcp-skills.md)
- [记忆](./requirements/04-memory.md)
- [Web 与 CLI](./requirements/05-web-and-cli.md)
- [存储、配置与审计](./requirements/06-storage-config-and-audit.md)
- [Agent Runtime 路线](./requirements/07-agent-runtime-roadmap.md)
- [数据模型](./requirements/data-model.md)
- [AI Workbench 总需求](./requirements/ai-workbench-requirements.md)

## 3. 实施计划

- [MVP 实施计划](./plans/01-mvp-implementation-plan.md)
- [MVP 任务列表](./plans/01-mvp-task-list.md)
- [第二阶段待办](./plans/02-phase2-todo.md)

## 4. 当前架构摘要

当前项目以 FastAPI 为主入口，CLI 为补充入口：

- `src/ai/api`：FastAPI、HTML、API schema、API services。
- `src/ai/core/models`：通用多供应商多模型请求。
- `src/ai/core/tools`：统一工具注册和执行，包含 MCP。
- `src/ai/rag`：文件索引、文本切分、向量存储和检索。
- `src/ai/storage`：数据库连接、ORM、Repository。
- `src/ai/config`：启动期最小配置。
- `src/ai/security`：加密和安全能力。
- `src/ai/exception`：统一异常。

## 5. 开发流程

新增功能前：

1. 阅读对应需求文档。
2. 阅读项目结构规范，确认目录落位。
3. 阅读编码规范和架构约束，确认没有违反红线。
4. 若涉及数据库，先更新 `docs/data.sql`。
5. 实现后运行最小验证命令。

## 6. 常用验证

```powershell
uv run python -m compileall -q src\ai main.py
sqlite3 :memory: ".read docs/data.sql" "PRAGMA foreign_key_check;"
```

涉及 FastAPI 路由时，使用 `fastapi.testclient.TestClient` 做 smoke test。

涉及 RAG、工具、模型 provider 时，至少跑一条端到端最小路径。

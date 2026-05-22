# Dependency Policy And Audit

## 1. 目标

本文档记录当前项目依赖的整理原则和本次依赖评估结论。依赖管理应服务于 AI Workbench 的 MVP 目标：本地优先、多供应商聊天、Web/CLI 共享核心、SQLite 运行态数据、工具/MCP/skills 边界和后续 Agent Runtime 扩展。

## 2. 依赖分层原则

### 2.1 主依赖

主依赖是当前代码直接导入，或 MVP 启动路径需要立即可用的依赖。

适合放入主依赖：

- Web 服务框架。
- 模型供应商适配。
- LangChain/LangGraph 基础能力。
- MCP 基础能力。
- 配置、模板、SQLite ORM、HTTP、重试、熔断、token 计数。
- 当前代码直接导入的解析和表单依赖。

### 2.2 可选依赖

可选依赖是后续能力或重型能力需要的依赖，不应默认拖慢 MVP 安装。

适合放入可选依赖：

- FAISS 向量索引。
- HuggingFace 本地 embedding。
- 后续项目知识库和高级 RAG 能力。

### 2.3 开发依赖

开发依赖只用于代码质量、类型检查、测试和本地开发，不应进入运行时主依赖。

当前开发依赖包括：

- `pytest`：运行测试套件。
- `ruff`：代码检查和格式相关工具。
- `mypy`：类型检查。

## 3. 本次补充的主依赖

本次也保留了当前工作区中已经刷新过的主依赖版本下限，并通过 `uv lock` 重新解析锁文件。

- `python-multipart`：FastAPI 路由使用 `Form`，表单解析需要显式依赖。
- `langchain-text-splitters`：RAG splitter 模块直接导入。
- `pydantic`：项目直接使用 `BaseModel` 和 `SecretStr`。
- `pyyaml`：skills frontmatter 和模型配置种子读取直接使用 YAML。
- `sqlalchemy`：多个存储模块直接使用 SQLAlchemy API。

## 4. 本次补充的开发依赖

- `pytest`：项目已有 `tests/`，但开发依赖未显式声明测试运行器。

## 5. 本次新增的可选依赖

- `faiss-cpu`：FAISS 向量存储运行时需要，但属于项目知识库/RAG 增强能力。
- `langchain-huggingface`：本地 HuggingFace embedding 运行时需要，但不属于 MVP 必需路径。

安装 RAG 增强能力时使用：

```powershell
uv sync --extra rag
```

## 6. 本次未移除的依赖

以下依赖虽然较重，但当前代码已有直接使用或属于 MVP/近期路线核心能力，因此暂不移除：

- `langchain`
- `langchain-openai`
- `langchain-google-genai`
- `langchain-anthropic`
- `langchain-ollama`
- `langchain-community`
- `langgraph`
- `langchain-mcp-adapters`
- `mcp`
- `fastapi`
- `jinja2`
- `sqlmodel`
- `pydantic-settings`
- `uvicorn`
- `tiktoken`
- `httpx`
- `tenacity`
- `pybreaker`

## 7. 暂不引入的依赖

- `typer`：当前 CLI 是交互式 `main.py`，尚未改造为子命令式 CLI。等 CLI MVP 实现时再引入，避免提前增加未使用依赖。
- `aiosqlite`：需求文档要求异步存储接口，但当前存储实现仍以 SQLModel 同步访问为主。等存储层进入异步改造时再引入。

## 8. 后续评估点

- CLI MVP 开始实现时，重新评估是否引入 `typer`。
- SQLite 异步存储开始实现时，重新评估是否引入 `aiosqlite` 或 SQLAlchemy async stack。
- 项目知识库开始实现时，确认是否把 `rag` 可选依赖纳入默认安装。
- 若某个供应商长期不用，可考虑把对应 provider 依赖拆到 optional extras。

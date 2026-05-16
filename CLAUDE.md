# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概览

AI Chat — 基于 LangChain/LangGraph 生态的多提供商 AI 聊天框架，提供 CLI 交互界面和 FastAPI Web 骨架。Python >= 3.13，使用 uv 管理依赖。

## 常用命令

```bash
# 安装依赖
uv sync

# 运行 CLI
python main.py

# 运行 Web（FastAPI 骨架）
uv run uvicorn src.ai_chat.web.app:create_app --factory --reload

# 代码检查
ruff check src/
ruff format src/

# 类型检查
mypy src/

# 运行测试（无 pytest 配置，直接执行）
python -m pytest tests/

# 运行单个测试文件
python -m pytest tests/tools/test_registry.py
```

## 架构与核心设计模式

项目采用 **注册 + 工厂 + 策略** 三层扩展模式，所有扩展点遵循统一流程：定义 ABC 接口 → 实现具体 Provider → 装饰器自动注册 → 工厂按名路由。

### 装饰器自动注册机制

这是项目最核心的扩展方式——导入模块时装饰器自动将类注册到全局工厂，无需手动维护注册表：

- **LLM Provider**: `@register_chat(name, config_fn)` / `@register_embedding(name, config_fn)` — 类装饰器，在 `llm/providers/` 中使用。注册时通过 `SUPPORTED_MODELS` 类变量自动建立 model_name → provider 的路由映射。
- **工具**: `@registered_tool(tool_type=ToolType.SYSTEM)` — 函数装饰器，等价于 LangChain `@tool` + 自动注册到 `tool_registry`。
- **记忆后端**: `@register_memory(name)` — 类装饰器，在 `memory/providers/` 中使用。

### 全局单例

- `llm_factory`（`src.ai_chat/llm/factory.py`）— 抽象工厂，支持泛型 provider_type（chat/embedding/image/video），按 model_name 自动路由到正确 Provider
- `tool_registry`（`src.ai_chat/tools/registry.py`）— 单例工具注册表，系统工具自动加载，自定义工具按名懒加载
- `prompt_registry`（`src.ai_chat/prompts/registry.py`）— 提示词内存注册表
- `settings`（`src/ai_chat/config/settings.py`）— pydantic BaseSettings 全局配置

### 分层架构

```
graphs/     → LangGraph 状态图编排（Agent 层）— 调用下层能力，不直接操作 SDK 或存储
chains/     → LCEL 轻量调用链
llm/        → 模型抽象 + 工厂 + Provider（providers/ 下按供应商分文件）
memory/     → 会话记忆（ConversationMemory 单会话 / SessionManager 多会话）
rag/        → RAG 管线（loaders/ splitters/ stores/ 子目录按扩展点分离）
prompts/    → Jinja2 提示词管理（数据库持久化 + 版本历史 + 内置种子数据）
tools/      → 工具注册 + 内置系统工具（文件/目录/搜索/命令）
skills/     → 技能插件（每个技能一个目录 + SKILL.md frontmatter）
mcp/        → MCP 客户端/服务端适配
config/     → 全局配置、日志、异常、基础枚举
```

### Graph 层 Agent 编排

- **UnifiedAgent** — 完整代理：意图分类节点 → 条件路由到 ReAct 节点（工具调用）或 RAG 节点（检索问答），集成记忆管理
- **MemoryAgent** — ReAct + 对话记忆
- **ChatGraph** — 意图分类 → 对话 / RAG 路由

Graph 层使用 `TypedDict` 定义状态，`StateGraph` 编排节点和条件边。

### 提示词系统

提示词通过 `PromptManager` 持久化到 SQLite，支持 Jinja2 模板语法（for/if/include 等）。首次启动从 `builtin_data.py` 导入种子数据。提示词内容支持 `== role ==` 分隔的多消息格式。模板通过 `PromptStore` CRUD + 内存注册表 + LRU 缓存三层管理。

### 记忆系统

`ConversationMemory` 是核心编排器：
- Token 感知的上下文压缩（tiktoken 计数 + 模型上下文窗口阈值）
- 短期消息窗口 + 自动摘要压缩
- SQLite / 内存两种后端（通过 `memory_factory` 路由）

## 编码规范要点

- 注释和文档字符串使用中文，类名/函数名/文件名使用英文
- 所有新增函数必须补充参数和返回值类型标注
- 使用现代类型语法：`list[str]`、`X | None`（Python 3.13）
- 公共类和函数必须有中文 docstring
- 配置统一通过 `config/settings.py` 管理，不散落 `os.getenv()` 调用
- 抛出项目领域异常（如 `ModelNotSupportedException`），不抛裸 `Exception`
- 异步优先设计同步包装，同步包装注意事件循环处理（参考 `UnifiedAgent.invoke`）

## 新增功能落位

| 新增内容 | 放置位置 |
|---------|---------|
| LLM 供应商 | `llm/providers/chat/<name>.py`，使用 `@register_chat` |
| 嵌入供应商 | `llm/providers/embedding/<name>.py`，使用 `@register_embedding` |
| 工具 | `tools/<name>.py`，使用 `@registered_tool` |
| 技能 | `skills/skills/<name>/SKILL.md` |
| 记忆后端 | `memory/providers/<name>.py` |
| RAG 组件 | `rag/loaders/`、`rag/splitters/`、`rag/stores/` 按类型分 |
| Agent/图 | `graphs/<name>.py` |

## 环境配置

根目录 `.env` 文件，支持多提供商 API Key。默认模型 `minmax-2.7`。配置通过 pydantic `BaseSettings` 自动加载，支持 `settings.refresh()` 热重载和 `settings.save_to_env_file()` 回写。

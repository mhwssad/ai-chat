# AI Chat

基于 LangChain 生态的多提供商 AI 聊天框架，提供统一的 CLI 交互界面。

## 功能特性

- **多 LLM 提供商** — 支持 OpenAI、Anthropic Claude、Google Gemini、Ollama（本地）、Minimax、阿里通义千问
- **智能代理** — 基于 LangGraph 的 ReAct 代理，支持工具调用和意图分类路由
- **RAG 检索增强生成** — 文档加载、文本分块、FAISS 向量存储、检索问答
- **对话记忆** — SQLite 持久化、短期记忆 + 自动摘要、会话管理
- **MCP 集成** — 连接外部 MCP 工具服务器，或将内置工具暴露为 MCP 服务
- **技能系统** — 基于 Markdown 的插件式斜杠命令，支持自定义系统提示词和工具绑定
- **调用链** — 预置 LCEL 链：对话、摘要、翻译、信息抽取、内容优化
- **内置工具** — 提供项目内文件、目录、搜索和只读命令查询能力

## 快速开始

### 环境要求

- Python >= 3.13
- [uv](https://docs.astral.sh/uv/) 包管理器

### 安装

```bash
git clone <repo-url>
cd ai-chat
uv sync
```

### 配置

在项目根目录创建 `.env` 文件，填入需要的 API Key：

```env
MODEL_NAME=gpt-4o

# LLM 提供商（按需配置）
OPENAI_API_KEY=sk-xxx
ANTHROPIC_API_KEY=sk-ant-xxx
GOOGLE_API_KEY=xxx
QWEN_API_KEY=sk-xxx
MINMAX_API_KEY=sk-cp-xxx
OLLAMA_BASE_URL=http://localhost:11434

# MCP（可选）
MCP_ENABLED=true
```

### 运行

```bash
python main.py
```

启动后进入交互式菜单：

```text
=== AI Chat ===
  1. 对话
  2. 调用链
  3. 工具管理
  4. 记忆管理
  5. MCP 管理
  6. 技能管理
  7. 退出
```

## 项目结构

```text
src/ai_chat/
├── config/       # 配置管理、日志、异常
├── llm/          # LLM 提供商抽象层（工厂 + 装饰器自动注册）
│   └── providers/  # OpenAI / Claude / Gemini / Ollama / Minimax / Qwen
├── chains/       # LCEL 可复用调用链
├── graphs/       # LangGraph 代理（ChatAgent / MemoryAgent / UnifiedAgent）
├── tools/        # 工具注册中心 + 文件/目录/搜索/只读命令工具
├── memory/       # 对话记忆（SQLite / 内存后端）
├── rag/          # RAG 管线（加载器 / 分块器 / 向量库 / 链）
├── mcp/          # MCP 客户端 + 服务端
├── prompts/      # Jinja2 提示词模板注册
└── skills/       # 技能插件系统
```

## 支持的 LLM 提供商

| 提供商    | 聊天模型    | Embedding              |
| --------- | ----------- | ---------------------- |
| OpenAI    | GPT-4o 等   | text-embedding-3-small |
| Anthropic | Claude 系列 | -                      |
| Google    | Gemini 系列 | -                      |
| Ollama    | 本地模型    | nomic-embed-text       |
| Minimax   | M2.7        | -                      |
| 通义千问  | Qwen 系列   | -                      |

## 内置代理

| 代理         | 说明                                 |
| ------------ | ------------------------------------ |
| ChatAgent    | ReAct 模式，支持工具调用             |
| ChatGraph    | 意图分类 → 对话 / RAG 路由           |
| MemoryAgent  | ReAct + 对话记忆                     |
| UnifiedAgent | 记忆 + 工具 + RAG + 技能，全功能代理 |

## 内置调用链

- **对话链** — 基础多轮对话
- **摘要链** — 长文本自动摘要
- **翻译链** — 多语言翻译
- **信息抽取** — 结构化信息提取
- **内容优化** — 文本润色与改写

## 内置工具

- **文件工具** — 读取、按行读取、覆盖写入、追加写入、精确替换、正则替换
- **目录工具** — 列出目录、查看路径信息、创建目录、按 glob 查找文件
- **搜索工具** — 在项目目录内按文本搜索文件内容
- **只读命令工具** — 通过 `run_command` 执行白名单内的 PowerShell 查询命令

说明：

- 所有内置工具默认限制在项目根目录及其子目录内运行
- `run_command` 仅用于只读查询，不是通用 shell

## Web 界面

当前仓库已移除内置 Streamlit UI。

后续页面层建议使用 FastAPI + Vue 独立承载，核心对话、调用链、工具、记忆和 MCP 能力继续复用 `src/ai_chat/` 下的业务模块。

当前已提供一版基于 FastAPI + Jinja2 的最小 Web 骨架，可作为后续页面层的起点。

### 启动 Web 骨架

```bash
uv run uvicorn src.ai_chat.web.app:create_app --factory --reload
```

启动后可访问：

- `/chat`：最小聊天页面（MemoryAgent / UnifiedAgent）
- `/chains` `/tools` `/memory` `/mcp` `/skills`：占位页面

## 设计模式

- **策略模式** — 所有 Provider 均基于 ABC 接口，可自由替换实现
- **抽象工厂** — LLMFactory / MemoryFactory / RAGFactory / AgentFactory / ChainFactory
- **装饰器自动注册** — `@register_chat` / `@register_embedding` / `@register_memory` / `@registered_tool` 导入即注册
- **单例** — 工具注册表、技能注册表、提示词注册表等全局唯一

## 开发

```bash
# 代码检查
ruff check src/
ruff format src/

# 类型检查
mypy src/
```

## 依赖

核心依赖：`langchain` / `langgraph` / `langchain-openai` / `langchain-anthropic` / `langchain-google-genai` / `langchain-ollama` / `langchain-mcp-adapters` / `mcp` / `sqlmodel` / `jinja2`

开发依赖：`ruff` / `mypy`

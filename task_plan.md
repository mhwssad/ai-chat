# 任务计划：完善 API 路由覆盖全部功能

## 目标

为 AI Chat 项目补全所有功能模块的 API 路由，从当前 8 个端点扩展到覆盖全部核心能力。

## 现状分析

### 已有路由（8 个端点）
| 模块 | 前缀 | 端点数 | 状态 |
|------|------|--------|------|
| 对话 | /api/chat | 3 | ✅ 完成 |
| 系统 | /api/system | 2 | ✅ 完成 |
| 工具 | /api/tools | 3 | ✅ 完成 |

### 待新增路由（10 个模块）
| 模块 | 前缀 | 核心服务来源 | Service 层 |
|------|------|-------------|-----------|
| RAG | /api/rag | core/rag/service.py | 需新建 |
| Agent | /api/agent | core/agent/ | 需新建 |
| 提示词 | /api/prompts | core/prompts/service.py | 需新建 |
| 记忆 | /api/memory | core/memory/service.py | 需新建 |
| 模型管理 | /api/models | core/models/ + storage/ | 需新建 |
| 会话 | /api/sessions | storage/runtime_models.py | 需新建 |
| 图片 | /api/image | service/image_service.py | 已有 |
| TTS | /api/tts | service/tts_service.py | 已有 |
| 调度器 | /api/scheduler | core/scheduler/service.py | 需新建 |
| 技能 | /api/skills | core/skills/ | 需新建 |

## 实施阶段

### 阶段一：基础设施准备
- [ ] 1.1 扩展 `ServiceContainer`，注册所有新服务
- [ ] 1.2 扩展 `AppContainer.wiring_config`，添加所有新路由模块
- [ ] 1.3 统一分页、错误响应 Schema

### 阶段二：新建 Service 层（6 个服务）
- [ ] 2.1 `src/ai/service/rag_service.py` — 包装 core/rag
- [ ] 2.2 `src/ai/service/agent_service.py` — 包装 core/agent
- [ ] 2.3 `src/ai/service/prompt_service.py` — 包装 core/prompts
- [ ] 2.4 `src/ai/service/memory_service.py` — 包装 core/memory
- [ ] 2.5 `src/ai/service/model_config_service.py` — 模型/供应商 CRUD
- [ ] 2.6 `src/ai/service/session_service.py` — 会话管理
- [ ] 2.7 `src/ai/service/scheduler_service.py` — 包装 core/scheduler
- [ ] 2.8 `src/ai/service/skill_service.py` — 包装 core/skills

### 阶段三：新建 Schema 层（10 个模块）
- [ ] 3.1 rag.py
- [ ] 3.2 agent.py
- [ ] 3.3 prompts.py
- [ ] 3.4 memory.py
- [ ] 3.5 models.py
- [ ] 3.6 sessions.py
- [ ] 3.7 image.py
- [ ] 3.8 tts.py
- [ ] 3.9 scheduler.py
- [ ] 3.10 skills.py
- [ ] 3.11 common.py（分页、错误等通用 Schema）

### 阶段四：新建 Route 层（10 个模块）
- [ ] 4.1 rag.py — 文档索引、检索、管理
- [ ] 4.2 agent.py — Agent 执行、取消、恢复、状态
- [ ] 4.3 prompts.py — 模板 CRUD、渲染、版本管理
- [ ] 4.4 memory.py — 记忆 CRUD、搜索、提取
- [ ] 4.5 models.py — 供应商/模型 CRUD、测试
- [ ] 4.6 sessions.py — 会话列表、详情、归档
- [ ] 4.7 image.py — 图像生成、列表、删除
- [ ] 4.8 tts.py — 语音合成、列表、删除
- [ ] 4.9 scheduler.py — 定时任务 CRUD、执行日志
- [ ] 4.10 skills.py — 技能列表、详情、启禁

### 阶段五：注册和验证
- [ ] 5.1 路由注册到 `api_router`
- [ ] 5.2 编译检查 `compileall`
- [ ] 5.3 `ruff check` + `ruff format`
- [ ] 5.4 启动验证 `uv run python main.py`

## 设计决策

1. **Service 层位置**：放在 `src/ai/service/`，与已有 ChatService/ToolService 同级
2. **DI 注入**：所有新服务注册到 `ServiceContainer`，路由通过 `@inject` 注入
3. **直接注入 vs 包装**：对于已有完善接口的 core 服务（PromptService、MemoryService、RagService、SchedulerService），service 层做薄包装主要用于类型转换和异常处理
4. **异步一致性**：所有路由端点使用 `async def`，service 方法提供异步版本

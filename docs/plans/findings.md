# 研究发现

> 创建时间：2026-06-07

---

## 1. 代码库现状分析

### 1.1 Agent 核心模块 (`src/ai/core/agent/`)

| 文件 | 职责 | 行数 |
|------|------|------|
| `orchestrator.py` | LangGraph StateGraph ReAct 循环，733 行 | 核心 |
| `state.py` | `GraphState(TypedDict)` 11 个状态字段 | 状态定义 |
| `types.py` | `AgentStatus`(7种)、`ToolCall`、`AgentTraceStep`、`AgentResult` | 类型 |
| `checkpoint.py` | `CheckpointManager` 封装 LangGraph checkpointer | 持久化 |
| `container.py` | DI 容器 `AgentContainer` | 依赖注入 |

**关键发现：**
- `AgentOrchestrator.run()` 接受 `session_id, user_message, system_prompt, max_iterations, tools, agent_timeout`
- 图结构：`START → context_builder → llm_call -[有工具]→ tools → plan_mode_check -[继续]→ llm_call`
- 工具执行已通过 `TimeoutToolNode(ToolNode)` 支持 `ainvoke()` 并行
- 已有 `AgentTraceStep` 类型但未完整集成到存储层
- `_build_result()` 从最终 `GraphState` 构建 `AgentResult`，无质量自检

### 1.2 工具子系统 (`src/ai/core/tools/`)

**关键发现：**
- `ToolRegistry` 纯数据存储，维护 `dict[str, BaseTool]` + `dict[str, ToolMeta]`
- `ToolManager` 编排层：执行 `execute()` 带权限校验 + 超时
- `PermissionChecker` 已有三级权限：`AUTO`/`CONFIRM`/`DENY`
- `TimeoutToolNode` 继承 LangGraph `ToolNode`，已支持并行工具执行（`ainvoke()` 内部 `asyncio.gather`）
- 13 个内置工具，分为无依赖（导入自注册）和有依赖（工厂注册）

### 1.3 安全模块 (`src/ai/security/`)

- 仅有 `crypto.py`（Fernet 加密），缺少沙箱和权限分级

### 1.4 记忆子系统 (`src/ai/core/memory/`)

- 13 个文件，`MemoryService` 统一门面
- 文件系统存储 + Chroma 向量索引 + SQL 控制面
- 三层搜索：向量召回 → 关键词补充 → LLM 精排
- 缺少工作记忆（scratchpad）概念

### 1.5 存储层 (`src/ai/storage/`)

- 16 张 ORM 表，`BaseRepository[T]` 泛型基类
- 已有 `AuditLog` 表可扩展
- 需新增 `agent_trace` 表用于执行链路追踪

---

## 2. 架构约束（硬约束）

来源：`docs/requirements/08-system-architecture.md` + `CLAUDE.md`

1. **五层架构**：Interaction → Shared Service → Core Capability → Storage → Infrastructure
2. **DI 组合根**：`AppContainer` 为唯一组合根
3. **异步优先**：阻塞型任务走统一线程池
4. **分层调用**：禁止路由直接写业务逻辑，禁止绕过 core 层
5. **异常体系**：所有自定义异常继承 `BaseExceptions`
6. **ORM 同步**：schema 变化必须同步 `docs/data.sql`

---

## 3. 实现策略

### 3.1 渐进式集成策略

每个增强通过配置开关控制，默认关闭，不影响现有功能：

```python
# config/settings.py 中新增 AgentSettings
class AgentSettings(BaseModel):
    reflection_enabled: bool = False
    reflection_max_rounds: int = 2
    recovery_enabled: bool = False
    sandbox_enabled: bool = False
    tracing_enabled: bool = False
    parallel_tools_enabled: bool = True
    working_memory_enabled: bool = False
```

### 3.2 依赖关系图

```
1.1 反思循环 ─────┐
                  ├──→ 1.2 错误恢复
                  │
1.3 并行编排 ─────┼──→ 3.2 工具组合
                  │
2.3 执行追踪 ─────┤
                  │
2.1 沙箱 ────→ 2.2 权限分级
                  │
3.3 工作记忆 ─────┘
                  │
1.1 + 1.2 ──→ 3.1 多 Agent
```

### 3.3 文件影响范围评估

| 增强项 | 新增文件 | 修改文件 | 风险 |
|--------|---------|---------|------|
| 1.1 反思循环 | `reflection.py` | `orchestrator.py`, `state.py`, `types.py` | 中 |
| 1.2 错误恢复 | `recovery.py` | `orchestrator.py`, `registry.py`, `types.py` | 中 |
| 1.3 并行编排 | - | `orchestrator.py` | 低（已有基础） |
| 2.1 沙箱 | `sandbox.py` | `manager.py`, `types.py` | 中高 |
| 2.2 权限分级 | `policy.py` | `permissions.py`, `manager.py` | 中 |
| 2.3 执行追踪 | `tracer.py` | `orchestrator.py`, 新增存储模型 | 中 |
| 3.1 多 Agent | `multi/` 目录 | `orchestrator.py`, `container.py` | 高 |
| 3.2 工具组合 | `pipeline.py` | `manager.py`, `types.py` | 中 |
| 3.3 工作记忆 | `working.py` | `service.py`, `state.py` | 中 |

# Agent 增强实施计划

> 创建时间：2026-06-07
> 基线：master 分支
> 来源：`docs/plans/agent-enhancement-roadmap.md`

---

## 状态总览

| 阶段 | 能力域 | 状态 | 预计文件数 |
|------|--------|------|-----------|
| 一 | 1.1 自我反思循环 | 🔲 未开始 | 新增 1 + 修改 4 |
| 一 | 1.2 错误恢复与重试 | 🔲 未开始 | 新增 1 + 修改 4 |
| 一 | 1.3 并行工具编排 | 🔲 未开始 | 修改 2 |
| 二 | 2.1 沙箱执行环境 | 🔲 未开始 | 新增 1 + 修改 3 |
| 二 | 2.2 权限分级控制 | 🔲 未开始 | 新增 1 + 修改 4 |
| 二 | 2.3 执行链路追踪 | 🔲 未开始 | 新增 2 + 修改 3 |
| 三 | 3.1 多 Agent 协作 | 🔲 未开始 | 新增 4 + 修改 3 |
| 三 | 3.2 工具组合编排 | 🔲 未开始 | 新增 1 + 修改 3 |
| 三 | 3.3 长期工作记忆 | 🔲 未开始 | 新增 1 + 修改 3 |

---

## 阶段一：核心智能增强

### 1.1 自我反思循环

**目标**：执行完成后自检，发现不足则自动重试或补充

**实现步骤**：

1. **新增 `src/ai/core/agent/reflection.py`**
   - `ReflectionLoop` 类，封装"执行→评估→改进"循环
   - 评估维度：完整性（回答是否充分）、准确性（事实是否正确）、意图满足（是否回答了用户问题）
   - 支持最大反思轮次配置（默认 2 轮）
   - 反思过程中允许补充工具调用

2. **修改 `src/ai/core/agent/state.py`**
   - 新增状态字段：`reflection_count: int`、`reflection_history: list[dict]`、`needs_reflection: bool`

3. **修改 `src/ai/core/agent/orchestrator.py`**
   - 在 `_build_graph()` 中新增 `reflection` 节点和条件边
   - 图结构扩展：`...→ llm_call → [有反思] → reflection → llm_call`
   - 新增配置参数 `reflection_enabled`、`reflection_max_rounds`

4. **修改 `src/ai/core/agent/types.py`**
   - `AgentResult` 新增 `reflections: list[ReflectionResult]` 字段
   - 新增 `ReflectionResult` 数据类

5. **修改 `src/ai/config/settings.py`**
   - 新增 `AgentSettings` 配置域（或扩展 `LLMSettings`）

**文件清单**：
- 新增：`src/ai/core/agent/reflection.py`
- 修改：`state.py`、`orchestrator.py`、`types.py`、`config/settings.py`

---

### 1.2 错误恢复与重试策略

**目标**：失败时自动重试、换工具、换参数、或询问用户

**依赖**：1.1（反思循环中的重试可复用）

**实现步骤**：

1. **新增 `src/ai/core/tools/recovery.py`**
   - `RecoveryStrategy` 枚举：`RETRY`、`FALLBACK`、`REPLAN`、`ASK_USER`
   - `RecoveryConfig` 数据类：策略 + 最大重试次数 + 回退映射
   - `RecoveryManager` 类：根据错误类型选择恢复策略并执行

2. **修改 `src/ai/core/tools/registry.py`**
   - `ToolMeta` 新增 `fallback_tool: str | None` 字段
   - 支持工具注册时声明 fallback

3. **修改 `src/ai/core/agent/orchestrator.py`**
   - 工具执行异常捕获后调用 `RecoveryManager`
   - 恢复事件注入 `GraphState`

4. **修改 `src/ai/core/agent/state.py`**
   - 新增 `recovery_history: list[RecoveryEvent]` 字段

5. **修改 `src/ai/core/callbacks/audit.py`**
   - 新增审计事件类型：`tool_recovery`

**文件清单**：
- 新增：`src/ai/core/tools/recovery.py`
- 修改：`registry.py`、`orchestrator.py`、`state.py`、`audit.py`

---

### 1.3 并行工具编排

**目标**：识别无依赖的工具调用并并行执行

**实现步骤**：

1. **修改 `src/ai/core/agent/orchestrator.py`**
   - 新增 `DependencyAnalyzer` 内部类，分析工具调用间的数据依赖
   - 依赖判断逻辑：如果工具 B 的参数引用了工具 A 的输出，则 B 依赖 A
   - 将无依赖的工具调用分组并行执行
   - 新增配置 `parallel_tools_enabled`（默认 True）

2. **修改 `src/ai/core/tools/timeout_node.py`**
   - 确认 `ainvoke()` 已支持并行，可能需要优化分组逻辑
   - 添加分组执行支持：接收分组信息，组内并行、组间串行

**文件清单**：
- 修改：`orchestrator.py`、`timeout_node.py`

---

## 阶段二：安全与可观测性

### 2.1 沙箱执行环境

**目标**：代码执行和文件操作在沙箱中运行

**实现步骤**：

1. **新增 `src/ai/core/tools/sandbox.py`**
   - `SandboxConfig` 数据类：目录白名单、域名白名单、超时、内存限制
   - `SubprocessSandbox` 类：`subprocess` 隔离模式（最低可行方案）
   - `FileSystemSandbox` 类：限制可访问的目录白名单
   - `NetworkSandbox` 类：限制可访问的域名/IP 白名单
   - `SandboxExecutor` 统一入口

2. **修改 `src/ai/core/tools/types.py`**
   - `ToolMeta` 新增 `requires_sandbox: bool` 字段

3. **修改 `src/ai/core/tools/manager.py`**
   - `execute()` 方法根据 `requires_sandbox` 选择直接执行或沙箱执行

4. **修改 `src/ai/core/tools/builtins/shell_tools.py`**
   - 标记为 `requires_sandbox=True`

**文件清单**：
- 新增：`src/ai/core/tools/sandbox.py`
- 修改：`types.py`、`manager.py`、`builtins/shell_tools.py`

---

### 2.2 权限分级控制

**目标**：细粒度的权限控制，支持自动批准/人工审批/拒绝

**依赖**：2.1（沙箱内的操作可降低权限等级）

**实现步骤**：

1. **新增 `src/ai/security/policy.py`**
   - `PermissionLevel` 枚举：`AUTO`/`CONFIRM`/`DENY`
   - `PermissionRule` 数据类：工具类型 + 参数模式 → 权限等级
   - `PermissionPolicy` 类：策略文件加载 + 规则匹配引擎
   - 默认策略：敏感操作（文件删除、网络请求、代码执行）需确认

2. **修改 `src/ai/core/tools/permissions.py`**
   - 重构 `PermissionChecker` 使用 `PermissionPolicy` 引擎
   - 支持参数模式匹配（如 `file_write:path=/etc/*` → DENY）

3. **修改 `src/ai/core/tools/manager.py`**
   - 集成新权限策略

4. **修改 `src/ai/cli/tabs/tools_tab.py`**
   - 展示权限规则管理界面

5. **修改 `src/ai/api/routes/`**
   - 新增权限策略 CRUD API 端点

**文件清单**：
- 新增：`src/ai/security/policy.py`
- 修改：`permissions.py`、`manager.py`、`tools_tab.py`、API routes

---

### 2.3 执行链路追踪

**目标**：完整的 Agent 决策链路可视化

**实现步骤**：

1. **新增 `src/ai/core/callbacks/tracer.py`**
   - `TraceRecorder` 类：每次请求生成唯一 `trace_id`
   - 记录步骤：推理→工具选择→参数构造→执行→结果→下一步推理
   - 结构化存储到 DB

2. **新增 `src/ai/storage/trace_models.py`**
   - `AgentTrace` ORM 模型：trace_id、session_id、status、开始/结束时间
   - `AgentTraceStep` ORM 模型：trace_id、step_index、step_type、input/output、duration

3. **新增 `src/ai/storage/trace_repository.py`**
   - `TraceRepository`、`TraceStepRepository`

4. **修改 `src/ai/core/agent/orchestrator.py`**
   - 集成 `TraceRecorder`，在每个节点记录步骤

5. **修改 `docs/data.sql`**
   - 新增 `agent_traces` 和 `agent_trace_steps` 表

6. **修改 `src/ai/api/routes/`**
   - 新增 trace 查询 API 端点

**文件清单**：
- 新增：`tracer.py`、`trace_models.py`、`trace_repository.py`
- 修改：`orchestrator.py`、`data.sql`、API routes

---

## 阶段三：高级协作能力

### 3.1 多 Agent 协作框架

**目标**：多个专业 Agent 分工合作

**依赖**：1.1（反思能力）、1.2（错误恢复）

**实现步骤**：

1. **新增 `src/ai/core/agent/roles.py`**
   - `AgentRole` 枚举：`ROUTER`/`CODER`/`RESEARCHER`/`REVIEWER`
   - `AgentProfile` 数据类：角色 + system prompt + 可用工具集 + 权限

2. **新增 `src/ai/core/agent/router.py`**
   - `AgentRouter` 类：分析用户意图，分发给最合适的 Agent

3. **新增 `src/ai/core/agent/handoff.py`**
   - `AgentHandoff` 类：Agent 间的任务交接协议（含上下文传递）

4. **新增 `src/ai/core/agent/team.py`**
   - `AgentTeam` 类：编排多 Agent 协作
   - 支持"编排者-执行者"模式和"辩论"模式

5. **修改 `src/ai/core/agent/orchestrator.py`**
   - 集成多 Agent 路由

6. **修改 `src/ai/core/agent/container.py`**
   - 注册多 Agent 相关依赖

**文件清单**：
- 新增：`roles.py`、`router.py`、`handoff.py`、`team.py`
- 修改：`orchestrator.py`、`container.py`

---

### 3.2 工具组合编排

**目标**：将多个工具编排成 pipeline 或 workflow

**依赖**：1.3（并行执行）

**实现步骤**：

1. **新增 `src/ai/core/tools/pipeline.py`**
   - `ToolPipeline` 类：工具链声明（输入→转换→输出）
   - 支持常见组合模式：搜索→提取→总结、读取→分析→生成
   - 缓存中间结果

2. **修改 `src/ai/core/tools/manager.py`**
   - 支持注册和执行 pipeline

3. **修改 `src/ai/core/tools/types.py`**
   - 新增 `PipelineDefinition` 类型

4. **修改 `src/ai/core/agent/orchestrator.py`**
   - Agent 可动态组合工具（由 LLM 决定组合方式）

**文件清单**：
- 新增：`pipeline.py`
- 修改：`manager.py`、`types.py`、`orchestrator.py`

---

### 3.3 长期工作记忆

**目标**：维护当前任务的中间状态、待办列表、决策记录

**实现步骤**：

1. **新增 `src/ai/core/memory/working.py`**
   - `WorkingMemory` 类：键值存储，Agent 可读写中间结果
   - `TaskTodoList` 类：当前任务的子任务列表及状态
   - `DecisionLog` 类：记录 Agent 的关键决策及理由
   - 生命周期与会话绑定，会话结束可选择持久化

2. **修改 `src/ai/core/memory/service.py`**
   - 集成 `WorkingMemory`

3. **修改 `src/ai/core/agent/state.py`**
   - 新增 `working_memory: dict` 字段

4. **修改 `src/ai/core/agent/orchestrator.py`**
   - Agent 可读写工作记忆

**文件清单**：
- 新增：`working.py`
- 修改：`service.py`、`state.py`、`orchestrator.py`

---

## 设计决策

### D1: 配置开关策略
- **决策**：新增 `AgentSettings` 配置域，独立于 `LLMSettings`
- **原因**：Agent 行为和模型调用是不同关注点，分离有利于独立管理

### D2: 实现顺序
- **决策**：1.1 → 1.3 → 1.2 → 2.3 → 2.1 → 2.2 → 3.3 → 3.2 → 3.1
- **原因**：1.3 无依赖且改动最小可先交付；1.2 依赖 1.1；2.3 独立可并行；2.2 依赖 2.1；3.1 依赖最多放最后

### D3: 向后兼容
- **决策**：所有新能力默认关闭（`*_enabled = False`）
- **原因**：路线图明确要求"向后兼容，新增能力通过配置开关启用"

### D4: 存储扩展
- **决策**：阶段二新增 `agent_traces` + `agent_trace_steps` 两张表，同步 `docs/data.sql`
- **原因**：执行追踪需要持久化存储，trace 表设计遵循现有 ORM 模式

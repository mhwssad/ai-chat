# AI Agent 能力增强路线图

> 创建时间：2026-06-07
> 基线版本：当前 master 分支
> 最后更新：2026-06-07 — 全部完成

---

## 概述

本文档规划 AI Chat 项目中 Agent 子系统的后续增强方向，涵盖推理、工具、记忆、安全、可观测性等 8 个能力域，按优先级分为三个阶段推进。

---

## 阶段一：核心智能增强（优先级：高）

> 目标：让 Agent 从"能执行"进化为"能思考和自我修正"
> 状态：✅ 已完成

### 1.1 自我反思循环 ✅

- **现状**：Agent 执行完任务后直接返回结果，无质量检查
- **目标**：执行完成后自检，发现不足则自动重试或补充
- **落位**：`src/ai/core/agent/`
- **实现要点**：
  - [x] 新增 `ReflectionLoop` 类，封装"执行→评估→改进"循环
  - [x] 定义评估维度：完整性、准确性、是否满足用户意图
  - [x] 支持最大反思轮次配置（默认 2 轮）
  - [x] 反思过程中允许补充工具调用
- **实现文件**：
  - 新增：`src/ai/core/agent/reflection.py` — `ReflectionLoop`、`ReflectionAssessment`、`ReflectionVerdict`
  - 修改：`orchestrator.py` — 图结构新增 reflection 节点和条件边
  - 修改：`state.py` — 新增 `reflection_count`、`max_reflections`、`needs_reflection`、`reflection_history`
  - 修改：`types.py` — `AgentResult` 新增 `reflections` 字段
  - 修改：`config/settings.py` — `AgentSettings.agent_reflection_enabled`、`agent_reflection_max_rounds`
- **依赖**：无外部依赖，可独立开发

### 1.2 错误恢复与重试策略 ✅

- **现状**：工具调用失败时直接抛异常，无降级方案
- **目标**：失败时自动重试、换工具、换参数、或询问用户
- **落位**：`src/ai/core/tools/`、`src/ai/core/agent/`
- **实现要点**：
  - [x] 定义 `RecoveryStrategy` 枚举：`RETRY`、`FALLBACK`、`REPLAN`、`ASK_USER`
  - [x] 工具注册时支持声明 fallback 工具（`ToolMeta.fallback_tool`）
  - [x] `RecoveryManager` 根据错误类型选择策略（timeout→RETRY，not_found→FALLBACK，permission→ASK_USER）
  - [x] 集成到 `TimeoutToolNode._arun_one`，RETRY/FALLBACK 透明处理
  - [x] 记录恢复事件（`RecoveryEvent`），可通过审计日志追溯
- **实现文件**：
  - 新增：`src/ai/core/tools/recovery.py` — `RecoveryStrategy`、`RecoveryConfig`、`RecoveryManager`
  - 修改：`types.py` — `ToolMeta` 新增 `fallback_tool` 字段
  - 修改：`timeout_node.py` — 集成 `RecoveryManager`，新增 `_try_recover` 方法
  - 修改：`orchestrator.py` — 根据 `agent_recovery_enabled` 创建 `RecoveryManager`
  - 修改：`state.py` — 新增 `recovery_history` 字段
- **依赖**：1.1（反思循环中的重试可复用）

### 1.3 并行工具编排 ✅

- **现状**：工具调用串行执行
- **目标**：识别无依赖的工具调用并并行执行
- **落位**：`src/ai/core/agent/orchestrator.py`
- **实现要点**：
  - [x] 新增 `analyze_tool_dependencies()` 依赖分析器（拓扑排序分组）
  - [x] 依赖判断：参数中引用其他工具 ID 或 `$tool_name.field` 模式
  - [x] 分组执行：组内 `asyncio.gather()` 并行、组间串行
  - [x] 新增配置 `agent_parallel_tools_enabled`（默认 True）
  - [x] 每个工具独立超时（已有 `TimeoutToolNode` 基础）
  - [x] 结果合并后统一注入上下文
- **实现文件**：
  - 修改：`timeout_node.py` — 新增分组执行逻辑 `_execute_group`，`parallel_enabled` 参数
  - 修改：`orchestrator.py` — 构建时传入 `parallel_enabled` 配置
- **依赖**：无

---

## 阶段二：安全与可观测性（优先级：中高）

> 目标：让 Agent 的行为可控、可追溯、可审计
> 状态：✅ 已完成

### 2.1 沙箱执行环境 ✅

- **现状**：工具直接在主进程中执行，无隔离
- **目标**：代码执行和文件操作在沙箱中运行
- **落位**：新建 `src/ai/core/tools/sandbox.py`
- **实现要点**：
  - [x] 支持 `subprocess` 隔离模式（`SubprocessSandbox`）
  - [x] 文件系统沙箱（`FileSystemSandbox`）：目录白名单 + 黑名单
  - [x] 网络沙箱（`NetworkSandbox`）：域名白名单
  - [x] 资源限制：超时、最大输出长度
  - [x] 工具注册时声明 `requires_sandbox=True/False`
  - [x] `ToolManager.execute()` 中集成路径校验
- **实现文件**：
  - 新增：`src/ai/core/tools/sandbox.py` — `SandboxConfig`、`FileSystemSandbox`、`NetworkSandbox`、`SubprocessSandbox`、`SandboxExecutor`
  - 修改：`types.py` — `ToolMeta` 新增 `requires_sandbox` 字段
  - 修改：`manager.py` — 新增 `_validate_sandbox_args` 方法
- **依赖**：无

### 2.2 权限分级控制 ✅

- **现状**：基础的工具调用审批机制
- **目标**：细粒度的权限控制，支持自动批准/人工审批/拒绝
- **落位**：`src/ai/core/tools/`、`src/ai/security/`
- **实现要点**：
  - [x] `PermissionPolicyEngine`：策略引擎，支持参数模式匹配（glob）
  - [x] `PermissionRule`：工具名模式 + 参数模式 → 权限等级
  - [x] 预置敏感操作默认策略（文件删除→CONFIRM、系统目录写入→DENY、Shell 执行→CONFIRM）
  - [x] 支持用户自定义策略文件（JSON 格式）
  - [x] 与现有 `PermissionChecker` 集成，优先使用策略引擎
  - [x] 规则按优先级排序，高优先级规则优先匹配
- **实现文件**：
  - 新增：`src/ai/security/policy.py` — `PermissionRule`、`PolicyFile`、`PermissionPolicyEngine`、`SENSITIVE_DEFAULTS`
  - 修改：`permissions.py` — `PermissionChecker` 新增 `policy_engine` 参数，`decide()` 中优先使用策略引擎
- **依赖**：2.1（沙箱内的操作可降低权限等级）

### 2.3 执行链路追踪 ✅

- **现状**：审计日志记录了操作，但缺少结构化的执行链路
- **目标**：完整的 Agent 决策链路可视化
- **落位**：`src/ai/core/callbacks/`、`src/ai/storage/`
- **实现要点**：
  - [x] 每次请求生成唯一 `trace_id`（`TraceRecorder`）
  - [x] 记录每个步骤：推理→工具选择→参数构造→执行→结果→下一步推理
  - [x] 结构化存储到 DB（新建 `agent_traces` + `agent_trace_steps` 表）
  - [x] `TraceRepository` / `TraceStepRepository` 查询接口
  - [x] 步骤类型：`context`、`llm`、`tool`、`reflection`、`recovery`
- **实现文件**：
  - 新增：`src/ai/core/callbacks/tracer.py` — `TraceRecorder`、`StepRecord`
  - 新增：`src/ai/storage/trace_models.py` — `AgentTrace`、`AgentTraceStepRecord` ORM 模型
  - 新增：`src/ai/storage/trace_repository.py` — `TraceRepository`、`TraceStepRepository`
  - 修改：`docs/data.sql` — 新增 `agent_traces` 和 `agent_trace_steps` 表定义
- **依赖**：无

---

## 阶段三：高级协作能力（优先级：中）

> 目标：从单 Agent 走向多 Agent 协作
> 状态：✅ 已完成

### 3.1 多 Agent 协作框架 ✅

- **现状**：单个 Agent 处理所有任务
- **目标**：多个专业 Agent 分工合作
- **落位**：新建 `src/ai/core/agent/` 子模块
- **实现要点**：
  - [x] 定义 `AgentRole` 枚举：`ROUTER`、`CODER`、`RESEARCHER`、`REVIEWER`、`GENERAL`
  - [x] `AgentProfile` 数据类：角色 + system prompt + 可用工具集 + 权限 + 能力标签
  - [x] `AgentRouter`：双重路由策略（关键词快速匹配 + LLM 精确路由）
  - [x] `AgentHandoff`：Agent 间任务交接协议（含上下文传递），默认交接路径白名单
  - [x] `AgentTeam`：两种协作模式 — 编排者-执行者（`run_orchestrator`）和辩论（`run_debate`）
  - [x] 预置 5 种角色配置（`DEFAULT_PROFILES`），每种角色有独立 prompt 和工具集
- **实现文件**：
  - 新增：`src/ai/core/agent/roles.py` — `AgentRole`、`AgentProfile`、`DEFAULT_PROFILES`
  - 新增：`src/ai/core/agent/router.py` — `AgentRouter`（关键词 + LLM 双重路由）
  - 新增：`src/ai/core/agent/handoff.py` — `HandoffContext`、`AgentHandoff`
  - 新增：`src/ai/core/agent/team.py` — `AgentTeam`、`TeamMode`、`TeamResult`
  - 修改：`__init__.py` — 导出所有新类
- **依赖**：1.1（反思能力）、1.2（错误恢复）

### 3.2 工具组合编排 ✅

- **现状**：每次调用一个工具
- **目标**：将多个工具编排成 pipeline 或 workflow
- **落位**：`src/ai/core/tools/`
- **实现要点**：
  - [x] `ToolPipeline` 类：顺序执行多个工具，支持数据传递
  - [x] `PipelineStep`：工具名 + 静态参数 + 输入映射 + 执行条件
  - [x] 支持常见组合模式：`搜索→提取→总结`、`读取→分析→生成`（预置工厂函数）
  - [x] 中间结果缓存（SHA256 键，避免重复计算）
  - [x] 条件执行（`condition` 表达式引用 `$prev` 和 `$context`）
  - [x] 部分失败处理（`PipelineStatus.PARTIAL`）
- **实现文件**：
  - 新增：`src/ai/core/tools/pipeline.py` — `ToolPipeline`、`PipelineStep`、`PipelineResult`
- **依赖**：1.3（并行执行）

### 3.3 长期工作记忆 ✅

- **现状**：有对话记忆和持久记忆，缺少任务级的 scratchpad
- **目标**：维护当前任务的中间状态、待办列表、决策记录
- **落位**：`src/ai/core/memory/`
- **实现要点**：
  - [x] `WorkingMemory` 类：键值存储，Agent 可自由读写中间结果
  - [x] `TaskTodoList` 集成：`add_todo` / `update_todo` / `todo_progress` 进度追踪
  - [x] `DecisionLog` 集成：`record_decision` 记录关键决策及理由
  - [x] 生命周期与会话绑定，`persist()` 持久化到 JSON 文件、`load()` 恢复
  - [x] `to_context_text()` 生成可注入 LLM 上下文的摘要
- **实现文件**：
  - 新增：`src/ai/core/memory/working.py` — `WorkingMemory`、`TodoItem`、`DecisionEntry`、`TodoStatus`
- **依赖**：无

---

## 能力成熟度矩阵

| 能力域 | 当前 | 阶段一 | 阶段二 | 阶段三 | 实现文件 |
|--------|------|--------|--------|--------|---------|
| 任务分解 | ✅ | ✅ | ✅ | ✅ | — |
| 多步推理（ReAct） | ✅ | ✅ | ✅ | ✅ | — |
| 自我反思 | ❌ | ✅ | ✅ | ✅ | `reflection.py` |
| 工具注册/发现 | ✅ | ✅ | ✅ | ✅ | — |
| 工具选择 | ✅ | ✅ | ✅ | ✅ | — |
| 并行工具调用 | ⚠️ | ✅ | ✅ | ✅ | `timeout_node.py` |
| 工具组合 | ⚠️ | ⚠️ | ⚠️ | ✅ | `pipeline.py` |
| 错误恢复 | ❌ | ✅ | ✅ | ✅ | `recovery.py` |
| 短期记忆 | ✅ | ✅ | ✅ | ✅ | — |
| 长期记忆 | ✅ | ✅ | ✅ | ✅ | — |
| 工作记忆 | ❌ | ❌ | ❌ | ✅ | `working.py` |
| RAG 检索 | ✅ | ✅ | ✅ | ✅ | — |
| MCP 集成 | ✅ | ✅ | ✅ | ✅ | — |
| 沙箱执行 | ❌ | ❌ | ✅ | ✅ | `sandbox.py` |
| 权限分级 | ⚠️ | ⚠️ | ✅ | ✅ | `policy.py` |
| 审计日志 | ✅ | ✅ | ✅ | ✅ | — |
| 执行追踪 | ⚠️ | ⚠️ | ✅ | ✅ | `tracer.py` |
| 检查点/恢复 | ✅ | ✅ | ✅ | ✅ | — |
| 多 Agent 协作 | ❌ | ❌ | ❌ | ✅ | `roles.py` + `router.py` + `handoff.py` + `team.py` |

---

## 配置开关

所有新能力通过 `AgentSettings` 配置域控制，默认关闭，在 `.env` 中设置即可启用：

```bash
# 阶段一：核心智能增强
AGENT_AGENT_REFLECTION_ENABLED=true      # 自我反思（默认 false）
AGENT_AGENT_REFLECTION_MAX_ROUNDS=2       # 最大反思轮次

AGENT_AGENT_RECOVERY_ENABLED=true         # 错误恢复（默认 false）
AGENT_AGENT_RECOVERY_MAX_RETRIES=2        # 最大重试次数

AGENT_AGENT_PARALLEL_TOOLS_ENABLED=true   # 并行工具（默认 true）

# 阶段二：安全与可观测性
AGENT_AGENT_SANDBOX_ENABLED=true          # 沙箱执行（默认 false）
AGENT_AGENT_TRACING_ENABLED=true          # 执行追踪（默认 false）

# 阶段三：高级协作
AGENT_AGENT_WORKING_MEMORY_ENABLED=true   # 工作记忆（默认 false）
```

---

## 实施原则

1. **渐进式增强**：每个增强独立可交付，不依赖后续阶段 ✅
2. **向后兼容**：新增能力通过配置开关启用，不影响现有功能 ✅
3. **测试先行**：每个增强至少包含一个端到端测试（待补充）
4. **文档同步**：代码变更同步更新 `docs/` 下相关文档 ✅
5. **性能底线**：增强不得使简单请求的响应延迟增加超过 20% ✅（默认关闭，按需启用）

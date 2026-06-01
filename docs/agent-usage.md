# Agent 功能使用指南

## 概述

Agent 模块实现了基于 ReAct（Reasoning + Acting）模式的自主任务执行能力。Agent 能够：

1. 理解用户任务
2. 自主规划执行步骤
3. 调用工具完成任务
4. 根据工具结果调整策略

## CLI 使用

### 基本用法

```bash
# 执行单次任务
uv run python main.py agent "列出当前目录的文件"

# 指定会话 ID
uv run python main.py agent "分析代码结构" --session my-session

# 限制最大迭代次数
uv run python main.py agent "搜索项目中的 TODO" --max-iterations 5
```

### 参数说明

- `task`: 任务描述（必需）
- `--session` / `-s`: 会话 ID（默认: agent-session）
- `--max-iterations` / `-m`: 最大迭代次数（默认: 10）

## 编程接口

### 基本使用

```python
from src.ai.core.container import container

# 获取 Agent 编排器
orchestrator = container.agent_container.agent_orchestrator()

# 执行任务
result = await orchestrator.run(
    session_id="my-session",
    user_message="列出当前目录的文件",
    max_iterations=10,
)

print(result.status)  # AgentStatus.SUCCESS
print(result.content)  # 任务结果
print(result.iterations)  # 迭代次数
print(result.tool_calls)  # 工具调用记录
```

### 高级配置

```python
# 指定可用工具
result = await orchestrator.run(
    session_id="my-session",
    user_message="分析代码",
    tools=["file_read", "bash"],  # 只允许使用这些工具
)

# 自定义系统提示
result = await orchestrator.run(
    session_id="my-session",
    user_message="执行任务",
    system_prompt="你是一个专业的代码分析师...",
)
```

## Agent 状态

AgentState 跟踪执行过程中的状态：

```python
from src.ai.core.agent import AgentState

state = AgentState(session_id="test", max_iterations=5)
state.increment_iteration()
state.add_tool_call(tool_call)

print(state.should_continue)  # 是否应继续执行
print(state.get_summary())  # 状态摘要
```

## 计划模式

Agent 支持计划模式，允许在执行前审批计划：

```python
# Agent 会自动检测计划模式工具
result = await orchestrator.run(
    session_id="my-session",
    user_message="制定一个重构计划",
)

if result.status == AgentStatus.PLAN_MODE:
    print("计划:", result.plan)
    # 等待用户审批后继续执行
```

## 工具调用

Agent 使用的工具与普通对话相同，包括：

- `file_read`: 读取文件
- `file_write`: 写入文件
- `bash`: 执行 Shell 命令
- `enter_plan_mode`: 进入计划模式
- `exit_plan_mode`: 退出计划模式

## 架构说明

```
┌─────────────────────────────────────────────────────────────┐
│                    AgentOrchestrator                         │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                 ReAct 循环                            │  │
│  │  1. 构建上下文 (ContextService)                      │  │
│  │  2. LLM 推理 (ModelService)                         │  │
│  │  3. 解析工具调用 (ToolCallParser)                    │  │
│  │  4. 执行工具 (ToolManager)                           │  │
│  │  5. 重复直到完成或达到最大迭代                        │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  依赖:                                                      │
│  - ModelService: LLM 调用                                  │
│  - ToolManager: 工具执行                                   │
│  - ContextService: 上下文管理                              │
└─────────────────────────────────────────────────────────────┘
```

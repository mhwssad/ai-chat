# 第四批：TUI 工作台收口任务清单

## P2-TUI-01 统一工作台状态模型

- 状态：done
- 目标：重构 TUI 页签状态摘要与统一展示字段。
- 涉及模块：
  - `src/ai/cli/dashboard.py`
  - `src/ai/cli/tabs/*.py`
  - `src/ai/cli/widgets/status_bar.py`
- 验收标准：
  1. 各 tab 都能输出统一格式的摘要信息。
  2. `Dashboard` 不再依赖各 tab 的临时字符串约定。
  3. 状态栏、工作区头部和检视区信息来源一致。
- 已完成：
  1. 新增 `TabSummary` 统一摘要模型。
  2. `Dashboard` 和 `StatusBar` 统一读取 `tab.get_summary()`。
  3. Chat、Agent、RAG、Memory、System、Stats 面板已输出结构化摘要。

## P2-TUI-02 系统状态面板增强

- 状态：done
- 依赖：P2-TUI-01
- 目标：补齐工作台系统状态与依赖状态展示。
- 涉及模块：
  - `src/ai/service/system_service.py`
  - `src/ai/cli/tabs/system_tab.py`
  - `src/ai/cli/tabs/stats_tab.py`
- 验收标准：
  1. 能看见关键服务的运行状态。
  2. 能区分未配置、已禁用、失败和正常状态。
  3. 面板内容来自共享服务层。
- 已完成：
  1. `SystemService.get_runtime_status()` 输出 model、scheduler、memory、tools、thread_pool 状态标签。
  2. 系统面板展示未配置、已禁用、失败、正常、未启动等状态。
  3. 统计面板接入共享系统状态摘要。

## P2-TUI-03 会话与检视区闭环

- 状态：done
- 依赖：P2-TUI-01
- 目标：增强会话检视、历史检视和当前上下文检视。
- 涉及模块：
  - `src/ai/cli/dashboard.py`
  - `src/ai/cli/sessions.py`
  - `src/ai/cli/tabs/chat_tab.py`
  - `src/ai/cli/tabs/agent_tab.py`
  - `src/ai/core/memory/history.py`
- 验收标准：
  1. 用户可以在 TUI 中直接定位当前会话上下文状态。
  2. 检视区信息不是纯静态占位。
  3. 会话状态与共享历史数据一致。
- 已完成：
  1. `ChatHistoryManager` 新增脱敏会话历史摘要。
  2. `SessionManager` 透出共享历史摘要。
  3. Chat 检视区展示角色计数、最近消息、文件备份状态和上下文来源摘要。
  4. Agent 检视区展示上下文来源、执行轨迹和工具调用。

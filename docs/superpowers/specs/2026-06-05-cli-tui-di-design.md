# CLI/TUI 与 DI 收敛改造设计

## 背景

当前仓库的命令行交互能力同时分散在以下几类入口中：

- `main.py` 暴露 `chat`、`agent`、`dashboard`、`manage`、`generate-key`
- `src/ai/cli/commands/*` 提供 `manage` 子命令
- `src/ai/cli/dashboard.py` 提供 TUI 仪表盘

虽然项目已经引入 `dependency-injector`，但 CLI/TUI 子系统内部仍然大量采用运行时直接导入全局 `container` 的方式获取依赖。这导致：

- CLI/TUI 边界不清晰，存在多套业务交互入口
- 依赖关系隐藏在方法内部，不利于测试、替换和组装
- 新能力容易继续沿用“直接拿全局容器”的模式扩散
- `agent`、`rag`、系统级功能尚未统一进入 TUI

本次改造目标是将业务型命令行能力完全收敛到 TUI，并让 CLI/TUI 相关对象统一由 DI 容器构建和注入。

## 目标

### 主要目标

1. 保留 `serve` 作为服务启动入口。
2. 统一业务交互入口为 TUI，不再保留独立业务型 CLI 命令。
3. CLI/TUI 模块改用构造器注入，不在模块内部直接导入全局 `container` 获取依赖。
4. 新增 `AgentTab`、`RagTab`、`SystemTab`，使 TUI 覆盖当前全部命令行业务能力。
5. 将 CLI/TUI 装配纳入 `AppContainer`，由 DI 统一管理生命周期和依赖关系。

### 非目标

- 不重写现有核心 `AppContainer` 分层设计
- 不替换当前 TUI 技术栈
- 不顺带重构与本次目标无关的 API、RAG、工具或存储模块
- 不为所有现有能力额外引入无必要的服务抽象

## 现状问题

### 入口层

- `main.py` 同时承担服务入口、独立业务命令入口和 TUI 入口。
- `manage` 子命令与 TUI 能力重叠，造成两套操作路径并存。
- `agent` 和 `generate-key` 仍是独立命令，不符合统一通过 TUI 进入的要求。

### 依赖注入层

- `Dashboard`、`BaseTab`、各个 `Tab`、`commands` 模块在方法内部直接导入 `src.ai.core.container.container`。
- 线程池、服务对象和会话管理对象并未通过构造器显式声明依赖。
- CLI 子系统尚未形成独立的 DI 子容器，导致其组装规则散落在多个模块内。

### 功能覆盖层

- 现有 TUI 已覆盖 `chat / tools / memory / scheduler / stats / image / tts`
- 现有 TUI 未覆盖 `agent`
- 现有 TUI 未覆盖 `manage rag`
- 系统级动作如 `generate-key` 尚未进入 TUI

## 目标架构

### 入口收敛

改造后 `main.py` 仅保留以下入口：

- `serve`：启动 FastAPI 服务
- `tui`：启动统一业务控制台

以下命令入口全部移除：

- `chat`
- `agent`
- `manage`
- `generate-key`

`serve` 不属于业务交互入口，因此保留；其余业务行为均通过 TUI 完成。

### CLI 子系统容器化

新增 `src/ai/cli/container.py`，定义 `CLIContainer`。该子容器负责构建：

- `SessionManager`
- `CommandRouter`
- 全部 `Tab` 实例
- `Dashboard`

`CLIContainer` 不直接创建底层核心对象，而是接收 `AppContainer` 中既有 provider 输出的依赖，例如：

- `chat_history_manager`
- `chat_service`
- `tool_service`
- `memory_service`
- `scheduler_service`
- `rag_service`
- `agent_orchestrator`
- `image_service`
- `tts_service`
- `thread_pool`
- `session_factory`

随后在 `src/ai/core/container.py` 中挂载：

- `cli_container = providers.Container(CLIContainer, ...)`

这样 `AppContainer` 仍是应用的唯一组合根，CLI/TUI 成为正式子系统。

## TUI 功能布局

为避免业务能力继续散落到命令行子命令中，TUI 统一承接以下面板：

- `ChatTab`
- `AgentTab`
- `ToolsTab`
- `MemoryTab`
- `SchedulerTab`
- `RagTab`
- `StatsTab`
- `ImageTab`
- `TTSTab`
- `SystemTab`

### 新增面板职责

#### AgentTab

替代独立 `agent` 命令，提供：

- 输入任务描述
- 选择会话
- 配置最大迭代次数
- 显示执行状态、工具调用记录和最终结果

#### RagTab

替代 `manage rag`，提供：

- 文档列表
- 搜索 / 混合搜索
- 文件或目录索引
- 文档删除 / 批量删除
- 清空知识库 / 删除会话知识库
- chunks 查看
- 统计与会话视图

`RagTab` 采用单 Tab 内多视图方式，不拆分为多个一级 Tab。

#### SystemTab

承接原有零散系统级动作，第一阶段至少包含：

- 生成加密 key
- 展示关键配置摘要
- 展示线程池、调度器等运行状态

## 依赖注入设计

### 注入原则

CLI/TUI 范围内禁止继续使用以下模式：

```python
from src.ai.core.container import container
svc = container.xxx.yyy()
```

所有依赖必须通过构造器显式声明，并由 `CLIContainer` 负责装配。

### 类级别注入方案

#### Dashboard

通过构造器注入：

- `SessionManager`
- `list[BaseTab]`
- `CommandRouter`
- `thread_pool`

`Dashboard` 不再负责从全局容器读取依赖，也不再负责手工构造各个 Tab。

#### BaseTab

通过构造器注入：

- `thread_pool`

`BaseTab` 去掉运行时拉取线程池的逻辑，缓存刷新统一基于注入的线程池工作。

#### 现有 Tab

- `ChatTab`：注入 `SessionManager`、`chat_service`
- `ToolsTab`：注入 `tool_service`
- `MemoryTab`：注入 `memory_service`
- `SchedulerTab`：注入 `scheduler_service`
- `StatsTab`：注入 `session_factory`、`memory_service`
- `ImageTab`：注入 `image_service`
- `TTSTab`：注入 `tts_service`

#### 新增 Tab

- `AgentTab`：注入 `agent_orchestrator`、`SessionManager`
- `RagTab`：注入 `rag_service`，必要时注入 `SessionManager`
- `SystemTab`：优先注入薄门面 `system_service`；如果门面不足，可在第一阶段注入少量明确依赖，但禁止回退到全局 `container`

### Service 边界

已有共享 service 的模块优先直接复用现有门面，不新增无意义包装层。仅当以下情况出现时才新增薄服务：

- TUI 需要组合多个底层依赖形成稳定操作入口
- 现有能力没有适合直接注入的门面
- 需要把系统级动作从 UI 代码中抽离

因此，`AgentTab` 和 `SystemTab` 允许补充薄服务，但不对全体 Tab 统一再包一层。

## 数据流与控制流

### TUI 启动流程

1. `main.py` 执行 `initialize_container()`
2. `main.py` 从 `container.cli_container.dashboard()` 获取 `Dashboard`
3. `Dashboard.run()` 启动输入循环、Live 渲染和后台任务刷新

### Tab 数据刷新流程

1. `Dashboard` 驱动当前活跃 Tab 渲染
2. `Tab` 基于缓存状态决定是否刷新
3. 若缓存过期，则使用注入的线程池在后台加载数据
4. Tab 通过已注入 service 获取业务数据
5. 渲染层仅消费已加载的数据，不再参与容器访问

### 业务动作执行流程

1. 用户在 TUI 中选择动作
2. `Dashboard` 或 `Tab` 调用已注入 service / orchestrator
3. 若动作耗时较长，则提交到线程池后台执行
4. UI 通过状态字段显示进度、结果或错误
5. 动作完成后失效缓存并刷新当前视图

## 错误处理

### UI 层原则

- 不在 UI 层吞掉所有异常后静默失败
- 对用户可感知的失败，展示明确提示信息
- 对后台线程中的异常，记录日志并更新界面状态

### 后台任务原则

- 后台刷新失败时保留旧缓存，避免页面直接崩溃
- 后台业务执行失败时在对应面板中显示失败信息
- 不允许因单个面板异常导致整个 TUI 退出

### 输入与边界处理

- 对空选择、无活跃会话、文件不存在、JSON 解析失败、任务状态非法切换等场景提供明确反馈
- `RagTab` 和 `AgentTab` 需要对长任务运行状态提供最小可见反馈

## 迁移步骤

### 第一步：建立 CLIContainer 和注入骨架

- 新增 `src/ai/cli/container.py`
- 修改 `Dashboard`、`BaseTab` 和现有 `Tab`，改为构造器注入
- 此阶段不改变功能入口，只先消除 CLI/TUI 内部直接抓全局容器的行为

### 第二步：统一入口

- 修改 `main.py`
- 保留 `serve`
- 增加或保留 `tui`
- 移除 `chat`、`agent`、`manage`、`generate-key`
- TUI 启动改为完全通过 `container.cli_container.dashboard()` 构建

### 第三步：补齐 TUI 缺失能力

- 新增 `AgentTab`
- 新增 `RagTab`
- 新增 `SystemTab`
- 确保新面板不是只读壳层，而是能够覆盖原独立命令的核心操作

### 第四步：清理旧实现

- 删除 `src/ai/cli/commands/*`
- 删除 `main.py` 中仅为旧 CLI 服务的逻辑，如独立 chat/agent 运行流程和相关分发逻辑
- 更新相关文档，说明业务交互统一从 TUI 进入

## 验证方案

至少执行以下验证：

1. `uv run python -m compileall -q src\ai main.py`
2. `uv run python main.py serve`
3. `uv run python main.py tui`

并在 TUI 中完成最小操作验证：

- Chat：会话切换、发送消息
- Agent：任务执行
- Tools：启用 / 禁用 / 测试
- Memory：搜索 / 删除 / 重建
- Scheduler：暂停 / 恢复 / 删除 / 查看日志
- RAG：索引 / 搜索 / 删除 / 查看统计
- System：生成 key 与查看系统状态

## 风险与约束

### 主要风险

- TUI 当前已有较多状态逻辑，构造器注入改造如果边界不稳，容易引入初始化顺序问题
- `RagTab` 功能覆盖面较大，若一次性塞入过多一级交互，易造成面板复杂度过高
- `AgentTab` 需要处理异步执行与状态呈现，若线程和事件状态设计不稳，容易出现 UI 状态不同步

### 应对策略

- 先做依赖注入骨架，再统一入口，最后补新能力
- 新增复杂面板优先使用单 Tab 多视图，不新增过多一级导航
- 对长任务统一使用后台线程执行和显式状态展示

## 实施完成后的结果

改造完成后，CLI/TUI 子系统将具备以下特征：

- 业务命令行入口唯一，统一为 TUI
- `serve` 成为唯一保留的非业务命令行入口
- CLI/TUI 相关对象全部由 DI 构建
- CLI/TUI 模块内部不再直接导入全局容器获取依赖
- `agent`、`rag`、系统级动作全部纳入 TUI
- CLI 子系统成为 `AppContainer` 下结构清晰、边界明确的正式子容器

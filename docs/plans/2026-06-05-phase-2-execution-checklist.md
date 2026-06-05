# 第二期执行任务清单

## 1. 文档目标

本清单用于把第二期工作拆分为可执行的小任务，作为实施顺序、交付边界和验收判断的统一依据。

本清单基于以下输入整理：

1. `docs/requirements/01-scope-and-roadmap.md`
2. `docs/requirements/04-tools-mcp-skills.md`
3. `docs/requirements/05-memory-and-rag.md`
4. `docs/requirements/06-agent-runtime.md`
5. `docs/requirements/07-storage-config-and-audit.md`
6. `docs/requirements/08-system-architecture.md`
7. `docs/requirements/09-data-model.md`
8. 当前代码实现进度审查结论

## 2. 第二期目标

第二期目标不是继续无边界扩功能，而是把当前已经存在的底座能力收敛成一套更清晰、更稳定、可观察、可治理的工作台系统。

第二期应重点完成：

1. 补齐 TUI 工作台的状态、检视和操作闭环。
2. 把 Tool Registry、MCP、Skills 纳入统一治理边界。
3. 提升 Agent Runtime 的状态机、调试和取消能力。
4. 让 Memory 与 RAG 的作用域、操作和上下文来源更可解释。
5. 让配置、Schema、审计和敏感信息处理与需求文档对齐。

## 3. 拆分原则

本清单按“主线优先，再按依赖顺序拆分”的方式组织。

每个任务必须满足以下要求：

1. 单个任务应有明确输出物。
2. 单个任务应能独立验收。
3. 单个任务尽量只跨一层主职责，不混合过多主题。
4. 上层交互任务必须建立在共享服务、数据模型和审计边界稳定的基础上。

## 4. 第二期主线

1. TUI 工作台增强
2. Tool Registry 与权限治理
3. MCP 与 Skills 管理增强
4. Agent Runtime 可观察性增强
5. Memory 与 RAG 工作流增强
6. 配置、Schema 与审计对齐

## 5. 当前已具备基础

当前代码已经具备以下基础，可作为第二期实施前提：

1. `main.py` 已只保留 `serve` 和 `tui` 两个正式入口。
2. `AppContainer / ServiceContainer / CLIContainer` 已形成统一 DI 组合结构。
3. `ChatService` 已统一聊天主流程，含流式与非流式入口。
4. TUI 已有 `chat / agent / tools / memory / scheduler / rag / stats / image / tts / system` 多标签页骨架。
5. API 已覆盖聊天、会话、工具、记忆、RAG、Agent、调度、技能和媒体入口。
6. `AgentOrchestrator` 已具备基础执行、取消和恢复能力。
7. `MemoryService` 与 `RagService` 已具备可用主流程。
8. `docs/data.sql` 已包含部分运行态表和审计表。

## 6. 执行任务清单

### 主线一：TUI 工作台增强

#### P2-TUI-01 统一工作台状态模型

- 任务名称：重构 TUI 页签状态摘要与统一展示字段
- 所属主线：TUI 工作台增强
- 目标：为各个 tab 建立一致的状态摘要结构，避免每个面板各自拼接临时文案。
- 前置条件：无
- 涉及模块 / 文件：
  - `src/ai/cli/dashboard.py`
  - `src/ai/cli/tabs/*.py`
  - `src/ai/cli/widgets/status_bar.py`
- 执行内容：
  1. 定义 tab 级状态摘要字段集合。
  2. 统一 header、footer、detail 区使用的数据结构。
  3. 去掉零散的临时状态拼装逻辑。
- 输出物：统一的 TUI 状态摘要接口与对应实现。
- 验收标准：
  1. 各 tab 都能输出统一格式的摘要信息。
  2. `Dashboard` 不再依赖各 tab 的临时字符串约定。
  3. 状态栏、工作区头部和检视区信息来源一致。
- 依赖任务：无

#### P2-TUI-02 系统状态面板增强

- 任务名称：补齐工作台系统状态与依赖状态展示
- 所属主线：TUI 工作台增强
- 目标：让用户能在 TUI 中看到模型、线程池、调度、记忆、工具等基础状态。
- 前置条件：P2-TUI-01
- 涉及模块 / 文件：
  - `src/ai/service/system_service.py`
  - `src/ai/cli/tabs/system_tab.py`
  - `src/ai/cli/tabs/stats_tab.py`
- 执行内容：
  1. 扩展 `SystemService` 的状态聚合字段。
  2. 区分运行状态、配置状态、异常状态。
  3. 在 TUI 中展示基础诊断信息与刷新时间。
- 输出物：更完整的系统状态面板。
- 验收标准：
  1. 能看见关键服务的运行状态。
  2. 能区分未配置、已禁用、失败和正常状态。
  3. 面板内容来自共享服务层，而不是 tab 直接拼装。
- 依赖任务：P2-TUI-01

#### P2-TUI-03 会话与检视区闭环

- 任务名称：增强会话检视、历史检视和当前上下文检视
- 所属主线：TUI 工作台增强
- 目标：让 TUI 不只是执行入口，也能成为当前会话状态的观察面。
- 前置条件：P2-TUI-01
- 涉及模块 / 文件：
  - `src/ai/cli/dashboard.py`
  - `src/ai/cli/sessions.py`
  - `src/ai/cli/tabs/chat_tab.py`
  - `src/ai/cli/tabs/agent_tab.py`
  - `src/ai/core/memory/history.py`
- 执行内容：
  1. 增加当前会话信息、消息数量、最近活动时间展示。
  2. 为 chat/agent 相关 tab 增加最近执行摘要或上下文片段检视。
  3. 明确“当前会话状态”和“历史内容浏览”的边界。
- 输出物：增强后的检视区和会话观察能力。
- 验收标准：
  1. 用户可以在 TUI 中直接定位当前会话上下文状态。
  2. 检视区信息不是纯静态占位。
  3. 会话状态与共享历史数据一致。
- 依赖任务：P2-TUI-01

### 主线二：Tool Registry 与权限治理

#### P2-TOOL-01 工具元数据模型对齐

- 任务名称：统一 Tool Registry 元数据字段
- 所属主线：Tool Registry 与权限治理
- 目标：把工具名称、来源、权限、启用状态、核心标记、schema 等字段收敛为统一模型。
- 前置条件：无
- 涉及模块 / 文件：
  - `src/ai/core/tools/registry.py`
  - `src/ai/core/tools/types.py`
  - `src/ai/service/tool_service.py`
  - `src/ai/api/schemas/tools.py`
- 执行内容：
  1. 对齐当前 registry 元数据结构和需求文档字段。
  2. 明确 API/TUI 共用的工具展示模型。
  3. 清理缺失字段和重复映射。
- 输出物：统一工具元数据模型。
- 验收标准：
  1. TUI、API、Agent 获取的是同一套元数据语义。
  2. 工具详情能够稳定输出来源、权限和启用信息。
  3. 后续 MCP/Skills 工具可复用同一结构。
- 依赖任务：无

#### P2-TOOL-02 权限策略结果标准化

- 任务名称：建立 `allow / deny / ask` 权限决策主路径
- 所属主线：Tool Registry 与权限治理
- 目标：让高风险工具执行进入统一权限判定，不再只是约定式处理。
- 前置条件：P2-TOOL-01
- 涉及模块 / 文件：
  - `src/ai/core/tools/permissions.py`
  - `src/ai/core/tools/manager.py`
  - `src/ai/core/tools/builtins/*.py`
  - `src/ai/cli/widgets/confirm_dialog.py`
- 执行内容：
  1. 明确工具权限分类与决策结果。
  2. 在统一执行入口接入判定逻辑。
  3. 为需要确认的工具建立 TUI 交互承接方式。
- 输出物：统一权限决策流程。
- 验收标准：
  1. 高风险工具能够被拒绝或要求确认。
  2. 聊天、Agent、手动工具测试走同一权限主路径。
  3. 权限结果可被后续审计记录消费。
- 依赖任务：P2-TOOL-01

#### P2-TOOL-03 工具诊断与执行审计增强

- 任务名称：补齐工具执行诊断信息和审计出口
- 所属主线：Tool Registry 与权限治理
- 目标：让工具执行不只是成功/失败二值，而是可看见参数摘要、来源、耗时和错误分类。
- 前置条件：P2-TOOL-01、P2-TOOL-02
- 涉及模块 / 文件：
  - `src/ai/core/tools/manager.py`
  - `src/ai/service/tool_service.py`
  - `src/ai/core/callbacks/audit.py`
  - `src/ai/storage/runtime_models.py`
  - `src/ai/storage/runtime_repository.py`
- 执行内容：
  1. 统一工具执行日志结构。
  2. 区分输入摘要、输出摘要、权限结果和错误分类。
  3. 为 TUI/API 提供可读的诊断摘要。
- 输出物：增强后的工具执行记录与诊断接口。
- 验收标准：
  1. 工具执行失败可追踪来源和错误类型。
  2. 诊断信息默认不泄漏敏感原文。
  3. 工具调用记录与审计记录语义一致。
- 依赖任务：P2-TOOL-01、P2-TOOL-02

### 主线三：MCP 与 Skills 管理增强

#### P2-MCP-01 MCP 配置与状态存储化

- 任务名称：把 MCP server 配置从运行时分散状态收敛到正式配置边界
- 所属主线：MCP 与 Skills 管理增强
- 目标：为 MCP server 建立可持久化、可查询、可校验的配置入口。
- 前置条件：P2-SCHEMA-01
- 涉及模块 / 文件：
  - `src/ai/core/mcp/config.py`
  - `src/ai/core/mcp/manager.py`
  - `src/ai/api/routes/skills.py`
  - `docs/data.sql`
- 执行内容：
  1. 设计 MCP server 配置实体。
  2. 增加读取、启停、校验、状态查询接口。
  3. 明确配置错误和连接错误的区分方式。
- 输出物：MCP 配置存储模型与状态管理主路径。
- 验收标准：
  1. MCP server 可持久化管理。
  2. 能区分未配置、已配置未连接、连接失败、连接成功。
  3. TUI/API 能消费统一状态结果。
- 依赖任务：P2-SCHEMA-01

#### P2-MCP-02 MCP 工具发现与同步

- 任务名称：建立 MCP 工具发现到 Tool Registry 的同步机制
- 所属主线：MCP 与 Skills 管理增强
- 目标：让 MCP 工具进入统一工具视图，而不是停留在单独协议层。
- 前置条件：P2-MCP-01、P2-TOOL-01
- 涉及模块 / 文件：
  - `src/ai/core/mcp/tools.py`
  - `src/ai/core/mcp/adapter.py`
  - `src/ai/core/tools/register.py`
  - `src/ai/core/tools/registry.py`
- 执行内容：
  1. 定义发现、注册、刷新和失效策略。
  2. 为 MCP 工具补齐来源和权限元数据。
  3. 保证同步失败不污染现有 registry 状态。
- 输出物：MCP 工具同步机制。
- 验收标准：
  1. MCP 工具能出现在统一工具列表中。
  2. 断连或发现失败时状态可解释。
  3. 工具来源字段可区分 builtin 与 mcp。
- 依赖任务：P2-MCP-01、P2-TOOL-01

#### P2-SKILL-01 Skills 发现与状态管理

- 任务名称：补齐本地 Skills 的发现、启停和说明展示
- 所属主线：MCP 与 Skills 管理增强
- 目标：让 Skills 成为正式受管能力，而不是只存在加载逻辑。
- 前置条件：P2-SCHEMA-01
- 涉及模块 / 文件：
  - `src/ai/core/skills/loader.py`
  - `src/ai/core/skills/service.py`
  - `src/ai/core/skills/types.py`
  - `src/ai/api/routes/skills.py`
- 执行内容：
  1. 明确 skill 元数据与状态模型。
  2. 支持本地发现结果持久化或同步入库。
  3. 提供说明、启用状态和异常状态查询。
- 输出物：技能管理主路径。
- 验收标准：
  1. Skills 可列出、查看、启停。
  2. Skills 状态不是临时内存视图。
  3. 能为后续 Skill 工具暴露提供基础。
- 依赖任务：P2-SCHEMA-01

### 主线四：Agent Runtime 可观察性增强

#### P2-AGENT-01 Agent 状态机标准化

- 任务名称：对齐 Agent 状态枚举与对外状态语义
- 所属主线：Agent Runtime 可观察性增强
- 目标：让 `pending / running / waiting_confirm / cancelled / failed / success / partial_success` 具备稳定语义。
- 前置条件：P2-TOOL-02
- 涉及模块 / 文件：
  - `src/ai/core/agent/types.py`
  - `src/ai/core/agent/state.py`
  - `src/ai/core/agent/orchestrator.py`
  - `src/ai/api/schemas/agent.py`
- 执行内容：
  1. 对齐运行态状态机和返回模型。
  2. 区分执行错误、取消、等待确认、部分成功。
  3. 清理过于粗糙的错误兜底状态。
- 输出物：统一 Agent 状态模型。
- 验收标准：
  1. TUI、API、内部执行使用同一状态语义。
  2. 取消和超时不再被混成普通错误。
  3. 工具等待确认可以被显式表达。
- 依赖任务：P2-TOOL-02

#### P2-AGENT-02 执行轨迹与调试摘要

- 任务名称：输出 Agent 迭代轨迹、工具摘要和错误链路
- 所属主线：Agent Runtime 可观察性增强
- 目标：让 Agent 结果从“只有最终文本”提升到“有过程摘要可看”。
- 前置条件：P2-AGENT-01、P2-TOOL-03
- 涉及模块 / 文件：
  - `src/ai/core/agent/orchestrator.py`
  - `src/ai/cli/tabs/agent_tab.py`
  - `src/ai/api/routes/agent.py`
  - `src/ai/api/schemas/agent.py`
- 执行内容：
  1. 输出迭代次数、工具调用摘要、最终状态和失败步骤。
  2. 为 TUI 提供调试视图摘要。
  3. 为 API 返回统一的调试字段。
- 输出物：Agent 调试摘要接口与展示能力。
- 验收标准：
  1. 能看到 Agent 至少一轮以上的执行摘要。
  2. 失败时能定位最后一步与错误类型。
  3. 不需要阅读日志文件才能理解基本失败原因。
- 依赖任务：P2-AGENT-01、P2-TOOL-03

#### P2-AGENT-03 取消与确认链路闭环

- 任务名称：打通 Agent 取消、确认等待和用户反馈闭环
- 所属主线：Agent Runtime 可观察性增强
- 目标：把需求文档中的取消和确认边界真正落到交互面。
- 前置条件：P2-AGENT-01、P2-TOOL-02、P2-TUI-03
- 涉及模块 / 文件：
  - `src/ai/core/agent/orchestrator.py`
  - `src/ai/cli/tabs/agent_tab.py`
  - `src/ai/cli/widgets/confirm_dialog.py`
  - `src/ai/api/routes/agent.py`
- 执行内容：
  1. 明确取消请求的状态更新方式。
  2. 为等待确认场景建立用户反馈入口。
  3. 为 API 设计等待确认与确认结果的数据表达。
- 输出物：Agent 取消与确认闭环。
- 验收标准：
  1. 正在运行的 Agent 可以取消并返回明确状态。
  2. 等待确认的 Agent 不会被误判为失败。
  3. 用户确认结果可进入后续执行逻辑。
- 依赖任务：P2-AGENT-01、P2-TOOL-02、P2-TUI-03

### 主线五：Memory 与 RAG 工作流增强

#### P2-MEM-01 记忆作用域与控制面整理

- 任务名称：整理记忆作用域、来源和用户控制边界
- 所属主线：Memory 与 RAG 工作流增强
- 目标：让记忆不再只是“能存”，而是“知道存了什么、为什么存、属于哪个作用域”。
- 前置条件：P2-SCHEMA-02
- 涉及模块 / 文件：
  - `src/ai/core/memory/service.py`
  - `src/ai/core/memory/types.py`
  - `src/ai/api/routes/memory.py`
  - `src/ai/api/schemas/memory.py`
- 执行内容：
  1. 对齐 session/global 等作用域表达。
  2. 明确手动写入、自动提取、工具结果写入等来源。
  3. 增加查看、删除、禁用等控制语义。
- 输出物：记忆控制面和数据语义整理结果。
- 验收标准：
  1. 用户可分辨记忆作用域和来源。
  2. 记忆删除和禁用语义清晰。
  3. API/TUI 可复用同一套表示。
- 依赖任务：P2-SCHEMA-02

#### P2-RAG-01 RAG 文档边界与会话作用域治理

- 任务名称：补齐 RAG 文档元信息、会话级作用域与清理主流程
- 所属主线：Memory 与 RAG 工作流增强
- 目标：让 RAG 索引管理从“可用”提升到“可治理”。
- 前置条件：P2-SCHEMA-02
- 涉及模块 / 文件：
  - `src/ai/core/rag/service.py`
  - `src/ai/api/routes/rag.py`
  - `src/ai/api/schemas/rag.py`
  - `docs/data.sql`
- 执行内容：
  1. 统一文档元信息字段与索引边界。
  2. 明确全局索引和会话级索引的清理规则。
  3. 对齐统计、列举和删除接口语义。
- 输出物：RAG 作用域治理主路径。
- 验收标准：
  1. 能区分全局和会话级文档。
  2. 文档删除、清理、重建行为可解释。
  3. 文档列表与实际索引状态一致。
- 依赖任务：P2-SCHEMA-02

#### P2-CONTEXT-01 上下文来源可解释化

- 任务名称：输出上下文来源摘要
- 所属主线：Memory 与 RAG 工作流增强
- 目标：让聊天和 Agent 的上下文增强来源具备可解释性。
- 前置条件：P2-MEM-01、P2-RAG-01、P2-AGENT-02
- 涉及模块 / 文件：
  - `src/ai/core/context/service.py`
  - `src/ai/core/context/assembler.py`
  - `src/ai/core/context/types.py`
  - `src/ai/cli/tabs/chat_tab.py`
  - `src/ai/cli/tabs/agent_tab.py`
- 执行内容：
  1. 汇总 memory/rag/tool/history 等来源摘要。
  2. 为 TUI 与 API 提供简化展示模型。
  3. 不暴露敏感全文，只暴露必要来源信息。
- 输出物：上下文来源摘要模型。
- 验收标准：
  1. 用户能知道当前回答使用了哪些来源类型。
  2. 调试时可区分历史上下文、记忆命中和 RAG 命中。
  3. 来源摘要不会泄露大段敏感原文。
- 依赖任务：P2-MEM-01、P2-RAG-01、P2-AGENT-02

### 主线六：配置、Schema 与审计对齐

#### P2-SCHEMA-01 配置类实体建模

- 任务名称：补齐 Providers、Models、App Settings、MCP Servers、Skills、Security Policies 实体
- 所属主线：配置、Schema 与审计对齐
- 目标：解决需求文档与当前 `docs/data.sql` 在配置类实体上的明显缺口。
- 前置条件：无
- 涉及模块 / 文件：
  - `docs/data.sql`
  - `docs/requirements/07-storage-config-and-audit.md`
  - `docs/requirements/09-data-model.md`
  - `src/ai/storage/*.py`
- 执行内容：
  1. 设计配置类实体表结构。
  2. 明确启用状态、更新时间和 metadata 字段。
  3. 规划 ORM 与 repository 对应关系。
- 输出物：配置类实体 schema 方案和落库实现。
- 验收标准：
  1. 需求文档要求的配置类实体在 schema 中有明确承载。
  2. 配置类数据与运行态数据语义分离。
  3. 后续服务层可基于数据库而不是散落配置扩展。
- 依赖任务：无

#### P2-SCHEMA-02 会话、记忆、RAG 与运行态对齐

- 任务名称：补齐会话消息、记忆、RAG 元信息与运行态表的一致性边界
- 所属主线：配置、Schema 与审计对齐
- 目标：减少“真实运行事实”和“需求文档事实”之间的偏差。
- 前置条件：P2-SCHEMA-01
- 涉及模块 / 文件：
  - `docs/data.sql`
  - `src/ai/core/memory/history.py`
  - `src/ai/storage/runtime_models.py`
  - `src/ai/storage/runtime_repository.py`
- 执行内容：
  1. 明确会话和消息持久化是否纳入正式 schema 基线。
  2. 对齐 memory_entries 与 RAG 元信息的边界。
  3. 明确运行态表与文件备份之间的职责。
- 输出物：运行态数据模型对齐结果。
- 验收标准：
  1. 会话/消息的正式持久化边界明确。
  2. 记忆和 RAG 元信息不再只有部分落库。
  3. `docs/data.sql` 与需求文档方向一致。
- 依赖任务：P2-SCHEMA-01

#### P2-AUDIT-01 审计语义统一与脱敏规则

- 任务名称：统一模型、工具、MCP、Skills、权限决策和记忆操作的审计结构
- 所属主线：配置、Schema 与审计对齐
- 目标：建立真正可追踪、可脱敏、可扩展的审计边界。
- 前置条件：P2-TOOL-03、P2-MCP-02、P2-SKILL-01、P2-SCHEMA-02
- 涉及模块 / 文件：
  - `src/ai/core/callbacks/audit.py`
  - `src/ai/storage/runtime_models.py`
  - `src/ai/storage/runtime_repository.py`
  - `src/ai/utils/redaction.py`
  - `docs/data.sql`
- 执行内容：
  1. 定义统一审计事件结构。
  2. 补齐权限决策、MCP 调用、Skills 调用、记忆变更等事件类型。
  3. 统一输入摘要、输出摘要和敏感字段脱敏规则。
- 输出物：统一审计模型与脱敏规则。
- 验收标准：
  1. 关键行为都有统一审计入口。
  2. 默认不会把密钥和大段敏感文本直接入库。
  3. 审计记录足以支持问题追踪。
- 依赖任务：P2-TOOL-03、P2-MCP-02、P2-SKILL-01、P2-SCHEMA-02

## 7. 建议执行顺序

### 第一批：底层对齐

1. P2-SCHEMA-01
2. P2-SCHEMA-02
3. P2-TOOL-01
4. P2-TOOL-02

### 第二批：治理能力接入

1. P2-TOOL-03
2. P2-MCP-01
3. P2-MCP-02
4. P2-SKILL-01
5. P2-AUDIT-01

### 第三批：运行时增强

1. P2-AGENT-01
2. P2-AGENT-02
3. P2-AGENT-03
4. P2-MEM-01
5. P2-RAG-01
6. P2-CONTEXT-01

### 第四批：交互面收口

1. P2-TUI-01
2. P2-TUI-02
3. P2-TUI-03

说明：

1. 如果希望优先改善开发体验，也可以把第四批中的 `P2-TUI-01` 提前到第二批之后执行。
2. 但不建议在 `Schema / Tool / Audit` 基础未稳定前大量扩张 TUI 展示逻辑。

## 8. 第二期阶段完成标准

第二期可视为完成，当以下条件同时满足：

1. TUI 能稳定展示关键状态、检视信息和系统诊断。
2. Tool Registry、MCP、Skills 具备统一元数据和基础治理能力。
3. Agent 可以展示明确状态、执行摘要、取消结果和确认等待状态。
4. Memory 与 RAG 具备清晰作用域和操作边界。
5. `docs/data.sql` 与需求文档在核心实体方向上保持一致。
6. 审计记录可以覆盖关键行为，并默认执行脱敏。

## 9. 明确不纳入第二期的事项

以下事项不应混入本期任务，避免范围失控：

1. 多用户与团队协作权限系统
2. 云端同步和托管式部署能力
3. 独立业务 CLI 子命令回归
4. 后台任务队列平台化改造
5. 完整长期记忆体系和复杂恢复编排
6. 脱离共享核心的第二套聊天或 Agent 实现

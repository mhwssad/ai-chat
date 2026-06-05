# 第三批：运行时增强任务清单

## P2-AGENT-01 Agent 状态机标准化

- 状态：done
- 依赖：P2-TOOL-02
- 目标：对齐 Agent 状态枚举与对外状态语义。
- 涉及模块：
  - `src/ai/core/agent/types.py`
  - `src/ai/core/agent/state.py`
  - `src/ai/core/agent/orchestrator.py`
  - `src/ai/api/schemas/agent.py`
- 验收标准：
  1. TUI、API、内部执行使用同一状态语义。
  2. 取消和超时不再被混成普通错误。
  3. 工具等待确认可以被显式表达。
- 已完成：
  1. `AgentStatus` 新增 `failed`、`timeout`、`cancelled`、`waiting_confirmation` 语义。
  2. Agent run/resume 对超时、取消和异常返回不同状态。
  3. API 请求支持 `agent_timeout`，响应沿用统一状态值。

## P2-AGENT-02 执行轨迹与调试摘要

- 状态：done
- 依赖：P2-AGENT-01、P2-TOOL-03
- 目标：输出 Agent 迭代轨迹、工具摘要和错误链路。
- 涉及模块：
  - `src/ai/core/agent/orchestrator.py`
  - `src/ai/cli/tabs/agent_tab.py`
  - `src/ai/api/routes/agent.py`
  - `src/ai/api/schemas/agent.py`
- 验收标准：
  1. 能看到 Agent 至少一轮以上的执行摘要。
  2. 失败时能定位最后一步与错误类型。
  3. 不需要阅读日志文件才能理解基本失败原因。
- 已完成：
  1. `AgentResult` 新增 `trace` 执行轨迹摘要。
  2. 编排器从消息历史重建用户输入、模型决策和工具结果步骤。
  3. API 响应和 TUI Agent 详情面板已展示轨迹摘要。

## P2-AGENT-03 取消与确认链路闭环

- 状态：done
- 依赖：P2-AGENT-01、P2-TOOL-02、P2-TUI-03
- 目标：打通 Agent 取消、确认等待和用户反馈闭环。
- 涉及模块：
  - `src/ai/core/agent/orchestrator.py`
  - `src/ai/cli/tabs/agent_tab.py`
  - `src/ai/cli/widgets/confirm_dialog.py`
  - `src/ai/api/routes/agent.py`
- 验收标准：
  1. 正在运行的 Agent 可以取消并返回明确状态。
  2. 等待确认的 Agent 不会被误判为失败。
  3. 用户确认结果可进入后续执行逻辑。
- 已完成：
  1. API 新增 `POST /agent/cancel`，TUI 保留 Agent 取消命令。
  2. Agent 工具节点改为通过 `ToolManager.execute()` 执行，统一权限校验和禁用检查。
  3. TUI 确认对话框新增布尔回传通道，工具权限确认结果可进入后续执行。
  4. 缺少确认回调时返回 `waiting_confirmation`，不会被误判为普通失败。

## P2-MEM-01 记忆作用域与控制面整理

- 状态：done
- 依赖：P2-SCHEMA-02
- 目标：整理记忆作用域、来源和用户控制边界。
- 涉及模块：
  - `src/ai/core/memory/service.py`
  - `src/ai/core/memory/types.py`
  - `src/ai/api/routes/memory.py`
  - `src/ai/api/schemas/memory.py`
- 验收标准：
  1. 用户可分辨记忆作用域和来源。
  2. 记忆删除和禁用语义清晰。
  3. API/TUI 可复用同一套表示。
- 已完成：
  1. 记忆领域对象新增 `scope`、`source_type`、`source_id`、`status` 字段。
  2. 保存、删除、启用、禁用同步到 `memory_entries` 控制面。
  3. API 支持按作用域/状态过滤，并提供状态切换入口。
  4. TUI 记忆列表和详情展示作用域、来源和状态。

## P2-RAG-01 RAG 文档边界与会话作用域治理

- 状态：done
- 依赖：P2-SCHEMA-02
- 目标：补齐 RAG 文档元信息、会话级作用域与清理主流程。
- 涉及模块：
  - `src/ai/core/rag/service.py`
  - `src/ai/api/routes/rag.py`
  - `src/ai/api/schemas/rag.py`
  - `docs/data.sql`
- 验收标准：
  1. 能区分全局和会话级文档。
  2. 文档删除、清理、重建行为可解释。
  3. 文档列表与实际索引状态一致。
- 已完成：
  1. `RagDocumentInfo`、API 响应和 TUI 文档列表补齐 `scope`、`status`、`collection_name`、`content_hash`。
  2. 索引和跳过重建时同步 `rag_documents` 控制面记录。
  3. 删除单文档、清空作用域和删除会话知识库时将控制面状态标记为 `deleted`。
  4. 文档列表合并 Chroma 实际分块与 DB 控制面状态，支持按状态查询。

## P2-CONTEXT-01 上下文来源可解释化

- 状态：done
- 依赖：P2-MEM-01、P2-RAG-01、P2-AGENT-02
- 目标：输出上下文来源摘要。
- 涉及模块：
  - `src/ai/core/context/service.py`
  - `src/ai/core/context/assembler.py`
  - `src/ai/core/context/types.py`
  - `src/ai/cli/tabs/chat_tab.py`
  - `src/ai/cli/tabs/agent_tab.py`
- 验收标准：
  1. 用户能知道当前回答使用了哪些来源类型。
  2. 调试时可区分历史上下文、记忆命中和 RAG 命中。
  3. 来源摘要不会泄露大段敏感原文。
- 已完成：
  1. 新增 `ContextSourceSummary`，从上下文段、预算报告和历史消息生成来源摘要。
  2. `ChatResult`、Chat API 响应、Agent 结果和 Agent API 响应统一携带 `context_sources`。
  3. TUI Chat/Agent 检视区展示来源类型、条目数、token 数和裁剪状态。
  4. 摘要只输出脱敏短文本，不展示大段原文。

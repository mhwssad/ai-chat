# 第二批：治理能力接入任务清单

## P2-TOOL-03 工具诊断与执行审计增强

- 状态：done
- 依赖：P2-TOOL-01、P2-TOOL-02
- 目标：补齐工具执行诊断信息和审计出口。
- 涉及模块：
  - `src/ai/core/tools/manager.py`
  - `src/ai/service/tool_service.py`
  - `src/ai/core/callbacks/audit.py`
  - `src/ai/storage/runtime_models.py`
  - `src/ai/storage/runtime_repository.py`
- 验收标准：
  1. 工具执行失败可追踪来源和错误类型。
  2. 诊断信息默认不泄漏敏感原文。
  3. 工具调用记录与审计记录语义一致。
- 已完成：
  1. 新增 `ToolExecutionDiagnostic` 诊断结果。
  2. 新增服务层 `execute_tool_diagnostic()`。
  3. API 工具执行响应补齐状态、耗时、权限、输入/输出摘要、错误字段。
  4. 工具执行诊断写入 `tool_calls` 和 `audit_logs`。

## P2-MCP-01 MCP 配置与状态存储化

- 状态：done
- 依赖：P2-SCHEMA-01
- 目标：把 MCP server 配置从运行时分散状态收敛到正式配置边界。
- 涉及模块：
  - `src/ai/core/mcp/config.py`
  - `src/ai/core/mcp/manager.py`
  - `docs/data.sql`
- 验收标准：
  1. MCP server 可持久化管理。
  2. 能区分未配置、已配置未连接、连接失败、连接成功。
  3. TUI/API 能消费统一状态结果。
- 已完成：
  1. MCP 配置仓库优先读取 `mcp_servers` 表，数据库无配置或不可用时回退 `mcp_servers.json`。
  2. MCP 子容器通过构造器注入 `session_factory`。
  3. MCP 健康检查新增 `not_configured`、`configured`、`available`、`error` 状态语义。

## P2-MCP-02 MCP 工具发现与同步

- 状态：done
- 依赖：P2-MCP-01、P2-TOOL-01
- 目标：建立 MCP 工具发现到 Tool Registry 的同步机制。
- 涉及模块：
  - `src/ai/core/mcp/tools.py`
  - `src/ai/core/mcp/adapter.py`
  - `src/ai/core/tools/register.py`
  - `src/ai/core/tools/registry.py`
- 验收标准：
  1. MCP 工具能出现在统一工具列表中。
  2. 断连或发现失败时状态可解释。
  3. 工具来源字段可区分 builtin 与 mcp。
- 已完成：
  1. `MCPManager.sync_tools()` 将发现到的 MCP 工具同步到统一注册表。
  2. MCP 工具元数据写入 `source_type=mcp` 与 `source_id=server_key`。
  3. 工具发现失败不阻断启动，并写入治理审计。

## P2-SKILL-01 Skills 发现与状态管理

- 状态：done
- 依赖：P2-SCHEMA-01
- 目标：补齐本地 Skills 的发现、启停和说明展示。
- 涉及模块：
  - `src/ai/core/skills/loader.py`
  - `src/ai/core/skills/service.py`
  - `src/ai/core/skills/types.py`
  - `src/ai/api/routes/skills.py`
- 验收标准：
  1. Skills 可列出、查看、启停。
  2. Skills 状态不是临时内存视图。
  3. 能为后续 Skill 工具暴露提供基础。
- 已完成：
  1. Skills 发现结果同步到 `skills` 配置表。
  2. 服务层合并数据库启停状态，并影响激活、斜杠命令和自动触发。
  3. API 增加 `enabled` 字段和 `POST /skills/{name}/enabled` 管理入口。

## P2-AUDIT-01 审计语义统一与脱敏规则

- 状态：done
- 依赖：P2-TOOL-03、P2-MCP-02、P2-SKILL-01、P2-SCHEMA-02
- 目标：统一模型、工具、MCP、Skills、权限决策和记忆操作的审计结构。
- 涉及模块：
  - `src/ai/core/callbacks/audit.py`
  - `src/ai/storage/runtime_models.py`
  - `src/ai/storage/runtime_repository.py`
  - `src/ai/utils/redaction.py`
  - `docs/data.sql`
- 验收标准：
  1. 关键行为都有统一审计入口。
  2. 默认不会把密钥和大段敏感文本直接入库。
  3. 审计记录足以支持问题追踪。
- 已完成：
  1. 新增 `AuditEvent` 与 `record_audit_event()` 统一审计入口。
  2. 工具诊断、LangChain callback、MCP 工具同步、Skills 启停和激活接入统一审计。
  3. 审计摘要统一通过 `redact_for_audit()` 脱敏和截断。

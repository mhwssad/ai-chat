# Data Model Requirements

## 1. 目标

本文档定义 AI Workbench MVP 的 SQLite 运行态数据模型。配置文件仍是系统显式配置的 source of truth，SQLite 只记录运行过程中发生的会话、消息、调用、权限、记忆索引、审计和系统状态。

当前实现对应代码位置：

- `src/ai_chat/memory/models.py`：会话、消息、摘要表。
- `src/ai_chat/storage/models.py`：模型调用、工具调用、权限决策、记忆条目、审计日志、系统状态和 schema 版本表。
- `src/ai_chat/storage/database.py`：runtime 数据库初始化入口。

## 2. 设计原则

- 会话和消息是聊天主流程的核心实体。
- 模型调用和工具调用是可观察性与审计的核心实体。
- 权限决策必须独立记录，便于复盘高风险操作。
- 审计日志记录摘要和引用，不默认保存完整敏感内容。
- 记忆条目先记录可审计索引边界，不在 MVP 阶段强制实现自动长期记忆。
- schema 版本表用于建立轻量迁移边界，后续可接入正式 migration 工具。

## 3. 表清单

### 3.1 `sessions`

会话元信息表，由 memory 模块维护。

核心字段：

- `session_id`：会话唯一标识。
- `title`：会话标题。
- `current_model`：当前会话后续消息默认模型。
- `message_count`：消息数量缓存。
- `status`：会话状态，例如 `active`、`archived`、`error`。
- `last_error`：最近错误摘要。
- `created_at`：创建时间。
- `updated_at`：更新时间。
- `metadata`：扩展信息。

### 3.2 `messages`

消息表，由 memory 模块维护。

核心字段：

- `id`：消息自增主键。
- `session_id`：所属会话。
- `role`：消息角色，例如 `human`、`ai`、`system`、`tool`。
- `content`：消息内容。
- `model`：生成或处理该消息的模型。
- `status`：消息状态，例如 `pending`、`streaming`、`completed`、`failed`、`partial`。
- `error_type`：错误类型。
- `error_message`：错误摘要。
- `created_at`：创建时间。
- `metadata`：扩展信息。

### 3.3 `summaries`

会话摘要表，用于会话内记忆压缩。

核心字段：

- `session_id`：关联会话。
- `summary`：摘要内容。
- `updated_at`：更新时间。

### 3.4 `model_calls`

模型调用记录表。

核心字段：

- `id`：调用记录主键。
- `session_id`：关联会话，可为空。
- `message_id`：关联消息，可为空。
- `provider`：供应商标识。
- `model`：模型标识。
- `request_id`：供应商或系统请求标识。
- `input_summary`：输入摘要。
- `output_summary`：输出摘要。
- `input_tokens`：输入 token 数。
- `output_tokens`：输出 token 数。
- `total_tokens`：总 token 数。
- `duration_ms`：耗时。
- `status`：调用状态。
- `error_type`：错误类型。
- `error_message`：错误摘要。
- `created_at`：创建时间。
- `metadata`：扩展信息。

### 3.5 `permission_decisions`

权限决策表。

核心字段：

- `id`：决策主键。
- `session_id`：关联会话，可为空。
- `capability_name`：能力或工具名称。
- `capability_source`：能力来源。
- `permission_scope`：权限范围，例如 `file_read`、`file_write`、`command_exec`。
- `decision`：决策结果，取值为 `allow`、`deny`、`ask`。
- `reason`：决策原因。
- `decided_by`：决策来源，例如 `policy`、`user`、`system`。
- `created_at`：创建时间。
- `metadata`：扩展信息。

### 3.6 `tool_calls`

工具调用记录表，覆盖内置工具、MCP 工具和 skill 派生工具。

核心字段：

- `id`：调用记录主键。
- `session_id`：关联会话，可为空。
- `message_id`：关联消息，可为空。
- `permission_decision_id`：关联权限决策，可为空。
- `tool_name`：工具名称。
- `source_type`：来源类型，例如 `builtin`、`mcp`、`skill`。
- `source_id`：来源标识。
- `input_summary`：输入摘要。
- `output_summary`：输出摘要。
- `duration_ms`：耗时。
- `status`：调用状态。
- `error_type`：错误类型。
- `error_message`：错误摘要。
- `created_at`：创建时间。
- `metadata`：扩展信息。

### 3.7 `memory_entries`

记忆条目和索引边界表。

核心字段：

- `id`：记忆条目主键。
- `session_id`：关联会话，可为空。
- `scope`：记忆范围，例如 `session`、`user`、`project`。
- `source_type`：来源类型，例如 `message`、`tool_result`、`manual`。
- `source_id`：来源标识。
- `content_summary`：内容摘要。
- `content_ref`：完整内容引用位置。
- `status`：状态，例如 `active`、`deleted`、`disabled`。
- `created_at`：创建时间。
- `updated_at`：更新时间。
- `metadata`：扩展信息。

### 3.8 `audit_logs`

通用审计日志表。

核心字段：

- `id`：审计记录主键。
- `session_id`：关联会话，可为空。
- `event_type`：事件类型，例如 `model_call`、`tool_call`、`permission_decision`、`memory_write`、`config_check`。
- `source_module`：来源模块。
- `target`：目标能力或对象。
- `input_summary`：输入摘要。
- `output_summary`：输出摘要。
- `status`：事件状态。
- `duration_ms`：耗时。
- `permission_decision`：权限决策摘要。
- `error_type`：错误类型。
- `error_message`：错误摘要。
- `created_at`：创建时间。
- `metadata`：扩展信息。

### 3.9 `system_states`

运行态系统状态表。

核心字段：

- `id`：状态记录主键。
- `state_key`：状态键。
- `state_value`：状态值。
- `scope`：作用域，例如 `global`、`provider`、`mcp`。
- `updated_at`：更新时间。
- `metadata`：扩展信息。

### 3.10 `schema_versions`

schema 版本表。

核心字段：

- `id`：版本记录主键。
- `schema_name`：schema 名称。
- `version`：版本号。
- `description`：说明。
- `applied_at`：应用时间。

## 4. 隐私与审计约束

- `input_summary` 和 `output_summary` 不应默认保存完整敏感内容。
- API Key、密钥、完整文件内容不应进入审计日志。
- 长文本应通过摘要或 `content_ref` 引用。
- 高风险工具调用必须能关联到权限决策。

## 5. 与旧表的兼容关系

项目已有 memory、llm、chains、prompts、workflows 等模块级存储表。本次新增 runtime 表不删除旧表。

后续进入 MVP 存储改造时，应逐步把 Web/CLI 共享核心服务迁移到统一 runtime 存储边界，再评估旧表是否合并、迁移或保留为模块私有表。

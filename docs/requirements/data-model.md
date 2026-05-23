# Data Model Requirements

## 1. 目标

本文档定义 AI Chat MVP 的 SQLite 数据模型。SQLite 是系统业务配置和运行态数据的 source of truth，负责保存供应商、模型、MCP server、skills、安全策略、会话、消息、调用、权限、记忆索引、审计和系统状态。

## 2. 实现状态

目标 schema 记录在 `docs/data.sql`。当前代码将进行重构，本文档不以旧代码中的数据库实现为准。

数据库文件位置建议：

| 文件              | 说明                                                         |
| ----------------- | ------------------------------------------------------------ |
| `data/app.db`     | 业务配置、会话、消息、调用记录、权限、记忆、审计和系统状态   |

## 3. 设计原则

- 供应商和模型配置是聊天主流程的基础实体，应支持数据库增删改查。
- 会话和消息是聊天主流程的核心实体。
- 模型调用和工具调用是可观察性与审计的核心实体。
- 权限决策必须独立记录，便于复盘高风险操作。
- 审计日志记录摘要和引用，不默认保存完整敏感内容。
- 记忆条目先记录可审计索引边界，不在 MVP 阶段强制实现自动长期记忆。
- schema 版本表用于建立轻量迁移边界，后续可接入正式 migration 工具。

## 3. 表清单

### 3.1 `providers`

供应商配置表。

核心字段：

- `id`：供应商主键。
- `provider_key`：供应商唯一标识。
- `display_name`：显示名称。
- `base_url`：基础 URL。
- `api_key_encrypted`：加密保存的 API Key，禁止明文入库。
- `default_model_id`：默认模型。
- `enabled`：是否启用。
- `status`：状态，例如 `unknown`、`available`、`unavailable`、`error`。
- `last_checked_at`：最近检查时间。
- `created_at`：创建时间。
- `updated_at`：更新时间。
- `metadata`：扩展信息。

### 3.2 `models`

模型配置表。

核心字段：

- `id`：模型主键。
- `provider_id`：所属供应商。
- `model_key`：供应商内模型标识。
- `display_name`：显示名称。
- `model_type`：模型类型，例如 `chat`、`embedding`、`vision`、`image`。
- `request_type`：请求协议类型，例如 `openai_compatible`、`anthropic`、`ollama`。
- `capabilities`：能力标签 JSON，例如 chat、tools、vision、embedding、reasoning。
- `supports_streaming`：是否支持流式输出。
- `supports_tools`：是否支持工具调用。
- `supports_vision`：是否支持视觉输入。
- `supports_embedding`：是否支持 embedding。
- `supports_reasoning`：是否支持推理能力。
- `context_window`：上下文长度。
- `max_output_tokens`：最大输出 token 数。
- `pricing_strategy`：计费策略，例如 `token`、`quantity`、`duration`、`flat`。
- `pricing_unit`：计费单位，例如 `token_1k`、`image`、`second`、`request`。
- `pricing_unit_size`：每个计费单位包含的用量，例如 1000 token 或 60 秒。
- `input_price`：输入维度单价，适用于 token 等区分输入/输出的模型。
- `output_price`：输出维度单价，适用于 token 等区分输入/输出的模型。
- `total_price`：总量维度单价，适用于图片、音频、视频等按总量计费的模型。
- `flat_price`：每次请求固定价格。
- `currency`：价格币种，默认 `USD`。
- `enabled`：是否启用。
- `created_at`：创建时间。
- `updated_at`：更新时间。
- `metadata`：扩展信息。

### 3.3 `app_settings`

基础系统设置表。

核心字段：

- `setting_key`：设置键。
- `setting_value`：设置值。
- `value_type`：值类型，例如 `string`、`number`、`boolean`、`json`。
- `description`：说明。
- `updated_at`：更新时间。
- `metadata`：扩展信息。

### 3.4 `mcp_servers`

MCP server 配置表。

核心字段：

- `id`：server 主键。
- `server_key`：server 唯一标识。
- `display_name`：显示名称。
- `transport`：连接方式。
- `command`：启动命令。
- `args`：启动参数 JSON。
- `url`：远程连接地址。
- `env`：环境变量引用 JSON。
- `permission_policy`：权限策略 JSON。
- `enabled`：是否启用。
- `status`：状态。
- `last_checked_at`：最近检查时间。
- `created_at`：创建时间。
- `updated_at`：更新时间。
- `metadata`：扩展信息。

### 3.5 `skills`

Skill 配置和发现结果表。

核心字段：

- `id`：skill 主键。
- `skill_key`：skill 唯一标识。
- `display_name`：显示名称。
- `description`：说明。
- `version`：版本。
- `source_path`：本地来源路径。
- `capabilities`：能力说明 JSON。
- `enabled`：是否启用。
- `created_at`：创建时间。
- `updated_at`：更新时间。
- `metadata`：扩展信息。

### 3.6 `security_policies`

安全策略表。

核心字段：

- `id`：策略主键。
- `policy_key`：策略唯一标识。
- `scope`：策略作用域。
- `rule`：策略规则 JSON。
- `enabled`：是否启用。
- `created_at`：创建时间。
- `updated_at`：更新时间。
- `metadata`：扩展信息。

### 3.7 `sessions`

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

### 3.8 `messages`

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

### 3.9 `summaries`

会话摘要表，用于会话内记忆压缩。

核心字段：

- `session_id`：关联会话。
- `summary`：摘要内容。
- `updated_at`：更新时间。

### 3.10 `model_calls`

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
- `input_cost`：输入费用。
- `output_cost`：输出费用。
- `total_cost`：总费用。
- `currency`：费用币种。
- `duration_ms`：耗时。
- `status`：调用状态。
- `error_type`：错误类型。
- `error_message`：错误摘要。
- `created_at`：创建时间。
- `metadata`：扩展信息。

### 3.11 `permission_decisions`

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

### 3.12 `tool_calls`

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

### 3.13 `memory_entries`

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

### 3.14 `audit_logs`

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

### 3.15 `system_states`

运行态系统状态表。

核心字段：

- `id`：状态记录主键。
- `state_key`：状态键。
- `state_value`：状态值。
- `scope`：作用域，例如 `global`、`provider`、`mcp`。
- `updated_at`：更新时间。
- `metadata`：扩展信息。

### 3.16 `schema_versions`

schema 版本表。

核心字段：

- `id`：版本记录主键。
- `schema_name`：schema 名称。
- `version`：版本号。
- `description`：说明。
- `applied_at`：应用时间。

## 4. 隐私与审计约束

- `input_summary` 和 `output_summary` 不应默认保存完整敏感内容。
- API Key、密钥、完整文件内容不应进入审计日志。API Key 应加密保存在配置表中，禁止明文入库。
- 长文本应通过摘要或 `content_ref` 引用。
- 高风险工具调用必须能关联到权限决策。

## 5. 与旧表的兼容关系

当前代码将进行大重构，目标 schema 不要求兼容旧表。迁移实现应以本文档和 `docs/data.sql` 为准。

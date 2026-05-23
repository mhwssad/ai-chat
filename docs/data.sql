PRAGMA foreign_keys = ON;

BEGIN;

-- ============================================================
-- schema_versions: 数据库 Schema 版本控制表
-- 记录每次 Schema 变更的版本信息
-- ============================================================
CREATE TABLE IF NOT EXISTS schema_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,           -- 自增主键
    schema_name TEXT NOT NULL UNIQUE,              -- Schema 名称，如 'runtime'
    version INTEGER NOT NULL,                      -- 版本号
    description TEXT,                              -- 版本描述信息
    applied_at TEXT NOT NULL DEFAULT (datetime('now'))  -- 应用时间
);

-- ============================================================
-- app_settings: 基础系统设置表
-- 存储默认模型等可管理配置项，配置文件只保留启动期最小引导
-- ============================================================
CREATE TABLE IF NOT EXISTS app_settings (
    setting_key TEXT PRIMARY KEY,                  -- 设置键
    setting_value TEXT NOT NULL,                   -- 设置值
    value_type TEXT NOT NULL DEFAULT 'string'
        CHECK (value_type IN ('string', 'number', 'boolean', 'json')), -- 值类型
    description TEXT,                              -- 设置说明
    updated_at TEXT NOT NULL DEFAULT (datetime('now')), -- 更新时间
    metadata TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(metadata)) -- 扩展元数据
);

-- ============================================================
-- providers: 模型供应商配置表
-- 存储供应商连接配置；不保存明文 API Key
-- ============================================================
CREATE TABLE IF NOT EXISTS providers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,          -- 自增主键
    provider_key TEXT NOT NULL UNIQUE,             -- 供应商唯一标识
    display_name TEXT,                             -- 显示名称
    base_url TEXT,                                 -- API 基础 URL
    api_key_encrypted TEXT,                        -- 加密保存的 API Key，禁止明文入库
    default_model_id INTEGER,                      -- 默认模型 ID
    enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)), -- 是否启用
    status TEXT NOT NULL DEFAULT 'unknown'
        CHECK (status IN ('unknown', 'available', 'unavailable', 'error')), -- 健康状态
    last_checked_at TEXT,                          -- 最近检查时间
    created_at TEXT NOT NULL DEFAULT (datetime('now')), -- 创建时间
    updated_at TEXT NOT NULL DEFAULT (datetime('now')), -- 更新时间
    metadata TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(metadata)), -- 扩展元数据
    FOREIGN KEY (default_model_id) REFERENCES models (id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_providers_enabled
    ON providers (enabled);

CREATE INDEX IF NOT EXISTS idx_providers_status
    ON providers (status);

-- ============================================================
-- models: 模型配置表
-- 存储可用模型、能力标签和启用状态
-- ============================================================
CREATE TABLE IF NOT EXISTS models (
    id INTEGER PRIMARY KEY AUTOINCREMENT,          -- 自增主键
    provider_id INTEGER NOT NULL,                  -- 所属供应商 ID
    model_key TEXT NOT NULL,                       -- 供应商内模型标识
    display_name TEXT,                             -- 显示名称
    model_type TEXT NOT NULL DEFAULT 'chat'
        CHECK (model_type IN ('chat', 'completion', 'embedding', 'vision', 'image', 'audio', 'rerank')), -- 模型类型
    request_type TEXT NOT NULL DEFAULT 'openai_compatible', -- 请求协议类型
    capabilities TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(capabilities)), -- 能力标签 JSON
    supports_streaming INTEGER NOT NULL DEFAULT 1 CHECK (supports_streaming IN (0, 1)),
    supports_tools INTEGER NOT NULL DEFAULT 0 CHECK (supports_tools IN (0, 1)),
    supports_vision INTEGER NOT NULL DEFAULT 0 CHECK (supports_vision IN (0, 1)),
    supports_embedding INTEGER NOT NULL DEFAULT 0 CHECK (supports_embedding IN (0, 1)),
    supports_reasoning INTEGER NOT NULL DEFAULT 0 CHECK (supports_reasoning IN (0, 1)),
    context_window INTEGER CHECK (context_window IS NULL OR context_window > 0),
    max_output_tokens INTEGER CHECK (max_output_tokens IS NULL OR max_output_tokens > 0),
    pricing_strategy TEXT NOT NULL DEFAULT 'token'
        CHECK (pricing_strategy IN ('token', 'quantity', 'duration', 'flat')),
    pricing_unit TEXT NOT NULL DEFAULT 'token_1k',
    pricing_unit_size REAL NOT NULL DEFAULT 1000 CHECK (pricing_unit_size > 0),
    input_price REAL CHECK (input_price IS NULL OR input_price >= 0),
    output_price REAL CHECK (output_price IS NULL OR output_price >= 0),
    total_price REAL CHECK (total_price IS NULL OR total_price >= 0),
    flat_price REAL CHECK (flat_price IS NULL OR flat_price >= 0),
    currency TEXT NOT NULL DEFAULT 'USD',
    enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)), -- 是否启用
    created_at TEXT NOT NULL DEFAULT (datetime('now')), -- 创建时间
    updated_at TEXT NOT NULL DEFAULT (datetime('now')), -- 更新时间
    metadata TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(metadata)), -- 扩展元数据
    UNIQUE (provider_id, model_key),
    FOREIGN KEY (provider_id) REFERENCES providers (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_models_provider_enabled
    ON models (provider_id, enabled);

CREATE INDEX IF NOT EXISTS idx_models_type_enabled
    ON models (model_type, enabled);

-- ============================================================
-- mcp_servers: MCP Server 配置表
-- 存储 MCP 连接方式、启用状态和权限策略
-- ============================================================
CREATE TABLE IF NOT EXISTS mcp_servers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    server_key TEXT NOT NULL UNIQUE,
    display_name TEXT,
    transport TEXT NOT NULL CHECK (transport IN ('stdio', 'http', 'sse', 'websocket')),
    command TEXT,
    args TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(args)),
    url TEXT,
    env TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(env)),
    permission_policy TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(permission_policy)),
    enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
    status TEXT NOT NULL DEFAULT 'unknown'
        CHECK (status IN ('unknown', 'available', 'unavailable', 'error')),
    last_checked_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    metadata TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(metadata))
);

CREATE INDEX IF NOT EXISTS idx_mcp_servers_enabled
    ON mcp_servers (enabled);

CREATE INDEX IF NOT EXISTS idx_mcp_servers_status
    ON mcp_servers (status);

-- ============================================================
-- skills: Skill 配置和发现结果表
-- 存储 skill 元数据和启用状态
-- ============================================================
CREATE TABLE IF NOT EXISTS skills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    skill_key TEXT NOT NULL UNIQUE,
    display_name TEXT,
    description TEXT,
    version TEXT,
    source_path TEXT,
    capabilities TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(capabilities)),
    enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    metadata TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(metadata))
);

CREATE INDEX IF NOT EXISTS idx_skills_enabled
    ON skills (enabled);

-- ============================================================
-- security_policies: 安全策略表
-- 存储权限策略和高风险操作规则
-- ============================================================
CREATE TABLE IF NOT EXISTS security_policies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    policy_key TEXT NOT NULL UNIQUE,
    scope TEXT NOT NULL,
    rule TEXT NOT NULL CHECK (json_valid(rule)),
    enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    metadata TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(metadata))
);

CREATE INDEX IF NOT EXISTS idx_security_policies_scope_enabled
    ON security_policies (scope, enabled);

-- ============================================================
-- prompt_templates: 提示词模板表
-- 使用数据库保存 Jinja2 提示词模板
-- ============================================================
CREATE TABLE IF NOT EXISTS prompt_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt_key TEXT NOT NULL UNIQUE,
    display_name TEXT,
    description TEXT,
    category TEXT NOT NULL DEFAULT 'general',
    template TEXT NOT NULL,
    template_format TEXT NOT NULL DEFAULT 'jinja2'
        CHECK (template_format IN ('jinja2')),
    version INTEGER NOT NULL DEFAULT 1 CHECK (version > 0),
    enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    metadata TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(metadata))
);

CREATE INDEX IF NOT EXISTS idx_prompt_templates_enabled
    ON prompt_templates (enabled);

CREATE INDEX IF NOT EXISTS idx_prompt_templates_category
    ON prompt_templates (category);

-- ============================================================
-- prompt_versions: 提示词模板历史版本表
-- ============================================================
CREATE TABLE IF NOT EXISTS prompt_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt_id INTEGER NOT NULL,
    version INTEGER NOT NULL CHECK (version > 0),
    template TEXT NOT NULL,
    change_note TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    metadata TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(metadata)),
    FOREIGN KEY (prompt_id) REFERENCES prompt_templates (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_prompt_versions_prompt
    ON prompt_versions (prompt_id, version);

-- ============================================================
-- sessions: 会话信息表
-- 存储会话的基本信息和状态
-- ============================================================
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,                   -- 会话唯一标识符 (UUID)
    title TEXT,                                    -- 会话标题
    current_model TEXT,                            -- 当前使用的模型名称
    current_model_id INTEGER,                      -- 当前使用的模型 ID
    message_count INTEGER NOT NULL DEFAULT 0 CHECK (message_count >= 0),  -- 消息总数
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'archived', 'error')),  -- 会话状态：活跃/归档/错误
    last_error TEXT,                               -- 最后一次错误信息
    created_at TEXT NOT NULL DEFAULT (datetime('now')),    -- 创建时间
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),    -- 最后更新时间
    metadata TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(metadata)),  -- 扩展元数据 JSON
    FOREIGN KEY (current_model_id) REFERENCES models (id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_sessions_updated_at
    ON sessions (updated_at DESC);  -- 按更新时间降序索引，用于查询最近活跃会话

CREATE INDEX IF NOT EXISTS idx_sessions_status
    ON sessions (status);  -- 按状态索引，用于筛选特定状态的会话

-- ============================================================
-- messages: 消息表
-- 存储会话中的所有消息记录
-- ============================================================
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,          -- 自增主键
    session_id TEXT NOT NULL,                       -- 关联的会话 ID
    role TEXT NOT NULL CHECK (role IN ('human', 'ai', 'system', 'tool')),  -- 消息角色：用户/AI/系统/工具
    content TEXT NOT NULL,                         -- 消息内容
    model TEXT,                                    -- 生成该消息的模型名称
    model_id INTEGER,                              -- 生成该消息的模型 ID
    status TEXT NOT NULL DEFAULT 'completed'       -- 消息状态
        CHECK (status IN ('pending', 'streaming', 'completed', 'failed', 'partial')),  -- 待处理/流式/完成/失败/部分完成
    error_type TEXT,                               -- 错误类型
    error_message TEXT,                            -- 错误信息
    created_at TEXT NOT NULL DEFAULT (datetime('now')),  -- 创建时间
    metadata TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(metadata)),  -- 扩展元数据
    FOREIGN KEY (session_id) REFERENCES sessions (session_id) ON DELETE CASCADE,  -- 级联删除
    FOREIGN KEY (model_id) REFERENCES models (id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_messages_session_created
    ON messages (session_id, created_at, id);  -- 按会话和时间索引，用于获取会话消息列表

CREATE INDEX IF NOT EXISTS idx_messages_status
    ON messages (status);  -- 按状态索引，用于筛选特定状态的消息

-- ============================================================
-- summaries: 会话摘要表
-- 存储每个会话的 AI 生成摘要
-- ============================================================
CREATE TABLE IF NOT EXISTS summaries (
    session_id TEXT PRIMARY KEY,                   -- 会话 ID (唯一)
    summary TEXT NOT NULL,                         -- 摘要内容
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),  -- 最后更新时间
    FOREIGN KEY (session_id) REFERENCES sessions (session_id) ON DELETE CASCADE  -- 级联删除
);

-- ============================================================
-- model_calls: 模型调用记录表
-- 记录所有 LLM API 调用，用于计费和调试
-- ============================================================
CREATE TABLE IF NOT EXISTS model_calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,          -- 自增主键
    session_id TEXT,                               -- 关联的会话 ID (可为空)
    message_id INTEGER,                            -- 关联的消息 ID (可为空)
    provider_id INTEGER,                           -- 关联的供应商 ID
    model_id INTEGER,                              -- 关联的模型 ID
    provider TEXT NOT NULL,                        -- 模型提供商，如 'openai', 'anthropic'
    model TEXT NOT NULL,                          -- 模型名称
    request_id TEXT,                              -- 请求 ID (用于追踪)
    input_summary TEXT,                           -- 输入摘要 (用于日志)
    output_summary TEXT,                           -- 输出摘要 (用于日志)
    input_tokens INTEGER CHECK (input_tokens IS NULL OR input_tokens >= 0),   -- 输入 Token 数
    output_tokens INTEGER CHECK (output_tokens IS NULL OR output_tokens >= 0),  -- 输出 Token 数
    total_tokens INTEGER CHECK (total_tokens IS NULL OR total_tokens >= 0),   -- 总 Token 数
    input_cost REAL CHECK (input_cost IS NULL OR input_cost >= 0),
    output_cost REAL CHECK (output_cost IS NULL OR output_cost >= 0),
    total_cost REAL CHECK (total_cost IS NULL OR total_cost >= 0),
    currency TEXT,
    duration_ms INTEGER CHECK (duration_ms IS NULL OR duration_ms >= 0),      -- 调用耗时(毫秒)
    status TEXT NOT NULL CHECK (status IN ('pending', 'success', 'failed', 'timeout', 'cancelled')),  -- 调用状态
    error_type TEXT,                               -- 错误类型
    error_message TEXT,                            -- 错误信息
    created_at TEXT NOT NULL DEFAULT (datetime('now')),  -- 创建时间
    metadata TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(metadata)),  -- 扩展元数据
    FOREIGN KEY (session_id) REFERENCES sessions (session_id) ON DELETE SET NULL,  -- 会话删除时置空
    FOREIGN KEY (message_id) REFERENCES messages (id) ON DELETE SET NULL,  -- 消息删除时置空
    FOREIGN KEY (provider_id) REFERENCES providers (id) ON DELETE SET NULL,
    FOREIGN KEY (model_id) REFERENCES models (id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_model_calls_session_created
    ON model_calls (session_id, created_at DESC);  -- 按会话和时间降序索引

CREATE INDEX IF NOT EXISTS idx_model_calls_provider_model
    ON model_calls (provider, model);  -- 按提供商和模型索引，用于统计用量

CREATE INDEX IF NOT EXISTS idx_model_calls_status
    ON model_calls (status);  -- 按状态索引，用于查询失败调用

-- ============================================================
-- permission_decisions: 权限决策表
-- 记录每次工具调用的权限检查决策
-- ============================================================
CREATE TABLE IF NOT EXISTS permission_decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,          -- 自增主键
    session_id TEXT,                               -- 关联的会话 ID (可为空)
    capability_name TEXT NOT NULL,                 -- 能力名称，如 'file_read', 'code_execute'
    capability_source TEXT,                         -- 能力来源，如 'mcp_server_name'
    permission_scope TEXT NOT NULL,                 -- 权限范围，如 'session', 'global'
    decision TEXT NOT NULL CHECK (decision IN ('allow', 'deny', 'ask')),  -- 决策结果：允许/拒绝/询问
    reason TEXT,                                   -- 决策原因
    decided_by TEXT NOT NULL CHECK (decided_by IN ('policy', 'user', 'system')),  -- 决策者：策略/用户/系统
    created_at TEXT NOT NULL DEFAULT (datetime('now')),  -- 创建时间
    metadata TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(metadata)),  -- 扩展元数据
    FOREIGN KEY (session_id) REFERENCES sessions (session_id) ON DELETE SET NULL  -- 会话删除时置空
);

CREATE INDEX IF NOT EXISTS idx_permission_decisions_session_created
    ON permission_decisions (session_id, created_at DESC);  -- 按会话和时间降序索引

CREATE INDEX IF NOT EXISTS idx_permission_decisions_capability
    ON permission_decisions (capability_name, capability_source);  -- 按能力索引

CREATE INDEX IF NOT EXISTS idx_permission_decisions_scope_decision
    ON permission_decisions (permission_scope, decision);  -- 按范围和决策索引

-- ============================================================
-- tool_calls: 工具调用记录表
-- 记录所有工具执行情况
-- ============================================================
CREATE TABLE IF NOT EXISTS tool_calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,          -- 自增主键
    session_id TEXT,                               -- 关联的会话 ID (可为空)
    message_id INTEGER,                            -- 关联的消息 ID (可为空)
    permission_decision_id INTEGER,                -- 关联的权限决策 ID (可为空)
    tool_name TEXT NOT NULL,                      -- 工具名称
    source_type TEXT NOT NULL CHECK (source_type IN ('builtin', 'mcp', 'skill')),  -- 来源类型：内置/MCP/技能
    source_id TEXT,                                -- 来源 ID，如 MCP 服务器名称
    input_summary TEXT,                            -- 输入摘要 (脱敏后的参数概要)
    output_summary TEXT,                           -- 输出摘要 (结果概要)
    duration_ms INTEGER CHECK (duration_ms IS NULL OR duration_ms >= 0),  -- 执行耗时(毫秒)
    status TEXT NOT NULL CHECK (status IN ('pending', 'success', 'failed', 'timeout', 'cancelled')),  -- 执行状态
    error_type TEXT,                               -- 错误类型
    error_message TEXT,                            -- 错误信息
    created_at TEXT NOT NULL DEFAULT (datetime('now')),  -- 创建时间
    metadata TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(metadata)),  -- 扩展元数据
    FOREIGN KEY (session_id) REFERENCES sessions (session_id) ON DELETE SET NULL,  -- 会话删除时置空
    FOREIGN KEY (message_id) REFERENCES messages (id) ON DELETE SET NULL,  -- 消息删除时置空
    FOREIGN KEY (permission_decision_id) REFERENCES permission_decisions (id) ON DELETE SET NULL  -- 权限决策删除时置空
);

CREATE INDEX IF NOT EXISTS idx_tool_calls_session_created
    ON tool_calls (session_id, created_at DESC);  -- 按会话和时间降序索引

CREATE INDEX IF NOT EXISTS idx_tool_calls_tool_source
    ON tool_calls (tool_name, source_type, source_id);  -- 按工具和来源索引

CREATE INDEX IF NOT EXISTS idx_tool_calls_status
    ON tool_calls (status);  -- 按状态索引，用于查询失败调用

-- ============================================================
-- rag_documents: RAG 文档索引表
-- ============================================================
CREATE TABLE IF NOT EXISTS rag_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_path TEXT NOT NULL,
    source_type TEXT NOT NULL DEFAULT 'file',
    title TEXT,
    content_hash TEXT NOT NULL,
    mime_type TEXT,
    size_bytes INTEGER CHECK (size_bytes IS NULL OR size_bytes >= 0),
    chunk_count INTEGER NOT NULL DEFAULT 0 CHECK (chunk_count >= 0),
    status TEXT NOT NULL DEFAULT 'indexed'
        CHECK (status IN ('indexed', 'deleted', 'failed')),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    metadata TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(metadata)),
    UNIQUE (source_path, content_hash)
);

CREATE INDEX IF NOT EXISTS idx_rag_documents_source_path
    ON rag_documents (source_path);

-- ============================================================
-- rag_chunks: RAG 文档切片表
-- ============================================================
CREATE TABLE IF NOT EXISTS rag_chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL,
    chunk_index INTEGER NOT NULL CHECK (chunk_index >= 0),
    content TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    token_count INTEGER CHECK (token_count IS NULL OR token_count >= 0),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    metadata TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(metadata)),
    FOREIGN KEY (document_id) REFERENCES rag_documents (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_rag_chunks_document
    ON rag_chunks (document_id, chunk_index);

-- ============================================================
-- rag_embeddings: RAG 向量表
-- ============================================================
CREATE TABLE IF NOT EXISTS rag_embeddings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chunk_id INTEGER NOT NULL,
    embedding_model TEXT NOT NULL,
    dimension INTEGER NOT NULL CHECK (dimension > 0),
    vector TEXT NOT NULL CHECK (json_valid(vector)),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    metadata TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(metadata)),
    UNIQUE (chunk_id, embedding_model),
    FOREIGN KEY (chunk_id) REFERENCES rag_chunks (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_rag_embeddings_model
    ON rag_embeddings (embedding_model);

-- ============================================================
-- memory_entries: 记忆条目表
-- 存储持久化记忆内容，支持多级作用域
-- ============================================================
CREATE TABLE IF NOT EXISTS memory_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,          -- 自增主键
    session_id TEXT,                               -- 关联的会话 ID (可为空)
    scope TEXT NOT NULL CHECK (scope IN ('session', 'user', 'project', 'team')),  -- 作用域：会话/用户/项目/团队
    memory_type TEXT NOT NULL DEFAULT 'project'
        CHECK (memory_type IN ('user', 'feedback', 'project', 'reference')), -- 记忆类型
    source_type TEXT NOT NULL CHECK (source_type IN ('message', 'tool_result', 'manual', 'auto_memory', 'team_memory')),  -- 来源类型
    source_id TEXT,                                -- 来源 ID，如消息 ID 或工具调用 ID
    content_summary TEXT NOT NULL,                -- 内容摘要 (用于检索)
    content_ref TEXT,                              -- 内容引用 (指向实际存储位置)
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'deleted', 'disabled')),  -- 状态：活跃/已删除/已禁用
    created_at TEXT NOT NULL DEFAULT (datetime('now')),  -- 创建时间
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),  -- 最后更新时间
    metadata TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(metadata)),  -- 扩展元数据
    FOREIGN KEY (session_id) REFERENCES sessions (session_id) ON DELETE SET NULL  -- 会话删除时置空
);

CREATE INDEX IF NOT EXISTS idx_memory_entries_session_scope
    ON memory_entries (session_id, scope);  -- 按会话和作用域索引

CREATE INDEX IF NOT EXISTS idx_memory_entries_scope_status
    ON memory_entries (scope, status);  -- 按作用域和状态索引

CREATE INDEX IF NOT EXISTS idx_memory_entries_source
    ON memory_entries (source_type, source_id);  -- 按来源索引，用于查找来源

-- ============================================================
-- audit_logs: 审计日志表
-- 记录所有重要操作的审计信息
-- ============================================================
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,          -- 自增主键
    session_id TEXT,                               -- 关联的会话 ID (可为空)
    event_type TEXT NOT NULL,                     -- 事件类型，如 'tool_call', 'model_call', 'permission_check'
    source_module TEXT,                            -- 源模块，如 'agent', 'tools', 'memory'
    target TEXT,                                   -- 目标，如工具名或资源路径
    input_summary TEXT,                            -- 输入摘要
    output_summary TEXT,                           -- 输出摘要
    status TEXT NOT NULL CHECK (status IN ('success', 'failed', 'denied', 'cancelled')),  -- 操作状态
    duration_ms INTEGER CHECK (duration_ms IS NULL OR duration_ms >= 0),  -- 操作耗时(毫秒)
    permission_decision TEXT,                      -- 权限决策摘要
    error_type TEXT,                               -- 错误类型
    error_message TEXT,                            -- 错误信息
    created_at TEXT NOT NULL DEFAULT (datetime('now')),  -- 创建时间
    metadata TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(metadata)),  -- 扩展元数据
    FOREIGN KEY (session_id) REFERENCES sessions (session_id) ON DELETE SET NULL  -- 会话删除时置空
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_session_created
    ON audit_logs (session_id, created_at DESC);  -- 按会话和时间降序索引

CREATE INDEX IF NOT EXISTS idx_audit_logs_event_type
    ON audit_logs (event_type);  -- 按事件类型索引，用于统计

CREATE INDEX IF NOT EXISTS idx_audit_logs_status
    ON audit_logs (status);  -- 按状态索引，用于查询异常

-- ============================================================
-- system_states: 系统状态表
-- 存储系统运行时状态，支持多级作用域
-- ============================================================
CREATE TABLE IF NOT EXISTS system_states (
    id INTEGER PRIMARY KEY AUTOINCREMENT,          -- 自增主键
    state_key TEXT NOT NULL,                       -- 状态键，如 'last_sync_time', 'model_config'
    state_value TEXT NOT NULL,                     -- 状态值 (JSON 格式)
    scope TEXT NOT NULL DEFAULT 'global' CHECK (scope IN ('global', 'provider', 'mcp')),  -- 作用域：全局/提供商/MCP
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),  -- 最后更新时间
    metadata TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(metadata)),  -- 扩展元数据
    UNIQUE (scope, state_key)  -- 作用域内状态键唯一
);

CREATE INDEX IF NOT EXISTS idx_system_states_scope
    ON system_states (scope);  -- 按作用域索引

-- ============================================================
-- 初始化 Schema 版本记录
-- ============================================================
INSERT INTO schema_versions (schema_name, version, description)
VALUES ('app', 1, 'Initial MVP SQLite schema for database-managed configuration and runtime data')
ON CONFLICT(schema_name) DO UPDATE SET
    version = excluded.version,
    description = excluded.description,
    applied_at = datetime('now');

COMMIT;

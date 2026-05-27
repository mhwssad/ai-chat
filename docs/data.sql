PRAGMA foreign_keys = ON;

BEGIN;

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
-- model_calls: 模型调用记录表
-- 记录所有 LLM API 调用，用于计费和调试
-- ============================================================
CREATE TABLE IF NOT EXISTS model_calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,          -- 自增主键
    session_id TEXT,                               -- 关联的会话 ID (可为空，仅用于分组)
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
    metadata TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(metadata))  -- 扩展元数据
);

CREATE INDEX IF NOT EXISTS idx_model_calls_session_created
    ON model_calls (session_id, created_at DESC);  -- 按会话和时间降序索引

CREATE INDEX IF NOT EXISTS idx_model_calls_model
    ON model_calls (model);  -- 按模型索引，用于统计用量

CREATE INDEX IF NOT EXISTS idx_model_calls_status
    ON model_calls (status);  -- 按状态索引，用于查询失败调用

-- ============================================================
-- tool_calls: 工具调用记录表
-- 记录所有工具执行情况
-- ============================================================
CREATE TABLE IF NOT EXISTS tool_calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,          -- 自增主键
    session_id TEXT,                               -- 关联的会话 ID (可为空，仅用于分组)
    tool_name TEXT NOT NULL,                      -- 工具名称
    source_type TEXT NOT NULL CHECK (source_type IN ('builtin', 'mcp')),  -- 来源类型：内置/MCP
    source_id TEXT,                                -- 来源 ID，如 MCP 服务器名称
    input_summary TEXT,                            -- 输入摘要 (脱敏后的参数概要)
    output_summary TEXT,                           -- 输出摘要 (结果概要)
    duration_ms INTEGER CHECK (duration_ms IS NULL OR duration_ms >= 0),  -- 执行耗时(毫秒)
    status TEXT NOT NULL CHECK (status IN ('pending', 'success', 'failed', 'timeout', 'cancelled')),  -- 执行状态
    error_type TEXT,                               -- 错误类型
    error_message TEXT,                            -- 错误信息
    created_at TEXT NOT NULL DEFAULT (datetime('now')),  -- 创建时间
    metadata TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(metadata))  -- 扩展元数据
);

CREATE INDEX IF NOT EXISTS idx_tool_calls_session_created
    ON tool_calls (session_id, created_at DESC);  -- 按会话和时间降序索引

CREATE INDEX IF NOT EXISTS idx_tool_calls_tool_source
    ON tool_calls (tool_name, source_type, source_id);  -- 按工具和来源索引

CREATE INDEX IF NOT EXISTS idx_tool_calls_status
    ON tool_calls (status);  -- 按状态索引，用于查询失败调用

-- ============================================================
-- memory_entries: 记忆条目表
-- 存储持久化记忆内容，支持多级作用域
-- ============================================================
CREATE TABLE IF NOT EXISTS memory_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,          -- 自增主键
    session_id TEXT,                               -- 关联的会话 ID (可为空，仅用于分组)
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
    metadata TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(metadata))  -- 扩展元数据
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
    session_id TEXT,                               -- 关联的会话 ID (可为空，仅用于分组)
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
    metadata TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(metadata))  -- 扩展元数据
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_session_created
    ON audit_logs (session_id, created_at DESC);  -- 按会话和时间降序索引

CREATE INDEX IF NOT EXISTS idx_audit_logs_event_type
    ON audit_logs (event_type);  -- 按事件类型索引，用于统计

CREATE INDEX IF NOT EXISTS idx_audit_logs_status
    ON audit_logs (status);  -- 按状态索引，用于查询异常

-- ============================================================
-- 预置提示词模板
-- 使用 INSERT OR IGNORE 避免重复插入，保留用户自定义
-- ============================================================
INSERT OR IGNORE INTO prompt_templates (prompt_key, display_name, description, category, template, template_format, metadata)
VALUES (
    'memory.system_prompt',
    '记忆系统提示词',
    '注入模型的记忆系统说明，包含记忆类型、使用规则和 MEMORY.md 入口',
    'memory',
    '# {{ display_name }} Memory

记忆类型：
- user：用户角色、目标、职责、偏好和稳定知识。
- feedback：用户给出的工作指导、纠正和确认。
- project：当前项目目标、正在进行的工作、bug 和事件。
- reference：外部系统资源指针，例如 issue、文档或任务链接。

使用规则：
- 只使用和当前任务相关的记忆。
- 不保存可从代码直接推导出的普通实现细节。
- 不保存 API Key、token、密码或其他敏感信息。
- 当记忆和当前用户指令冲突时，以当前用户指令为准。{% if extra_guidelines %}

额外规则：
{% for item in extra_guidelines -%}
- {{ item }}
{% endfor %}{% endif %}{% if entrypoint %}

## MEMORY.md
{{ entrypoint }}{% endif %}',
    'jinja2',
    '{}'
);

INSERT OR IGNORE INTO prompt_templates (prompt_key, display_name, description, category, template, template_format, metadata)
VALUES (
    'memory.context_header',
    '上下文记忆头部',
    '将上下文记忆条目格式化为可注入模型的提示片段',
    'memory',
    '# {{ display_name }} Memory
{% for entry in entries -%}
{{ entry.label }} {{ entry.content }}
{% endfor %}',
    'jinja2',
    '{}'
);

INSERT OR IGNORE INTO prompt_templates (prompt_key, display_name, description, category, template, template_format, metadata)
VALUES (
    'memory.context_section',
    '上下文记忆片段',
    '将记忆条目格式化为 markdown 子章节',
    'memory',
    '## {{ section_title }}
{% for entry in entries -%}
- {{ entry.content }}
{% endfor %}',
    'jinja2',
    '{}'
);

INSERT OR IGNORE INTO prompt_templates (prompt_key, display_name, description, category, template, template_format, metadata)
VALUES (
    'rag.context_format',
    'RAG 上下文格式',
    '将 RAG 检索结果格式化为可注入模型的上下文文本',
    'rag',
    '{% for result in results %}{% if not loop.first %}

{% endif %}[{{ result.index }}] {{ result.title }}
{{ result.content }}{% endfor %}',
    'jinja2',
    '{}'
);

-- ============================================================
-- Schema 版本记录
-- ============================================================
COMMIT;

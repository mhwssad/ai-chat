# 第一批：底层对齐任务清单

## P2-SCHEMA-01 配置类实体建模

- 状态：done
- 目标：补齐 Providers、Models、App Settings、MCP Servers、Skills、Security Policies 实体。
- 涉及模块：
  - `docs/data.sql`
  - `src/ai/storage/config_models.py`
  - `src/ai/storage/config_repository.py`
  - `src/ai/storage/database.py`
  - `src/ai/storage/__init__.py`
- 已完成：
  1. 增加配置类 SQL schema。
  2. 增加 SQLModel ORM。
  3. 增加 repository 骨架。
  4. 纳入数据库初始化导入。
- 验收：
  1. `docs/data.sql` 可被 SQLite 正常读取。
  2. Python 编译检查通过。

## P2-SCHEMA-02 会话、记忆、RAG 与运行态对齐

- 状态：done
- 目标：补齐会话消息、记忆、RAG 元信息与运行态表的一致性边界。
- 涉及模块：
  - `docs/data.sql`
  - `src/ai/core/memory/history.py`
  - `src/ai/storage/runtime_models.py`
  - `src/ai/storage/runtime_repository.py`
- 执行步骤：
  1. 将会话和消息正式纳入 schema 基线。
  2. 保留现有 LangChain `SQLChatMessageHistory` 主路径，先不强行替换。
  3. 补齐 RAG 文档元信息表，用于承接全局/会话级知识索引边界。
  4. 增加对应 ORM 与 repository。
  5. 明确文件备份与 SQL 主存储的职责说明。
- 已完成：
  1. 增加 `chat_sessions`、`chat_message_store`、`rag_documents` schema。
  2. 增加 `ChatSession`、`ChatMessageStore`、`RagDocument` ORM。
  3. 增加对应 repository。
  4. `ChatHistoryManager` 轻量同步 `chat_sessions` 会话摘要。
- 验收标准：
  1. 会话/消息的正式持久化边界明确。
  2. RAG 文档元信息在 schema 中有正式承载。
  3. `docs/data.sql` 与需求文档方向一致。
  4. Python 编译检查和 SQLite schema 校验通过。

## P2-TOOL-01 工具元数据模型对齐

- 状态：done
- 目标：统一 Tool Registry 元数据字段。
- 涉及模块：
  - `src/ai/core/tools/types.py`
  - `src/ai/core/tools/registry.py`
  - `src/ai/core/tools/register.py`
  - `src/ai/service/tool_service.py`
  - `src/ai/api/schemas/tools.py`
  - `src/ai/api/routes/tools.py`
- 已完成：
  1. 新增 `ToolMeta` 与 `ToolDescriptor`。
  2. Registry 支持统一 descriptor 查询。
  3. API/TUI 共用的服务层输出新增 `display_name`、`output_description`。
- 验收：
  1. 编译检查通过。
  2. 工具元数据输出字段覆盖需求文档要求。

## P2-TOOL-02 权限策略结果标准化

- 状态：done
- 目标：建立 `allow / deny / ask` 权限决策主路径。
- 涉及模块：
  - `src/ai/core/tools/permissions.py`
  - `src/ai/core/tools/manager.py`
  - `src/ai/core/tools/builtins/*.py`
  - `src/ai/cli/widgets/confirm_dialog.py`
- 执行步骤：
  1. 引入权限决策结果对象。
  2. 将当前 `AUTO / CONFIRM / DENY` 映射到 `allow / ask / deny`。
  3. 在工具执行入口暴露决策结果。
  4. 为后续审计记录保留结构化字段。
- 已完成：
  1. 新增 `PermissionDecision` 结构化结果。
  2. 新增 `PermissionChecker.decide()`，保留 `check()` 兼容旧调用。
  3. `ToolManager` 和 `ToolService` 暴露权限检查入口。
  4. API 增加 `POST /tools/{name}/permission` 权限检查接口。
- 验收标准：
  1. 高风险工具可拒绝或要求确认。
  2. 聊天、Agent、手动工具测试走同一权限主路径。
  3. 权限结果可被后续审计记录消费。

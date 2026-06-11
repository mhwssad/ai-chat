# 研究发现

## 项目架构总结

### DI 容器层次
```
AppContainer
├── Layer 0: 配置 (bootstrap_settings, settings)
├── Layer 1: 基础设施 (thread_pool, model_container, chat_llm)
├── Layer 2: 子容器
│   ├── StorageContainer (DB引擎、会话工厂)
│   ├── PromptContainer (提示词服务)
│   ├── SkillContainer (技能服务)
│   ├── MCPContainer (MCP管理器)
│   ├── HTTPContainer (HTTP客户端)
│   ├── ToolContainer (工具注册表/管理器)
│   ├── MemoryContainer (记忆服务)
│   ├── RagContainer (RAG服务)
│   ├── SchedulerContainer (调度器服务)
│   └── ContextContainer (上下文服务)
├── Layer 3: AgentContainer (Agent编排器)
└── Layer 4: ServiceContainer (共享服务层)
    ├── chat_service ✅
    ├── image_service ✅
    ├── tts_service ✅
    ├── tool_service ✅
    └── system_service ✅
```

### 现有 Service 层能力
- **ChatService**: chat(), chat_stream(), chat_with_messages()
- **ImageService**: generate(), list(), delete()
- **TTSService**: synthesize(), list(), delete()
- **ToolService**: list_tools(), get_tool_detail(), execute_tool_diagnostic(), enable_tool(), disable_tool()
- **SystemService**: get_status_summary(), get_config_summary()

### Core 服务可直接调用的方法

#### RagService (core/rag/service.py)
- index_file(), index_url(), index_stream(), index_text(), index_directory()
- search(), hybrid_search(), build_context()
- delete_file(), delete_all(), list_documents(), get_stats()
- list_sessions(), delete_session()
- 全部有异步 a 前缀版本

#### PromptService (core/prompts/service.py)
- save_template(), get_template(), render()
- list_templates(), delete_template(), update_template()
- list_versions(), get_version(), rollback_template()
- list_templates_paginated()

#### MemoryService (core/memory/service.py)
- save(), get(), delete(), disable(), enable(), list_entries()
- search(), find_relevant_memories()
- extract_from_conversation(), save_extracted()
- get_context_for_prompt(), rebuild_index(), get_stats(), auto_maintenance()

#### SchedulerService (core/scheduler/service.py)
- create_cron_task(), create_interval_task(), create_one_shot_task()
- get_task(), get_task_by_name(), delete_task(), list_tasks()
- enable_task(), disable_task(), pause_task(), resume_task()
- update_task_after_execution(), get_task_logs(), get_stats()
- start(), stop(), is_running

#### AgentOrchestrator (core/agent/orchestrator.py)
- run() -> AgentResult
- cancel() -> bool
- resume() -> AgentResult

#### MCPManager (core/mcp/manager.py)
- discover_tools(), call_tool()
- list_resources(), read_resource()
- health_check(), sync_tools()

### 存储层 Repository
- ProviderConfigRepository, ModelConfigRepository (配置模型)
- ChatSessionRepository, ChatMessageStoreRepository (运行时)
- PromptTemplateRepository, PromptVersionRepository (提示词)
- ScheduledTaskRepository, TaskExecutionLogRepository (调度)
- MemoryEntryRepository, RagDocumentRepository (记忆/RAG)
- AuditLogRepository (审计)

### 异常体系
所有异常继承 BaseExceptions，按域分包：llm, tool, mcp, media, prompt, memory, rag, scheduler, skill, loader, pool, http

## 路由设计要点

### RESTful 规范
- GET 列表/详情、POST 创建/执行、PUT 更新、DELETE 删除
- 路径参数用于单个资源定位
- 查询参数用于过滤/分页

### 统一响应格式
- 列表接口支持分页 (page, page_size, total)
- 错误统一通过 HTTPException 返回
- 异常映射：领域异常 -> HTTP 状态码

### Schema 命名规范
- XxxRequest / XxxResponse / XxxInfo / XxxDetail
- Pydantic BaseModel + Field 描述

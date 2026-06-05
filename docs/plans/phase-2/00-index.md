# 第二期任务执行索引

本目录将 `docs/plans/2026-06-05-phase-2-execution-checklist.md` 拆分为多个可执行任务清单文件。

## 执行顺序

1. `01-foundation-alignment.md`
2. `02-governance-integration.md`
3. `03-runtime-enhancement.md`
4. `04-tui-workbench.md`

## 当前状态

| 任务 | 状态 | 说明 |
| --- | --- | --- |
| P2-SCHEMA-01 | done | 已补齐配置类 schema、ORM、repository 骨架 |
| P2-SCHEMA-02 | done | 已补齐会话摘要、LangChain 消息表和 RAG 文档元信息承载面 |
| P2-TOOL-01 | done | 已统一 Tool Registry 元数据结构 |
| P2-TOOL-02 | done | 已新增结构化权限决策结果与 API 检查入口 |
| P2-TOOL-03 | done | 已新增工具执行诊断、API 诊断响应和审计写入 |
| P2-MCP-01 | done | 已接入 DB 优先的 MCP 配置读取、JSON 回退和明确健康状态 |
| P2-MCP-02 | done | 已把 MCP 工具发现同步到统一 Tool Registry，并标记来源 |
| P2-SKILL-01 | done | 已补齐 Skills 发现同步、启停状态和 API 管理入口 |
| P2-AUDIT-01 | done | 已新增统一审计入口，并接入工具、MCP 与 Skills 关键动作 |
| P2-AGENT-01 | done | 已标准化 Agent 状态语义，区分失败、超时、取消与等待确认 |
| P2-AGENT-02 | done | 已新增 Agent 执行轨迹摘要，并接入 API 与 TUI 详情展示 |
| P2-AGENT-03 | done | 已打通 Agent 取消入口、工具权限确认回调和等待确认状态 |
| P2-MEM-01 | done | 已补齐记忆作用域、来源、状态控制面，并接入 API/TUI 展示 |
| P2-RAG-01 | done | 已补齐 RAG 文档作用域、状态控制面、API/TUI 展示和删除状态同步 |
| P2-CONTEXT-01 | done | 已新增上下文来源摘要，并接入 Chat/Agent API 与 TUI 检视区 |
| P2-TUI-01 | done | 已新增 TabSummary，状态栏和工作区头部统一读取 tab 摘要 |
| P2-TUI-02 | done | 已增强 SystemService 运行状态聚合，并接入系统/统计面板 |
| P2-TUI-03 | done | 已接入会话历史摘要和上下文来源检视区 |

## 状态约定

- `pending`：尚未开始。
- `in_progress`：正在执行。
- `done`：已实现并通过最小验证。
- `blocked`：需要用户决策或外部条件。

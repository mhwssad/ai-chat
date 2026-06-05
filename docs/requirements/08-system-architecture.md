# 系统架构与边界需求

## 1. 目标

系统应通过清晰的层次结构、共享服务边界和统一 Dependency Injection 组织能力，支撑 Web、TUI 和 API 的长期演进。

## 2. 架构目标

架构应满足以下目标：

1. 共享核心能力复用。
2. 交互入口与业务逻辑分离。
3. 模块边界清晰。
4. 测试替换能力明确。
5. 新能力可在不复制核心逻辑的前提下扩展。

## 3. 系统层次划分

系统应至少划分为以下层次：

1. Interaction Layer：Web、TUI、API。
2. Shared Service Layer：聊天、工具、媒体、系统聚合服务。
3. Core Capability Layer：模型、上下文、工具、记忆、RAG、Agent、调度、技能、MCP。
4. Storage Layer：数据库、持久化和 repository。
5. Infrastructure Layer：线程池、HTTP 客户端、配置和运行时辅助设施。

## 4. 交互层边界

交互层职责应限于：

1. 接收输入。
2. 转换参数。
3. 展示状态与结果。
4. 处理用户交互事件。

交互层不应直接实现模型调用、上下文组装、工具执行或数据持久化规则。

## 5. 共享服务层边界

共享服务层应作为交互层与 Core Capability Layer 之间的稳定门面。

当前项目中，该层允许以以下对象作为代表性边界：

1. `ChatService`
2. `ToolService`
3. `ImageService`
4. `TTSService`
5. `SystemService`

后续新增服务也应遵循同样的组织方式。

## 6. Core 能力层边界

Core 能力层应承载：

1. 模型能力。
2. 上下文构建。
3. Tool Registry 与 Tool Manager。
4. Memory Service。
5. RAG Service。
6. Agent Orchestrator。
7. Scheduler。
8. Skills 与 MCP 管理。

这些模块应尽量通过构造器声明依赖，而不是隐式拿全局对象。

## 7. 存储层边界

存储层应负责：

1. SQLite schema 与 session 管理。
2. repository 和 store 实现。
3. 数据持久化细节。

存储层不应承担交互逻辑，也不应直接决定 UI 结构。

## 8. DI 与组合根

系统应以应用级容器作为唯一组合根。

当前项目中，需求基线允许将以下结构视为架构事实方向：

1. `AppContainer` 作为主组合根。
2. `ServiceContainer` 作为共享服务层子容器。
3. `CLIContainer` 作为 TUI 子系统容器。

系统应继续通过 DI 构建共享服务、TUI 面板、Agent 依赖和其他跨模块对象。

## 9. 异步与线程池约束

系统应尽量采用异步接口组织模型调用、上下文构建、API 请求和 Agent 执行流程。

对于阻塞型任务，系统应通过统一线程池或等价运行时设施处理，而不是在任意入口层随意创建独立执行环境。

## 10. 模块间依赖规则

模块间依赖应遵循以下规则：

1. Interaction Layer 依赖 Shared Service Layer。
2. Shared Service Layer 依赖 Core Capability Layer。
3. Core Capability Layer 可依赖 Storage Layer 与 Infrastructure Layer。
4. UI 组件不应直接依赖数据库实现细节。
5. Agent Runtime 不应复制聊天、工具或上下文逻辑。

## 11. 约束与风险

1. 如果入口层直接依赖容器全局对象，测试和替换成本会持续升高。
2. 如果服务层边界不稳定，Web、TUI 和 API 会重新分叉。
3. 如果 Agent、RAG、记忆和工具之间缺少统一架构层次，后续演进会失去控制。

## 12. 验收标准

1. 交互层、共享服务层、核心能力层和存储层边界清晰。
2. 共享服务能够被多个入口复用。
3. TUI 子系统由独立 DI 子容器统一装配。
4. 新能力扩展不需要复制聊天或工具核心流程。

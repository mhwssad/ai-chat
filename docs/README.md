# AI Chat 文档索引

本目录用于维护项目级文档，覆盖需求、计划、架构、依赖和开发规范。后续实现应优先从需求文档和实施计划出发，避免功能分散演进。

## 1. 需求文档

- [AI Workbench 总需求](./requirements/ai-workbench-requirements.md)
- [MVP 范围](./requirements/01-mvp-scope.md)
- [聊天与模型](./requirements/02-chat-and-models.md)
- [工具、MCP 与 Skills](./requirements/03-tools-mcp-skills.md)
- [记忆](./requirements/04-memory.md)
- [Web 与 CLI](./requirements/05-web-and-cli.md)
- [存储、配置与审计](./requirements/06-storage-config-and-audit.md)
- [Agent Runtime 路线](./requirements/07-agent-runtime-roadmap.md)

## 2. 实施计划

- [MVP 实施计划](./plans/01-mvp-implementation-plan.md)

## 3. 架构与规范

- [项目结构规范](./project-structure-standards.md)
- [代码规范](./coding-standards.md)
- [依赖策略与审计](./dependencies.md)

## 4. 临时记录

临时记录只用于捕捉想法和待办，可以保留为本地笔记。进入实现前，应将稳定内容沉淀到需求、计划或规范文档中。

## 5. 建议使用方式

1. 新增功能前，先阅读总需求和对应模块需求。
2. 开始实现前，阅读 MVP 实施计划，确认当前阶段和验收标准。
3. 新增模块前，阅读项目结构规范，确认代码应该落在哪一层。
4. 调整依赖前，更新依赖策略与审计文档。
5. 提交前，自查是否遵守“单一职责、分层清晰、扩展点注册化”这三条核心约束。

## Brief overview

ai-chat 项目 — 基于 LangChain/LangGraph 生态的多提供商 AI 聊天框架。使用 Python 3.13+，uv 管理依赖。规则适用于日常开发协作。

## 项目架构

- 使用**注册 + 工厂 + 策略**三层扩展模式
- 所有扩展点遵循统一流程：定义 ABC 接口 → 实现具体 Provider → 装饰器自动注册 → 工厂按名路由
- 导入模块时装饰器自动将类注册到全局工厂，无需手动维护注册表

## 扩展点命名规范

- LLM Provider: `@register_chat(name, config_fn)` / `@register_embedding(name, config_fn)` → 放在 `llm/providers/chat/` 或 `llm/providers/embedding/`
- 工具: `@registered_tool(tool_type=ToolType.SYSTEM)` → 放在 `tools/`
- 记忆后端: `@register_memory(name)` → 放在 `memory/providers/`
- 技能: `skills/skills/<name>/SKILL.md`

## 代码风格

- 注释和文档字符串使用**中文**
- 类名/函数名/文件名使用**英文**
- 所有新增函数必须补充参数和返回值**类型标注**
- 使用现代类型语法：`list[str]`、`X | None`（Python 3.13）
- 公共类和函数必须有**中文 docstring**
- 抛出项目领域异常（如 `ModelNotSupportedException`），**不抛裸 Exception**
- 配置统一通过 `config/settings.py` 管理，**禁止散落 os.getenv() 调用**

## 异步设计

- 异步优先设计，同步包装注意事件循环处理（参考 `UnifiedAgent.invoke`）
- 异步方法需要补充重试和超时机制

## 配置管理

- 使用 pydantic `BaseSettings` 自动加载配置
- 支持 `settings.refresh()` 热重载
- 支持 `settings.save_to_env_file()` 回写

## 测试

- 使用 pytest 运行测试：`python -m pytest tests/`
- 运行单个测试文件：`python -m pytest tests/tools/test_registry.py`

## 代码检查

- ruff check src/ → 代码检查
- ruff format src/ → 代码格式化
- mypy src/ → 类型检查

## Git 提交规范

- 每次提交应保持原子性：一个提交只做一件事（新增功能、修复 bug、重构等）
- 提交信息格式：`类型: 简短描述`，如 `feat: 添加 Qwen 模型支持`
- 常用类型：`feat`/`fix`/`refactor`/`docs`/`test`/`chore`
- 避免提交未完成的工作，使用 wip（Work In Progress）分支或草稿提交

## 编码优先级

1. 类型安全 > 动态灵活
2. 显式优于隐式
3. 组合优于继承（优先使用组合模式）
4. 错误应尽早暴露（fail fast）
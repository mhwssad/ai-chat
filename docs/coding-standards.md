# AI Chat 代码规范

本文档约束 `ai-chat` 项目的 Python 编码风格、实现方式和扩展约定。目标不是追求“通用模板”，而是让当前项目在继续扩展 `LLM / Graph / RAG / Memory / Tool / Skill / MCP` 能力时保持一致性。

## 1. 基本原则

### 1.1 单一职责

- 一个模块只负责一个明确领域能力。
- 一个类只负责一个核心对象行为。
- 一个函数尽量只做一件事，输入输出明确，可单独测试。

示例：

- `llm/factory.py` 负责 Provider 注册与路由，不承担具体供应商实现。
- `skills/loader.py` 只负责技能文件解析，不承担运行技能。
- `graphs/unified_agent.py` 负责图编排，不负责底层 Provider 注册。

### 1.2 优先扩展，避免分支堆叠

项目当前已经形成较明显的“注册 + 工厂 + 策略”模式，新增能力优先沿用该模式。

- 新增模型供应商：放在 `llm/providers/`，通过装饰器注册。
- 新增工具：放在 `tools/`，通过注册器接入。
- 新增 Memory / RAG / Splitter / Loader：通过对应工厂注册。
- 不要把新能力直接塞进 `if/elif` 长分支中，除非这是入口菜单类代码。

### 1.3 面向维护者编程

- 代码应当让后来者在不阅读太多上下文时也能定位职责。
- 复杂流程拆成小函数或私有方法，不把所有逻辑堆在单个入口函数中。
- 优先清晰，次优极致简洁。

## 2. 语言与格式

### 2.1 Python 版本

- 统一按 `pyproject.toml` 中的 `Python >= 3.13` 编写。
- 可以使用现代类型语法，如 `list[str]`、`dict[str, int]`、`X | None`。

### 2.2 字符与编码

- 源码文件统一使用 `UTF-8`。
- 项目现有注释、文档字符串、提示词大多为中文，后续保持中文为主。
- 对外暴露的类名、函数名、文件名继续使用英文，注释和说明使用中文。

### 2.3 导入规范

- 标准库、第三方、本地模块分组导入。
- 避免 `from x import *`。
- 尽量使用绝对导入，如 `from src.ai_chat.llm import llm_factory`。
- 仅在避免循环依赖或类型检查时使用 `TYPE_CHECKING`。

## 3. 命名规范

### 3.1 文件与模块

- 文件名使用小写下划线：`unified_agent.py`、`logging_setup.py`。
- 模块名应体现职责，不使用过度抽象名称如 `utils.py`、`common2.py`。
- 如果确实需要公共能力，放在有明确边界的领域模块内，例如 `tools/common.py`。

### 3.2 类命名

- 类名使用 `PascalCase`。
- 抽象角色优先使用语义后缀：
  - `Factory`
  - `Registry`
  - `Provider`
  - `Config`
  - `Exception`
- 面向图或编排的类，优先体现用途：`ChatGraph`、`UnifiedAgent`。

### 3.3 函数与变量

- 函数、方法、变量使用 `snake_case`。
- 布尔字段使用可读前缀：`is_`、`has_`、`enable_`、`can_`。
- 私有属性和私有方法使用单下划线前缀，如 `_build_graph()`、`_rag_store`。

### 3.4 常量

- 模块级常量使用全大写下划线，如 `_CLASSIFY_PROMPT`、`_RAG_SYSTEM`。
- 仅对稳定不变的值使用常量；业务流程中临时拼接字符串不必强行提取。

## 4. 类型标注规范

### 4.1 全量类型标注

- 新增函数、方法必须补充参数和返回值类型。
- 公共 API 必须完整标注。
- 内部复杂变量也建议标注，特别是：
  - 状态对象
  - 工厂注册表
  - 回调函数
  - 异步迭代器

### 4.2 数据模型选择

按项目现状统一使用以下分工：

- 配置对象：`pydantic BaseSettings` 子类
- 简单领域数据：`dataclass`
- 图状态：`TypedDict`
- 协议性抽象行为：`ABC + abstractmethod`

示例：

- `UnifiedState` 使用 `TypedDict`
- `ProviderConfig`、`ChatRequest` 使用 `dataclass`
- `ChatProvider` 使用抽象基类

## 5. 文档字符串与注释

### 5.1 文档字符串

- 公共类、公共函数、公共模块必须有 docstring。
- 保持与现有代码一致，优先使用中文说明。
- 首行先写一句职责概述，再补充必要细节。

推荐格式：

```python
def create(self, name: str) -> BaseTool:
    """按名称创建工具实例。"""
```

### 5.2 注释原则

- 注释解释“为什么”，少解释“这行代码做了什么”。
- 复杂节点流程、兼容逻辑、边界处理可以加少量注释。
- 不要用注释掩盖命名不清的问题，优先重命名。

## 6. 分层实现规范

### 6.1 Graph 层

`graphs/` 负责对话流程编排：

- 定义 `StateGraph` 状态结构
- 组织节点和路由
- 调用下层 `llm / rag / memory / tools`

不要在 Graph 层做这些事：

- 直接写供应商 API 细节
- 直接解析 `.env`
- 直接实现向量库底层操作

### 6.2 Factory / Registry 层

工厂与注册器是本项目的核心扩展机制。

- `Factory` 负责创建和路由。
- `Registry` 负责登记和查询。
- 注册表内部状态应封装，不允许外部直接改内部字典。
- 新增注册能力时，优先提供：
  - `register(...)`
  - `get(...)` 或 `create(...)`
  - `list_*()` 或 `get_all()`

### 6.3 Provider 层

`llm/providers/`、`memory/providers/` 等提供具体实现。

- 每个 Provider 文件只放一个主要实现类。
- Provider 应遵守抽象接口，不在外部依赖其内部细节。
- Provider 的初始化配置尽量通过 `Config` 对象传入，不散落环境变量读取逻辑。

### 6.4 Config 层

- 所有配置统一从 `config/` 管理。
- 环境变量读取优先通过 `BaseSettingsConfig` 子类处理。
- 业务模块不要随意重复读取 `.env` 或 `os.getenv()`。

## 7. 异常处理规范

### 7.1 抛出有语义的异常

- 优先抛出项目内的领域异常，而不是裸 `Exception`。
- 找不到注册项时，优先给出“请求值 + 可选值列表”。
- 错误信息必须足够定位问题。

推荐：

```python
raise ModelNotSupportedException(model_name, list(self._chat_routing))
```

避免：

```python
raise Exception("error")
```

### 7.2 不要吞异常

- 除非有明确降级策略，否则不要 `except Exception: pass`。
- 如果要兜底，至少记录原因或返回可解释结果。
- 文件加载这类容错场景，可以像 `skills/loader.py` 一样返回 `None`，但要保证调用方能识别。

## 8. 异步与同步规范

### 8.1 优先保留 async 主路径

项目已经同时存在同步和异步接口：

- `ainvoke()` / `astream()`
- `invoke()` / `stream()`

新增涉及 I/O 的能力时：

- 优先先设计异步接口
- 如确有需要，再提供同步包装
- 同步包装必须明确处理事件循环场景，避免直接在运行中的 loop 内错误调用

### 8.2 流式输出

- 流式接口返回 `Iterator[str]` 或 `AsyncIterator[str]`
- 如果要做历史保存，注意避免重复保存分块内容，应在收集完成后统一落库

## 9. 可扩展性约定

### 9.1 新增模型供应商

新增聊天模型或嵌入模型时：

1. 在 `llm/providers/` 新建文件。
2. 实现 `ChatProvider` 或 `EmbeddingProvider`。
3. 提供 `SUPPORTED_MODELS`。
4. 通过 `register_chat` 或 `register_embedding` 自动注册。

### 9.2 新增工具

- 工具放入 `src/ai_chat/tools/`
- 优先通过 `registered_tool` 注册
- 新增工具默认使用 `ToolType.CUSTOM`
- 只有基础内置工具才应标记为 `ToolType.SYSTEM`
- 工具函数名、工具名、描述必须清晰表达用途
- 工具本体只负责工具行为，不做复杂菜单交互
- `CUSTOM` 工具不应依赖包导入时全量扫描，而应支持按名称懒加载
- `SYSTEM` 工具若涉及文件、目录或命令执行，应优先限制在项目根目录范围内
- 命令执行类工具必须默认只读，并显式限制允许的命令前缀与语法

### 9.3 新增技能

- 每个技能一个目录：`skills/skills/<skill_name>/SKILL.md`
- 技能元信息与提示正文分离，遵守已有 frontmatter 解析格式
- 技能名应稳定，不随描述变化频繁修改

## 10. 测试与校验规范

### 10.1 测试目录

- 测试统一放在 `tests/`
- 测试结构尽量映射 `src/ai_chat/` 的模块结构

推荐示例：

- `tests/llm/test_factory.py`
- `tests/skills/test_loader.py`
- `tests/graphs/test_unified_agent.py`

### 10.2 最低测试要求

新增代码至少覆盖以下一种：

- 正常路径
- 一个关键边界条件
- 一个失败路径

工厂、注册器、解析器这类模块尤其需要测试：

- 重复注册
- 未注册查询
- 配置解析失败
- 默认值回退

## 11. 提交前自查清单

提交前至少检查：

1. 代码是否放在正确层级，而不是图方便塞进现有文件。
2. 是否补齐类型标注和 docstring。
3. 是否复用现有工厂/注册器，而不是绕开扩展机制。
4. 是否出现过长函数、重复逻辑、无语义异常。
5. 是否需要同步补测试和文档。

## 12. 当前项目特别约定

结合当前仓库现状，后续开发额外遵守以下约定：

- CLI 菜单类代码可以保留少量 `if/elif`，但业务能力不应继续向菜单堆积。
- `src.ai_chat` 下每个一级包都应保持领域清晰，不跨层写入无关逻辑。
- `README.md` 适合放使用说明；面向开发协作的规则统一放在 `docs/`。
- 若发现通用能力只被单个模块使用，先保持局部私有，不急于抽成“公共工具模块”。

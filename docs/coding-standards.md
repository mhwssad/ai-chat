# 代码规范

本文档定义 `ai-chat` 项目的编码规范。所有新代码必须遵守。

---

## 1. 语言与命名

### 1.1 语言选择

| 场景 | 语言 |
| --- | --- |
| 类名、函数名、变量名、文件名 | 英文 |
| 注释、docstring、commit message | 中文 |
| 字符串常量（面向用户的提示、错误信息） | 中文 |

### 1.2 命名约定

```python
# 类名：PascalCase
class ModelProviderRegistry: ...

# 函数/方法：snake_case
def get_chat_llm(): ...

# 常量：UPPER_SNAKE_CASE
COMPRESS_BASE_PROMPT = "..."

# 私有成员：单下划线前缀
self._registry = registry

# 模块级私有变量：单下划线前缀
_engine: Engine | None = None

# 文件名：snake_case
# 正确：model_registry.py, chat_service.py
# 错误：ModelRegistry.py, chatService.py
```

---

## 2. 类型标注

### 2.1 必须标注

所有新增**公共函数和方法**必须有参数和返回值类型标注：

```python
# ✅ 正确
def get_history(self, session_id: str) -> BaseChatMessageHistory:
    ...

# ❌ 错误 — 缺少返回值标注
def get_history(self, session_id: str):
    ...
```

### 2.2 现代类型语法

使用 Python 3.13 的现代类型语法，禁止旧式写法：

```python
# ✅ 正确
def search(query: str, *, limit: int = 5) -> list[MemorySearchResult]: ...
def get(name: str) -> MemoryEntry | None: ...

# ❌ 错误
from typing import List, Optional, Union
def search(query: str, *, limit: int = 5) -> List[MemorySearchResult]: ...
def get(name: str) -> Optional[MemoryEntry]: ...
```

### 2.3 延迟类型求值

当类型引用会导致循环导入时，使用 `from __future__ import annotations` + `TYPE_CHECKING`：

```python
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel
    from src.ai.core.memory.history_store import FileHistoryStore


class MyService:
    def __init__(self, llm: BaseChatModel, store: FileHistoryStore) -> None:
        ...
```

---

## 3. 依赖注入（DI）

### 3.1 核心原则

**禁止在类内部直接创建依赖。** 所有依赖必须通过构造器注入。

```python
# ✅ 正确 — 依赖通过构造器注入
class SkillService:
    def __init__(self, *, loader: SkillLoader, renderer: SkillRenderer) -> None:
        self._loader = loader
        self._renderer = renderer

# ❌ 错误 — 在构造器内部创建依赖
class SkillService:
    def __init__(self, *, loader: SkillLoader | None = None) -> None:
        self._loader = loader or SkillLoader()      # 回退创建
        self._renderer = SkillRenderer()             # 直接创建
```

### 3.2 禁止访问全局容器

类的方法内部**禁止** `from src.ai.core.container import container`：

```python
# ❌ 错误 — 方法内访问全局容器
def _calculate_budget(self, request) -> int | None:
    from src.ai.core.container import container
    app_settings = container.settings()
    ...

# ✅ 正确 — 通过构造器注入 settings
class ContextAssembler:
    def __init__(self, settings: object) -> None:
        self._settings = settings

    def _calculate_budget(self, request) -> int | None:
        context_window = self._settings.llm.max_input_tokens
        ...
```

### 3.3 禁止访问模块级单例

类的方法内部**禁止** `from src.ai.core.xxx import yyy_service`：

```python
# ❌ 错误
def _load_from_db(self) -> str | None:
    from src.ai.core.prompts import prompt_service
    result = prompt_service.render(...)

# ✅ 正确
class UserCollector:
    def __init__(self, prompt_service: object) -> None:
        self._prompt_service = prompt_service

    def _load_from_db(self) -> str | None:
        result = self._prompt_service.render(...)
```

### 3.4 工厂函数职责

DI 容器中的工厂函数负责**组装和回退逻辑**：

```python
def _create_prompt_service(store):
    """提示词模板服务。"""
    from src.ai.core.prompts.renderer import PromptRenderer
    from src.ai.core.prompts.service import PromptService
    # 工厂函数负责创建依赖并注入
    return PromptService(renderer=PromptRenderer(), store=store)
```

### 3.5 Builtin 工具注入

`@tool` 装饰器的函数签名是 LLM 的 JSON Schema，不能加业务参数。使用**工厂函数 + 闭包**注入依赖：

```python
def create_skill_tool(skill_service):
    """工厂函数：创建绑定了 SkillService 的 skill 工具。"""

    @tool
    async def skill(name: str, arguments: str = "") -> str:
        """执行指定技能。"""
        try:
            return skill_service.activate(name, arguments=arguments)
        except Exception as exc:
            return f"技能执行失败: {exc}"

    return skill


def register(skill_service):
    """注册 skill 工具。"""
    skill_tool = create_skill_tool(skill_service)
    register_tool(skill_tool, source_type="builtin", essential=True)
```

---

## 4. Docstring

### 4.1 公共类和函数

必须有中文 docstring：

```python
class MemoryService:
    """统一记忆服务。

    文件系统为长期记忆存储（MEMORY.md 索引 + 详情文件），
    对话历史和上下文构建通过 LangChain 策略管理。
    """

    def save(self, request: MemoryWriteRequest) -> MemoryEntry:
        """保存记忆到文件系统。

        Args:
            request: 记忆写入请求。

        Returns:
            保存后的记忆条目。
        """
```

### 4.2 Args / Returns / Raises

使用 Google 风格，Args/Returns/Raises 用中文：

```python
def render(self, request: PromptRenderRequest) -> PromptRenderResult:
    """渲染提示词模板。

    Args:
        request: 渲染请求，包含 prompt_key 和变量。

    Returns:
        渲染结果。

    Raises:
        PromptNotFoundError: 提示词模板不存在。
    """
```

### 4.3 模块级 docstring

每个模块文件顶部必须有中文 docstring：

```python
"""上下文组装器 — token 预算分配和裁剪。"""
```

---

## 5. 导入规范

### 5.1 导入顺序

```python
# 1. 标准库
import hashlib
import logging
from pathlib import Path

# 2. 第三方库
from langchain_core.tools import BaseTool
from sqlalchemy import Engine

# 3. 项目内部
from src.ai.config.base_config import project_root
from src.ai.core.rag.types import RAGSearchConfig

# 4. 相对导入（同包内）
from .base import BaseMemoryStrategy
from .types import MemoryEntry
```

### 5.2 延迟导入

避免 import 时副作用（如 langchain_core 冷启动），在工厂函数内部使用延迟导入：

```python
def _create_prompt_service(store):
    """提示词模板服务。"""
    # 延迟导入，避免 import 时触发 langchain 冷启动
    from src.ai.core.prompts.renderer import PromptRenderer
    from src.ai.core.prompts.service import PromptService
    return PromptService(renderer=PromptRenderer(), store=store)
```

### 5.3 禁止顶层导入重型依赖

重型依赖（如 `magika`、`rapidocr`、`langchain_*`）必须延迟导入：

```python
# ❌ 错误 — 顶层导入重型依赖
from magika import Magika

class FileRecognizer:
    def __init__(self):
        self._magika = Magika()

# ✅ 正确 — 延迟导入
class FileRecognizer:
    def __init__(self):
        from magika import Magika
        self._magika = Magika()
```

---

## 6. 异常处理

### 6.1 使用项目领域异常

禁止抛出裸 `Exception`，必须继承 `BaseExceptions`：

```python
from src.ai.exception.model_exception import ModelNotSupportedException

# ✅ 正确
raise ModelNotSupportedException(
    "不支持的模型",
    context={"model": model_name, "provider": provider_key},
)

# ❌ 错误
raise Exception("不支持的模型")
```

### 6.2 异常上下文

使用 `context` 参数传递结构化调试信息：

```python
raise MCPConfigError(
    "MCP server 不存在",
    context={"server": server_key},
)
```

### 6.3 日志与异常

```python
# 捕获后记录日志，不吞掉异常
try:
    result = await some_operation()
except Exception:
    logger.warning("操作失败，使用回退方案", exc_info=True)
    return fallback_value
```

---

## 7. 异步优先

### 7.1 异步方法命名

异步方法以 `a` 前缀命名：

```python
class CompressionStrategy:
    def build_context_messages(self, session_id, system_prompt) -> list[BaseMessage]:
        """同步构建上下文。"""
        ...

    async def abuild_context_messages(self, session_id, system_prompt) -> list[BaseMessage]:
        """异步构建上下文。"""
        ...
```

### 7.2 异步优先设计

优先实现异步版本，同步版本作为兼容包装：

```python
def build(self, request: ContextBuildRequest) -> ContextBuildResult:
    """同步构建上下文。"""
    import asyncio
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        return self._build_sync(request)

    return asyncio.run(self.abuild(request))
```

---

## 8. 配置管理

### 8.1 禁止直接 os.getenv

业务代码禁止 `os.getenv()`，配置统一通过 `config/settings.py`：

```python
# ❌ 错误
api_key = os.getenv("OPENAI_API_KEY")

# ✅ 正确 — 通过 Settings 访问
from src.ai.config.settings import settings
api_key = settings.llm.api_key
```

### 8.2 配置分域

配置按域划分，通过 pydantic `BaseSettings` 管理：

| 域 | 类 | 用途 |
| --- | --- | --- |
| LLM | `LLMSettings` | 模型名、超时、上下文管理 |
| Memory | `MemorySettings` | 记忆后端、摘要设置 |
| MCP | `MCPSettings` | MCP 客户端/服务端配置 |

---

## 9. 数据库

### 9.1 Repository Pattern

所有数据库访问通过 Repository 类，禁止直接操作 Session：

```python
# ✅ 正确
class ProviderRepository:
    def get_by_key(self, provider_key: str) -> Provider | None:
        with get_session() as session:
            return session.exec(...).first()

# ❌ 错误 — 路由中直接操作 Session
@router.get("/providers")
def list_providers():
    with get_session() as session:
        return session.exec(select(Provider)).all()
```

### 9.2 API Key 加密

API Key 必须加密保存（Fernet），禁止明文入库。

### 9.3 Schema 同步

ORM/schema 变化必须同步更新 `docs/data.sql`。

---

## 10. 分层约束

### 10.1 调用链

```text
API Route → Service → Core (Models/Tools/Memory) → Storage
```

- 路由只做参数校验和调用 service
- 禁止路由直接写业务逻辑
- 禁止绕过 `core/models` 调用模型
- 禁止绕过 `core/tools` 调用工具

### 10.2 新增功能落位

| 新增内容 | 放置位置 |
| --- | --- |
| FastAPI 路由 | `src/ai/api/routes/<name>.py` |
| API schema | `src/ai/api/schemas/<name>.py` |
| API service | `src/ai/api/services/<name>_service.py` |
| 模型 provider | `src/ai/core/models/providers/<name>.py` |
| 工具 | `src/ai/core/tools/builtins.py` 添加 `ToolDefinition` |
| ORM / Repository | `src/ai/storage/<name>_models.py` + `<name>_repository.py` |

---

## 11. 验证要求

每次代码修改后，根据影响面运行最小验证：

```bash
# Python 编译
uv run python -m compileall -q src/ai main.py

# 代码检查
ruff check src/
ruff format src/

# 类型检查
mypy src/

# 数据库 schema
sqlite3 :memory: ".read docs/data.sql" "PRAGMA foreign_key_check;"
```

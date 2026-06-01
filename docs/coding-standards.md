# 编码规范

本项目遵循以下编码规范，所有代码贡献必须符合这些要求。

## 语言规范

- **注释和文档字符串**：使用中文
- **类名、函数名、文件名**：使用英文
- **变量名**：使用英文，遵循 snake_case 命名法

## 类型标注

- 所有新增函数必须补充参数和返回值类型标注
- 使用 Python 3.13 现代类型语法：
  - `list[str]` 而非 `List[str]`
  - `dict[str, Any]` 而非 `Dict[str, Any]`
  - `X | None` 而非 `Optional[X]`
  - `X | Y` 而非 `Union[X, Y]`
- 从 `typing` 模块导入时，仅导入 `Any`、`TypeVar`、`Generic`、`TYPE_CHECKING` 等仍需导入的类型

```python
# 正确
def process(data: str, limit: int | None = None) -> dict[str, Any]:
    ...

# 错误
from typing import Optional, Dict
def process(data: str, limit: Optional[int] = None) -> Dict[str, Any]:
    ...
```

## 文档字符串

- 公共类和函数必须有中文 docstring
- 推荐使用 Google 风格的 docstring 格式：

```python
def search(query: str, top_k: int = 5) -> list[Result]:
    """搜索记忆条目。

    Args:
        query: 搜索关键词
        top_k: 返回的最大结果数

    Returns:
        按相关度排序的结果列表

    Raises:
        MemoryException: 搜索服务不可用时
    """
    ...
```

## 异常处理

- 抛出项目领域异常（如 `ModelNotSupportedException`、`ToolExecutionException`）
- 禁止抛出裸 `Exception`
- 所有自定义异常必须继承 `BaseExceptions`（位于 `src/ai/exception/base_exception.py`）
- 异常消息使用中文

```python
# 正确
from src.ai.exception.llm_exception import ModelNotSupportedException

raise ModelNotSupportedException(f"不支持的模型: {model_key}")

# 错误
raise Exception(f"Unsupported model: {model_key}")
```

## 配置管理

- 禁止业务代码直接 `os.getenv()`
- 配置统一通过 `src/ai/config/settings.py` 管理
- 使用 pydantic `BaseSettings` 自动加载环境变量

## 异步设计

- 异步优先设计
- 同步包装注意事件循环处理
- 数据库操作使用 async session

## 分层约束

- API 路由只做参数校验和调用 service，禁止直接写业务逻辑
- 禁止绕过 `core/models` 调用模型
- 禁止绕过 `core/tools` 调用工具
- 禁止 RAG 自建模型 provider
- ORM/schema 变化必须同步 `docs/data.sql`
- API Key 必须加密保存（Fernet），禁止明文入库

## 代码格式

- 使用 `ruff` 进行代码检查和格式化
- 行宽限制：88 字符（ruff 默认）
- 使用 `ruff check src/` 检查，`ruff format src/` 格式化

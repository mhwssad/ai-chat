# Context / Memory 模块重构方案

## 1. 问题描述

当前 `context` 和 `memory` 两个模块存在职责边界模糊和代码重复，主要体现在三个方面。

### 1.1 压缩逻辑重复

`CompressionStrategy._aincremental_compress()`（memory 模块）和 `FullCompact.compact()`（context 模块）包含几乎相同的逻辑：

- 将消息格式化为 `[消息#N] type: content`
- 构建增量合并提示词（已有摘要 + 新增内容 + 要求）
- 调用 LLM 链生成摘要
- 生成 file_references

差异仅在于使用的提示词模板不同（`memory.compress_incremental_format` vs `memory.full_compress_format`）。

### 1.2 工具函数重复

`context/compact.py` 和 `memory/strategies/compression.py` 各自定义了一份相同的 `_get_template_content()` 函数。

### 1.3 反向依赖

`context/compact.py` 从 `memory/llm_utils.py` 导入 `build_llm_chain`，形成 context → memory 的反向依赖。正确的依赖方向应为 memory → context（memory 模块使用 context 模块提供的压缩能力）。

## 2. 目标

1. **消除压缩逻辑重复** — 增量压缩和全量压缩统一由 `FullCompact` 管理
2. **消除工具函数重复** — `_get_template_content` 收口到一处
3. **修正依赖方向** — `llm_utils` 从 memory 迁移到 utils，消除反向依赖
4. **明确职责边界** — context 负责压缩算法，memory 负责调度和持久化

## 3. 模块职责定义

### Context 模块 — "本轮提示词怎么组装"

- 收集上下文段（系统环境、用户提示、记忆、工具、RAG）
- token 预算分配和裁剪
- 系统提示拼装（带缓存边界）
- 段级缓存
- **对话压缩（增量 / 全量）**
- 微压缩（工具结果清理）
- 压缩后上下文恢复

### Memory 模块 — "跨轮记什么"

- 长期记忆 CRUD（文件系统 MEMORY.md + 会话文件）
- 对话历史持久化（SQL + JSONL）
- 记忆提取（正则 + LLM）
- 记忆相关性选择（LLM）
- **压缩调度**（判断何时压缩、用增量还是全量）
- **压缩结果持久化**（保存摘要到 FileHistoryStore）
- 上下文消息列表构建（系统提示 + 摘要 + 最近消息）

## 4. 重构步骤

### Step 1：迁移 `llm_utils` 到 `utils` 模块

将 `src/ai/core/memory/llm_utils.py` 迁移到 `src/ai/utils/llm_utils.py`，消除 context → memory 的反向依赖。

**改动文件：**

| 文件 | 改动 |
|------|------|
| `src/ai/utils/llm_utils.py` | 新建，内容从 `memory/llm_utils.py` 迁入 |
| `src/ai/core/memory/llm_utils.py` | 改为从 `src.ai.utils.llm_utils` 重新导出（保持向后兼容） |
| `src/ai/core/context/compact.py` | import 路径改为 `src.ai.utils.llm_utils` |
| `src/ai/core/memory/strategies/compression.py` | import 路径改为 `src.ai.utils.llm_utils` |
| `src/ai/core/memory/extractor.py` | import 路径改为 `src.ai.utils.llm_utils` |
| `src/ai/core/rag/encoder.py` | import 路径改为 `src.ai.utils.llm_utils` |

### Step 2：扩展 `FullCompact` 支持增量模式

当前 `FullCompact` 只支持全量压缩（9 章节结构）。扩展它支持增量压缩（摘要合并），使 `CompressionStrategy` 不再需要自己实现压缩逻辑。

**改动文件：**

| 文件 | 改动 |
|------|------|
| `src/ai/core/context/compact.py` | `FullCompact` 新增 `compact_incremental()` 方法 |

**`FullCompact` 扩展后的接口：**

```python
class FullCompact:
    """对话压缩器 — 支持全量和增量两种模式。"""

    def __init__(
        self,
        llm: BaseChatModel,
        prompt_service: object,
        *,
        keep_recent: int = 10,
    ) -> None:
        ...

    async def compact_full(
        self,
        messages: list[Any],
        existing_summary: str = "",
    ) -> tuple[str, list[dict[str, Any]]]:
        """全量压缩：9 章节标准结构。"""
        ...

    async def compact_incremental(
        self,
        records: list[dict[str, Any]],
        existing_summary: str = "",
    ) -> str:
        """增量压缩：将新增消息合并到已有摘要。

        Args:
            records: 待压缩的消息记录列表（FileHistoryStore 格式）。
            existing_summary: 已有的摘要文本。

        Returns:
            合并后的摘要文本。
        """
        ...
```

### Step 3：精简 `CompressionStrategy`

将 `CompressionStrategy._aincremental_compress()` 中的 LLM 压缩逻辑委托给 `FullCompact.compact_incremental()`，自身只负责：

- 判断何时触发压缩（消息数阈值）
- 判断使用增量还是全量模式
- 从 FileHistoryStore 读取待压缩记录
- 将压缩结果保存到 FileHistoryStore

**改动文件：**

| 文件 | 改动 |
|------|------|
| `src/ai/core/memory/strategies/compression.py` | 移除 `_aincremental_compress` 中的 LLM 调用逻辑，委托给 `FullCompact` |
| `src/ai/core/memory/strategies/compression.py` | 移除 `_build_compress_system` 和 `_get_template_content`（已迁入 FullCompact） |

**重构后的 `_aincremental_compress`：**

```python
async def _aincremental_compress(
    self, session_id: str, *, total: int | None = None
) -> None:
    """增量压缩：委托 FullCompact 执行，自身只负责调度和持久化。"""
    summary_data = self._file_store.read_summary(session_id)
    existing_summary = summary_data.get("summary", "") if summary_data else ""
    existing_end = (
        summary_data.get("compressed_range", [0, 0])[1] if summary_data else 0
    )

    if total is None:
        total = self._file_store.message_count(session_id)
    compress_end = total - self._keep_recent

    if compress_end <= existing_end:
        return

    records = self._file_store.read_records(
        session_id, offset=existing_end, limit=compress_end - existing_end
    )
    if not records:
        return

    try:
        new_summary = await self._full_compact.compact_incremental(
            records, existing_summary=existing_summary
        )

        file_refs = [
            {
                "index": r.get("index", 0),
                "timestamp": r.get("timestamp", ""),
                "snippet": str(r.get("content", ""))[:80],
            }
            for r in records
        ]

        self._file_store.save_summary(
            session_id,
            new_summary,
            compressed_range=(0, compress_end),
            file_references=file_refs,
        )
        logger.info(
            "会话 %s 增量压缩完成：压缩了 %d 条消息，保留最近 %d 条",
            session_id, len(records), self._keep_recent,
        )
    except Exception:
        logger.warning("增量压缩失败，保留原始消息", exc_info=True)
```

### Step 4：消除 `_get_template_content` 重复

`FullCompact` 内部统一处理提示词获取，不再需要外部的 `_get_template_content` 函数。

**改动文件：**

| 文件 | 改动 |
|------|------|
| `src/ai/core/memory/strategies/compression.py` | 移除 `_get_template_content` 函数 |
| `src/ai/core/context/compact.py` | `_get_template_content` 改为 `FullCompact` 的私有方法 |

### Step 5：清理 `memory/llm_utils.py`

迁移完成后，`memory/llm_utils.py` 仅保留向后兼容的重新导出。

**最终内容：**

```python
"""向后兼容 — 实际实现已迁至 src.ai.utils.llm_utils。"""

from src.ai.utils.llm_utils import build_llm_chain  # noqa: F401
```

## 5. 依赖方向（重构后）

```
src/ai/utils/llm_utils.py          ← 纯工具，无模块依赖
       ↑
src/ai/core/context/compact.py     ← 压缩算法（FullCompact、MicroCompact）
       ↑
src/ai/core/memory/strategies/     ← 压缩调度 + 持久化（CompressionStrategy）
       ↑
src/ai/core/context/service.py     ← 门面编排（ContextService）
```

依赖方向：`utils` ← `context` ← `memory`，无反向依赖。

## 6. 不改动的部分

- `MemoryService` — 长期记忆 CRUD 不涉及压缩，无需改动
- `ChatHistoryManager` / `FileHistoryStore` — 持久化层不变
- `ContextService` — 编排逻辑不变，仍通过 `strategy` 接口调用 memory
- `ContextRestorer` — 摘要解析逻辑不变
- 各 Collector — 收集逻辑不变

## 7. 验证方案

每个 Step 完成后：

1. **编译检查**：`uv run python -m compileall -q src/ai main.py`
2. **Ruff 检查**：`ruff check src/ && ruff format src/`
3. **依赖方向检查**：确认 `context/` 不再 import `memory/` 的任何模块（除类型检查）
4. **端到端**：发送多轮对话（>30 条消息），确认增量压缩正常触发
5. **全量压缩**：发送 >100 条消息，确认全量压缩正常触发

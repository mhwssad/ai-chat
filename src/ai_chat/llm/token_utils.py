"""Token 计数工具 — tiktoken 精确计数 + 使用量解析。"""

from typing import Optional

from langchain_core.messages import BaseMessage

from src.ai_chat.config.logging_setup import get_logger

logger = get_logger(__name__)

# tiktoken 编码器单例，延迟初始化
_encoder = None

# 字符级回退的估算比率
_CHARS_PER_TOKEN: float = 3.5


def _get_encoder():
    """获取 tiktoken 编码器实例（cl100k_base，GPT-4/GPT-4o 同款）。

    延迟导入 tiktoken 以避免模块加载时的网络请求（首次调用时下载词表）。
    """
    global _encoder
    if _encoder is not None:
        return _encoder
    try:
        import tiktoken
        _encoder = tiktoken.get_encoding("cl100k_base")
        logger.debug("tiktoken cl100k_base 编码器加载成功")
    except ImportError:
        logger.warning("tiktoken 未安装，回退到字符级 token 估算（精度约 ±30%）")
        _encoder = False
    except Exception as e:
        logger.warning("tiktoken 加载失败: %s，回退到字符级估算", e)
        _encoder = False
    return _encoder if _encoder is not False else None


def count_text_tokens(text: str) -> int:
    """精确计算文本的 token 数量。

    使用 tiktoken cl100k_base 编码器计数。
    对 OpenAI 模型误差 <2%，Claude/Gemini 约 ~10%，Ollama 本地模型约 ~15%。
    tiktoken 不可用时回退到字符级估算（约 3.5 字符/token）。
    """
    encoder = _get_encoder()
    if encoder is not None:
        return len(encoder.encode(text))
    # 回退：字符级估算
    return max(1, int(len(text) / _CHARS_PER_TOKEN))


def _extract_text_content(content) -> str:
    """从消息 content 中提取纯文本。"""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            item if isinstance(item, str) else str(item.get("text", ""))
            for item in content
        )
    return str(content)


def estimate_message_tokens(message: BaseMessage) -> int:
    """估算单条 LangChain 消息的 token 数。

    对 content 调用 tiktoken 计数，加上 4 token 的消息元数据开销（角色标签等）。
    """
    text = _extract_text_content(message.content)
    return count_text_tokens(text) + 4


def estimate_messages_tokens(messages: list[BaseMessage]) -> int:
    """估算消息列表的总 token 数。"""
    return sum(estimate_message_tokens(msg) for msg in messages)


def extract_total_tokens(usage: Optional[dict]) -> Optional[int]:
    """从 usage 字典中提取总 token 数，统一各供应商格式。

    支持:
    - OpenAI: {'total_tokens': T}
    - OpenAI: {'prompt_tokens': N, 'completion_tokens': M}
    - Claude/Gemini: {'input_tokens': N, 'output_tokens': M}
    """
    if usage is None:
        return None

    # 直接 total_tokens 字段
    if "total_tokens" in usage:
        return usage["total_tokens"]

    # prompt + completion 求和
    prompt = usage.get("prompt_tokens") or usage.get("input_tokens")
    completion = usage.get("completion_tokens") or usage.get("output_tokens")
    if prompt is not None and completion is not None:
        return prompt + completion

    return None


def extract_prompt_tokens(usage: Optional[dict]) -> Optional[int]:
    """从 usage 字典中提取 prompt/input token 数。

    这个值代表发送给 LLM 的上下文消耗，是最精确的上下文大小指标。
    """
    if usage is None:
        return None
    return usage.get("prompt_tokens") or usage.get("input_tokens")

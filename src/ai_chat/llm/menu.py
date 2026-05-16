"""LLM 模块管理入口 — 提供交互式 CLI 菜单查看模型、测试对话、计算 token。"""

from langchain_core.messages import HumanMessage

from src.ai_chat.config.logging_setup import get_logger
from src.ai_chat.llm.factory import llm_factory
from src.ai_chat.llm.model_metadata import get_model_context_size
from src.ai_chat.llm.models import ChatRequest
from src.ai_chat.llm.token_utils import count_text_tokens

logger = get_logger(__name__)


def _choose(prompt: str, options: list[str]) -> int:
    """显示选项列表并等待用户输入，返回选择的序号（从 1 开始）。"""
    for i, opt in enumerate(options, 1):
        print(f"  {i}. {opt}")
    while True:
        raw = input(prompt).strip()
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return int(raw)


def _choose_chat_model() -> str:
    """交互式选择 chat 模型，返回模型名称。"""
    models = llm_factory.get_all_supported_chat_models()
    if not models:
        print("  （无可用 chat 模型，请检查 API Key 配置）\n")
        return ""
    idx = _choose("选择模型: ", models)
    return models[idx - 1]


def _choose_embedding_model() -> str:
    """交互式选择 embedding 模型，返回模型名称。"""
    models = llm_factory.get_all_supported_embedding_models()
    if not models:
        print("  （无可用 embedding 模型）\n")
        return ""
    idx = _choose("选择模型: ", models)
    return models[idx - 1]


def menu_llm():
    """LLM 管理 — 交互式 CLI 菜单。

    功能:
    1. 列出支持的模型（按 chat/embedding 分组）
    2. 测试对话（选模型 → 输入消息 → 显示回复和 token 用量）
    3. 测试嵌入（选模型 → 输入文本 → 显示向量维度）
    4. Token 计数（输入文本 → 显示 tiktoken 计数）
    5. 查看模型上下文信息（上下文窗口大小）
    6. 返回上级菜单
    """
    logger.info("进入 LLM 管理菜单")

    while True:
        print("\n── LLM 管理 ──")
        idx = _choose("操作: ", [
            "列出支持的模型",
            "测试对话",
            "测试嵌入",
            "Token 计数",
            "查看模型上下文信息",
            "返回上级",
        ])
        if idx == 6:
            logger.debug("退出 LLM 管理菜单")
            return

        if idx == 1:
            # 列出支持的模型
            chat_models = llm_factory.get_all_supported_chat_models()
            emb_models = llm_factory.get_all_supported_embedding_models()
            print()
            if chat_models:
                print("  Chat 模型:")
                for m in chat_models:
                    ctx = get_model_context_size(m)
                    print(f"    - {m}  (上下文: {ctx:,} tokens)")
            else:
                print("  Chat 模型: （无，请检查 API Key 配置）")
            if emb_models:
                print("  Embedding 模型:")
                for m in emb_models:
                    print(f"    - {m}")
            else:
                print("  Embedding 模型: （无）")
            print()

        elif idx == 2:
            # 测试对话
            model = _choose_chat_model()
            if not model:
                continue
            text = input("  输入消息: ").strip()
            if not text:
                continue
            try:
                request = ChatRequest(messages=[HumanMessage(content=text)])
                print("  等待回复...")
                response = llm_factory.chat(request, model_name=model)
                print(f"\n  回复: {response.content}\n")
                if response.usage:
                    print(f"  Token 用量: {response.usage}")
                print()
            except Exception as e:
                print(f"\n  错误: {e}\n")
                logger.error("测试对话失败: %s", e)

        elif idx == 3:
            # 测试嵌入
            model = _choose_embedding_model()
            if not model:
                continue
            text = input("  输入文本: ").strip()
            if not text:
                continue
            try:
                print("  计算嵌入...")
                vector = llm_factory.embed(text, model_name=model)
                print(f"\n  向量维度: {len(vector)}")
                print(f"  前 5 个值: {vector[:5]}\n")
            except Exception as e:
                print(f"\n  错误: {e}\n")
                logger.error("测试嵌入失败: %s", e)

        elif idx == 4:
            # Token 计数
            text = input("  输入文本: ").strip()
            if not text:
                continue
            tokens = count_text_tokens(text)
            print(f"  Token 数: {tokens}  (字符数: {len(text)})\n")

        elif idx == 5:
            # 查看模型上下文信息
            model = _choose_chat_model()
            if not model:
                continue
            ctx = get_model_context_size(model)
            threshold = int(ctx * 0.8)
            print(f"\n  模型: {model}")
            print(f"  上下文窗口: {ctx:,} tokens")
            print(f"  压缩阈值 (80%): {threshold:,} tokens\n")

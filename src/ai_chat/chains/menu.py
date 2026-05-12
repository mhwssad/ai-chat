"""Chain 模块管理入口。"""

from src.ai_chat.chains.factory import chain_factory


def _choose(prompt: str, options: list[str]) -> int:
    for i, opt in enumerate(options, 1):
        print(f"  {i}. {opt}")
    while True:
        raw = input(prompt).strip()
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return int(raw)


def _choose_model() -> str:
    model = input("  模型名称（回车默认 qwen-turbo）: ").strip()
    return model or "qwen-turbo"


_CHAIN_MENU = {
    1: ("chat", "ChatChain — 简单对话"),
    2: ("summarize", "SummarizeChain — 文本摘要"),
    3: ("translate", "TranslateChain — 翻译"),
    4: ("extraction", "ExtractionChain — 结构化抽取"),
    5: ("refine", "RefineChain — 文本优化"),
}


def menu_chains():
    """chains 模块管理入口 — 选择并执行 chain。"""
    while True:
        print("\n── 调用链 ──")
        labels = [v[1] for v in _CHAIN_MENU.values()] + ["返回上级"]
        idx = _choose("选择链: ", labels)
        if idx == len(labels):
            return

        name = _CHAIN_MENU[idx][0]
        model = _choose_model()

        if name == "chat":
            chain = chain_factory.create(name, model_name=model)
            text = input("  输入消息: ")
            print(f"\n结果: {chain.invoke(text)}\n")

        elif name == "summarize":
            chain = chain_factory.create(name, model_name=model)
            text = input("  输入待摘要文本: ")
            print(f"\n摘要: {chain.invoke(text)}\n")

        elif name == "translate":
            chain = chain_factory.create(name, model_name=model)
            target = input("  目标语言（默认中文）: ").strip() or "中文"
            text = input("  输入待翻译文本: ")
            print(f"\n译文: {chain.invoke(text, target=target)}\n")

        elif name == "extraction":
            chain = chain_factory.create(name, model_name=model)
            text = input("  输入文本: ")
            fields = input("  提取字段（逗号分隔，如: 姓名,年龄,地址）: ")
            field_list = [f.strip() for f in fields.split(",") if f.strip()]
            print(f"\n结果: {chain.invoke(text, field_list)}\n")

        elif name == "refine":
            chain = chain_factory.create(name, model_name=model)
            text = input("  输入原始文本: ")
            instruction = input("  优化指令: ")
            print(f"\n结果: {chain.invoke(instruction, text)}\n")

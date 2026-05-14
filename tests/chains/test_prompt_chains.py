import unittest
from unittest.mock import MagicMock, patch

from src.ai_chat.chains.chat_chain import (
    ChatChain,
    ExtractionChain,
    RefineChain,
    SummarizeChain,
    TranslateChain,
)


class _FakePipeline:
    def __init__(self) -> None:
        self.last_messages = None

    def invoke(self, messages):
        self.last_messages = messages
        return "ok"

    def stream(self, messages):
        self.last_messages = messages
        yield "ok"


class _FakeLLM:
    def __init__(self, pipeline: _FakePipeline) -> None:
        self.pipeline = pipeline

    def __or__(self, _parser):
        return self.pipeline


class PromptChainTests(unittest.TestCase):
    def setUp(self) -> None:
        self.pipeline = _FakePipeline()
        provider = MagicMock()
        provider.get_client.return_value = _FakeLLM(self.pipeline)
        self.provider = provider
        self.provider_patcher = patch(
            "src.ai_chat.chains.chat_chain.llm_factory.get_chat_provider",
            return_value=self.provider,
        )
        self.provider_patcher.start()

    def tearDown(self) -> None:
        self.provider_patcher.stop()

    def test_chat_chain_inserts_history_between_system_and_human(self) -> None:
        chain = ChatChain(model_name="fake-model")
        history = [MagicMock(content="history")]

        chain.invoke("你好", history=history)

        self.assertEqual(self.pipeline.last_messages[0].type, "system")
        self.assertIs(self.pipeline.last_messages[1], history[0])
        self.assertEqual(self.pipeline.last_messages[-1].content, "你好")

    def test_summarize_chain_call_context_overrides_constructor_context(self) -> None:
        chain = SummarizeChain(
            model_name="fake-model",
            prompt_context={"language": "英文", "instruction": "默认摘要"},
        )

        chain.invoke("正文", instruction="覆盖摘要", prompt_context={"language": "法文"})

        self.assertIn("法文", str(self.pipeline.last_messages[0].content))
        self.assertIn("覆盖摘要", str(self.pipeline.last_messages[1].content))

    def test_translate_chain_uses_target_argument_over_prompt_context(self) -> None:
        chain = TranslateChain(
            model_name="fake-model",
            prompt_context={"target": "日文"},
        )

        chain.invoke("hello", target="德文", prompt_context={"target": "法文"})

        self.assertIn("德文", str(self.pipeline.last_messages[0].content))

    def test_extraction_chain_renders_fields_desc(self) -> None:
        chain = ExtractionChain(model_name="fake-model")

        chain.invoke("张三，20岁", ["姓名", "年龄"])

        self.assertIn("姓名、年龄", str(self.pipeline.last_messages[0].content))
        self.assertEqual(self.pipeline.last_messages[1].content, "张三，20岁")

    def test_refine_chain_uses_prompt_context_language(self) -> None:
        chain = RefineChain(model_name="fake-model", prompt_context={"language": "英文"})

        chain.invoke("精简", "原文")

        self.assertIn("英文", str(self.pipeline.last_messages[0].content))


if __name__ == "__main__":
    unittest.main()

import unittest

from langchain_core.prompts import ChatPromptTemplate

from src.ai_chat.prompts import has_prompt, prompt_registry, render_messages, render_system_prompt


class PromptRegistryTests(unittest.TestCase):
    def test_builtin_prompt_keys_are_registered(self) -> None:
        expected = {
            "chain.chat",
            "chain.summarize",
            "chain.translate",
            "chain.extraction",
            "chain.refine",
            "agent.react.system",
            "graph.chat.system",
            "graph.intent.chat_or_rag",
            "graph.intent.react_or_rag",
            "graph.rag.answer",
        }

        self.assertTrue(expected.issubset(set(prompt_registry.list_prompts())))
        self.assertTrue(all(has_prompt(name) for name in expected))

    def test_render_messages_renders_builtin_prompt(self) -> None:
        messages = render_messages("chain.translate", text="hello", target="中文")

        self.assertEqual(len(messages), 2)
        self.assertIn("中文", str(messages[0].content))
        self.assertEqual(messages[1].content, "hello")

    def test_render_system_prompt_requires_single_system_message(self) -> None:
        prompt_registry.register(
            "test.invalid.system",
            ChatPromptTemplate.from_messages([("human", "hi")]),
        )

        with self.assertRaises(ValueError):
            render_system_prompt("test.invalid.system")

    def test_render_messages_raises_for_missing_required_context(self) -> None:
        with self.assertRaises(KeyError):
            render_messages("chain.translate", text="hello")


if __name__ == "__main__":
    unittest.main()

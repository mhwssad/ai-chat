import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.messages import AIMessage, HumanMessage

from src.ai_chat.graphs.chat_agent import ChatAgent
from src.ai_chat.graphs.chat_graph import ChatGraph
from src.ai_chat.graphs.memory_agent import MemoryAgent
from src.ai_chat.graphs.unified_agent import UnifiedAgent


class _FakeProvider:
    def __init__(self, client) -> None:
        self._client = client

    def get_client(self, _model_name):
        return self._client


class GraphPromptTests(unittest.TestCase):
    def test_chat_agent_uses_registry_system_prompt(self) -> None:
        fake_client = MagicMock()
        fake_agent = AsyncMock()
        fake_agent.ainvoke.return_value = {"messages": [AIMessage(content="ok")]}

        with patch("src.ai_chat.graphs.chat_agent.llm_factory.get_chat_provider", return_value=_FakeProvider(fake_client)), \
             patch("src.ai_chat.graphs.chat_agent.create_agent", return_value=fake_agent) as create_agent_mock:
            ChatAgent(model_name="fake-model")

        self.assertIn("你可以使用工具", create_agent_mock.call_args.kwargs["system_prompt"])

    def test_chat_agent_supports_raw_system_prompt_override(self) -> None:
        fake_client = MagicMock()
        default_agent = AsyncMock()
        default_agent.ainvoke.return_value = {"messages": [AIMessage(content="ok")]}
        temp_agent = AsyncMock()
        temp_agent.ainvoke.return_value = {"messages": [AIMessage(content="override")]}

        with patch("src.ai_chat.graphs.chat_agent.llm_factory.get_chat_provider", return_value=_FakeProvider(fake_client)), \
             patch("src.ai_chat.graphs.chat_agent.create_agent", side_effect=[default_agent, temp_agent]):
            agent = ChatAgent(model_name="fake-model")
            result = agent.invoke("hi", system_prompt_override="技能提示词")

        self.assertEqual(result, "override")

    def test_memory_agent_uses_registry_system_prompt(self) -> None:
        fake_client = MagicMock()
        fake_agent = AsyncMock()
        fake_agent.ainvoke.return_value = {"messages": [AIMessage(content="ok")]}
        fake_memory = MagicMock()
        fake_memory.session_id = "session-1"
        fake_memory.load_history.return_value = []

        with patch("src.ai_chat.graphs.memory_agent.llm_factory.get_chat_provider", return_value=_FakeProvider(fake_client)), \
             patch("src.ai_chat.graphs.memory_agent.create_agent", return_value=fake_agent) as create_agent_mock, \
             patch("src.ai_chat.graphs.memory_agent.ConversationMemory", return_value=fake_memory):
            MemoryAgent(model_name="fake-model")

        self.assertIn("你可以使用工具", create_agent_mock.call_args.kwargs["system_prompt"])

    def test_chat_graph_classify_and_rag_use_prompt_registry(self) -> None:
        fake_store = MagicMock()
        fake_store.similarity_search.return_value = [{"content": "知识库内容"}]
        fake_client = MagicMock()
        fake_client.invoke.side_effect = [
            AIMessage(content="rag"),
            AIMessage(content="答案"),
        ]

        with patch("src.ai_chat.graphs.chat_graph.llm_factory.get_chat_provider", return_value=_FakeProvider(fake_client)), \
             patch("src.ai_chat.graphs.chat_graph.rag_factory.create_store", return_value=fake_store):
            graph = ChatGraph(model_name="fake-model")
            result = graph.invoke("什么是 RAG", history=[])

        self.assertEqual(result, "答案")
        classify_messages = fake_client.invoke.call_args_list[0].args[0]
        rag_messages = fake_client.invoke.call_args_list[1].args[0]
        self.assertEqual(classify_messages[1].content, "什么是 RAG")
        self.assertIn("知识库内容", str(rag_messages[1].content))

    def test_unified_agent_uses_registry_prompts_and_skill_override(self) -> None:
        fake_store = MagicMock()
        fake_store.similarity_search.return_value = [{"content": "知识"}]
        fake_client = MagicMock()
        react_agent = AsyncMock()
        react_agent.ainvoke.return_value = {"messages": [AIMessage(content="react ok")]}
        temp_agent = AsyncMock()
        temp_agent.ainvoke.return_value = {"messages": [AIMessage(content="skill ok")]}
        fake_memory = MagicMock()
        fake_memory.session_id = "session-1"
        fake_memory.load_history.return_value = []

        with patch("src.ai_chat.graphs.unified_agent.llm_factory.get_chat_provider", return_value=_FakeProvider(fake_client)), \
             patch("src.ai_chat.graphs.unified_agent.rag_factory.create_store", return_value=fake_store), \
             patch("src.ai_chat.graphs.unified_agent.ConversationMemory", return_value=fake_memory), \
             patch("src.ai_chat.graphs.unified_agent.create_agent", side_effect=[react_agent, temp_agent]) as create_agent_mock:
            agent = UnifiedAgent(model_name="fake-model")
            result = agent.invoke("hi", system_prompt_override="技能提示词")

        self.assertEqual(result, "skill ok")
        self.assertIn("你可以使用工具", create_agent_mock.call_args_list[0].kwargs["system_prompt"])
        self.assertEqual(create_agent_mock.call_args_list[1].kwargs["system_prompt"], "技能提示词")


if __name__ == "__main__":
    unittest.main()

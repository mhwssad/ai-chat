import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from src.ai_chat.memory.models import Session, SessionNotFoundException
from src.ai_chat.web.app import create_app


class WebAppTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app()
        self.client = TestClient(self.app)

    def test_root_redirects_to_chat(self) -> None:
        response = self.client.get("/", follow_redirects=False)

        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["location"], "/chat")

    @patch("src.ai_chat.web.app.list_recent_sessions", return_value=[])
    def test_chat_page_renders_form(self, _list_recent_sessions) -> None:
        response = self.client.get("/chat")

        self.assertEqual(response.status_code, 200)
        self.assertIn("MemoryAgent", response.text)
        self.assertIn("UnifiedAgent", response.text)
        self.assertIn("新建会话", response.text)
        self.assertIn("发送消息", response.text)

    @patch("src.ai_chat.web.app.create_chat_session", return_value="session-123")
    def test_create_session_redirects_to_chat(self, _create_chat_session) -> None:
        response = self.client.post(
            "/chat/session",
            data={"agent_name": "memory", "model_name": "demo-model"},
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 303)
        self.assertIn("/chat?", response.headers["location"])
        self.assertIn("session_id=session-123", response.headers["location"])

    @patch("src.ai_chat.web.app.send_chat_message", return_value="ok")
    def test_send_message_redirects_back_to_chat(self, _send_chat_message) -> None:
        response = self.client.post(
            "/chat/message",
            data={
                "agent_name": "memory",
                "model_name": "demo-model",
                "session_id": "session-123",
                "message": "你好",
            },
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 303)
        self.assertIn("session_id=session-123", response.headers["location"])

    @patch(
        "src.ai_chat.web.app.list_recent_sessions",
        return_value=[Session(session_id="session-1", title="最近会话")],
    )
    @patch(
        "src.ai_chat.web.app.load_session_messages",
        return_value=[],
    )
    @patch("src.ai_chat.web.app.ensure_session_exists", return_value=Session(session_id="session-1", title="最近会话"))
    def test_chat_page_shows_recent_sessions(
        self,
        _ensure_session_exists,
        _load_session_messages,
        _list_recent_sessions,
    ) -> None:
        response = self.client.get("/chat?session_id=session-1")

        self.assertEqual(response.status_code, 200)
        self.assertIn("最近会话", response.text)
        self.assertIn("session-1", response.text)

    def test_placeholder_pages_render(self) -> None:
        for path in ("/chains", "/tools", "/memory", "/mcp", "/skills"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200)
            self.assertIn("后续", response.text)

    @patch("src.ai_chat.web.app.ensure_session_exists", side_effect=SessionNotFoundException("missing"))
    @patch("src.ai_chat.web.app.list_recent_sessions", return_value=[])
    def test_missing_session_shows_error(self, _list_recent_sessions, _ensure_session_exists) -> None:
        response = self.client.get("/chat?session_id=missing")

        self.assertEqual(response.status_code, 200)
        self.assertIn("会话不存在", response.text)

    @patch("src.ai_chat.web.app.send_chat_message", side_effect=RuntimeError("provider failed"))
    @patch("src.ai_chat.web.app.ensure_session_exists", return_value=Session(session_id="session-1"))
    @patch("src.ai_chat.web.app.load_session_messages", return_value=[])
    @patch("src.ai_chat.web.app.list_recent_sessions", return_value=[])
    def test_send_message_errors_are_rendered(
        self,
        _list_recent_sessions,
        _load_session_messages,
        _ensure_session_exists,
        _send_chat_message,
    ) -> None:
        response = self.client.post(
            "/chat/message",
            data={
                "agent_name": "unified",
                "model_name": "demo-model",
                "session_id": "session-1",
                "message": "你好",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("发送消息失败", response.text)


if __name__ == "__main__":
    unittest.main()

import uuid

from app.core.session import SessionStore
from app.models.schemas import ChatMessage


class TestSessionStore:
    def test_create_session_returns_valid_uuid(self):
        store = SessionStore()
        session_id = store.create_session()
        # Should parse as UUID without raising
        uuid.UUID(session_id)

    def test_create_session_is_unique(self):
        store = SessionStore()
        ids = {store.create_session() for _ in range(10)}
        assert len(ids) == 10

    def test_append_and_get_history(self):
        store = SessionStore()
        session_id = store.create_session()
        msg1 = ChatMessage(role="user", content="Hello")
        msg2 = ChatMessage(role="assistant", content="Hi!")
        store.append_message(session_id, msg1)
        store.append_message(session_id, msg2)
        history = store.get_history(session_id)
        assert len(history) == 2
        assert history[0].content == "Hello"
        assert history[1].content == "Hi!"

    def test_delete_session(self):
        store = SessionStore()
        session_id = store.create_session()
        store.append_message(session_id, ChatMessage(role="user", content="Test"))
        store.delete_session(session_id)
        assert store.get_history(session_id) == []

    def test_delete_nonexistent_session_is_safe(self):
        store = SessionStore()
        store.delete_session("nonexistent-id")  # Should not raise

    def test_get_history_invalid_session_returns_empty(self):
        store = SessionStore()
        history = store.get_history("does-not-exist")
        assert history == []

    def test_append_message_to_unknown_session_creates_it(self):
        store = SessionStore()
        store.append_message("new-session", ChatMessage(role="user", content="Start"))
        history = store.get_history("new-session")
        assert len(history) == 1

    def test_session_exists(self):
        store = SessionStore()
        session_id = store.create_session()
        assert store.session_exists(session_id) is True
        assert store.session_exists("missing") is False

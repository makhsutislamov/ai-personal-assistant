from __future__ import annotations

import uuid

from app.models.schemas import ChatMessage


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, list[ChatMessage]] = {}

    def create_session(self) -> str:
        session_id = str(uuid.uuid4())
        self._sessions[session_id] = []
        return session_id

    def get_history(self, session_id: str) -> list[ChatMessage]:
        return self._sessions.get(session_id, [])

    def append_message(self, session_id: str, message: ChatMessage) -> None:
        if session_id not in self._sessions:
            self._sessions[session_id] = []
        self._sessions[session_id].append(message)

    def delete_session(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def session_exists(self, session_id: str) -> bool:
        return session_id in self._sessions

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from assistant.config import Settings, get_settings
from assistant.conversation import orchestrator
from assistant.conversation.schemas import ChatRequest, ChatResponse
from assistant.db.models import ConversationMessage
from pydantic import BaseModel

router = APIRouter(tags=["chat"])


async def _get_session() -> AsyncSession:  # type: ignore[return]
    raise NotImplementedError("DB session dependency not configured")


class SessionTranscript(BaseModel):
    session_id: str
    messages: list[dict[str, str]]


@router.post("/chat/respond", response_model=ChatResponse)
async def chat_respond(
    body: ChatRequest,
    session: AsyncSession = Depends(_get_session),
    settings: Settings = Depends(get_settings),
) -> ChatResponse:
    return await orchestrator.respond(session, body, settings)


@router.get("/chat/sessions/{session_id}", response_model=SessionTranscript)
async def get_session(
    session_id: str,
    session: AsyncSession = Depends(_get_session),
) -> SessionTranscript:
    from assistant.conversation.session import get_history

    messages = await get_history(session, session_id)
    return SessionTranscript(
        session_id=session_id,
        messages=[{"role": msg.role, "content": msg.content} for msg in messages],
    )


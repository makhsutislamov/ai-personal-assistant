from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from assistant.config import Settings, get_settings
from assistant.conversation import orchestrator
from assistant.conversation.schemas import ChatRequest, ChatResponse
from assistant.notes.generator import generate_notes
from assistant.notes.schemas import GeneratedNotes

router = APIRouter(tags=["chat"])


async def _get_session() -> AsyncSession:  # type: ignore[return]
    raise NotImplementedError("DB session dependency not configured")


class SessionTranscript(BaseModel):
    session_id: str
    messages: list[dict[str, str]]


class SaveNotesRequest(BaseModel):
    notes: GeneratedNotes
    tags: list[str] | None = None


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


@router.post("/chat/sessions/{session_id}/notes", response_model=GeneratedNotes)
async def generate_session_notes(
    session_id: str,
    session: AsyncSession = Depends(_get_session),
    settings: Settings = Depends(get_settings),
) -> GeneratedNotes:
    return await generate_notes(session, session_id, settings)


@router.post("/chat/sessions/{session_id}/notes/save", status_code=204)
async def save_session_notes(
    session_id: str,
    body: SaveNotesRequest,
    session: AsyncSession = Depends(_get_session),
) -> None:
    from assistant.memory import service as memory_service
    import json

    content = f"Summary: {body.notes.summary}\n"
    if body.notes.decisions:
        content += "Decisions:\n" + "\n".join(f"- {d}" for d in body.notes.decisions) + "\n"
    if body.notes.action_items:
        content += "Action Items:\n" + "\n".join(f"- {a}" for a in body.notes.action_items) + "\n"
    if body.notes.open_questions:
        content += "Open Questions:\n" + "\n".join(f"- {q}" for q in body.notes.open_questions)

    tags = body.tags or body.notes.suggested_tags

    await memory_service.auto_ingest(
        session=session,
        content=content.strip(),
        source_type="conversation",
        source_ref=session_id,
        metadata={"tags": tags, "type": "notes"},
    )



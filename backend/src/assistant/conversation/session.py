from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from assistant.db.models import ConversationMessage, ConversationSession


async def get_or_create_session(session: AsyncSession, session_id: str | None) -> str:
    """Return the given session_id if valid, or create a new session."""
    if session_id:
        result = await session.execute(
            select(ConversationSession).where(ConversationSession.session_id == session_id)
        )
        row = result.scalar_one_or_none()
        if row is not None:
            return session_id

    new_id = str(uuid.uuid4())
    conv = ConversationSession(session_id=new_id, topic_tags="[]")
    session.add(conv)
    await session.commit()
    return new_id


async def get_history(
    session: AsyncSession, session_id: str, limit: int = 20
) -> list[ConversationMessage]:
    result = await session.execute(
        select(ConversationMessage)
        .where(ConversationMessage.session_id == session_id)
        .order_by(ConversationMessage.created_at.asc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def append_message(
    session: AsyncSession, session_id: str, role: str, content: str
) -> ConversationMessage:
    msg = ConversationMessage(
        message_id=str(uuid.uuid4()),
        session_id=session_id,
        role=role,
        content=content,
    )
    session.add(msg)
    await session.commit()
    return msg

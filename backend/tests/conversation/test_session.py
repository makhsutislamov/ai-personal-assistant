from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from assistant.conversation.session import append_message, get_history, get_or_create_session
from assistant.db.engine import create_engine, create_session_factory
from assistant.db.migrations import run_migrations


@pytest.fixture
async def db_session():
    engine = create_engine(":memory:")
    await run_migrations(engine)
    factory = create_session_factory(engine)
    async with factory() as session:
        yield session
    await engine.dispose()


async def test_create_new_session(db_session: AsyncSession):
    sid = await get_or_create_session(db_session, None)
    assert sid is not None
    assert len(sid) == 36  # UUID format


async def test_reuse_existing_session(db_session: AsyncSession):
    sid = await get_or_create_session(db_session, None)
    sid2 = await get_or_create_session(db_session, sid)
    assert sid == sid2


async def test_invalid_session_creates_new(db_session: AsyncSession):
    sid = await get_or_create_session(db_session, "non-existent-id")
    assert sid != "non-existent-id"


async def test_append_and_retrieve_messages(db_session: AsyncSession):
    sid = await get_or_create_session(db_session, None)
    await append_message(db_session, sid, "user", "Hello")
    await append_message(db_session, sid, "assistant", "Hi there")

    history = await get_history(db_session, sid)
    assert len(history) == 2
    assert history[0].role == "user"
    assert history[0].content == "Hello"
    assert history[1].role == "assistant"

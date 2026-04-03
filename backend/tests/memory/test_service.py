from __future__ import annotations

from datetime import datetime, timedelta, timezone, UTC
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from assistant.db.engine import create_engine, create_session_factory
from assistant.db.migrations import run_migrations
from assistant.memory import service as memory_service
from assistant.memory.schemas import DeleteFilter


@pytest.fixture
async def db_session():
    engine = create_engine(":memory:")
    await run_migrations(engine)
    factory = create_session_factory(engine)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest.fixture(autouse=True)
def mock_embedding():
    """Mock Ollama embedding so tests don't need a running Ollama."""
    with patch(
        "assistant.memory.service.generate_embedding",
        new=AsyncMock(return_value=[0.1, 0.2, 0.3]),
    ):
        yield


async def test_create_and_confirm_candidate(db_session: AsyncSession):
    candidate = await memory_service.create_candidate(
        db_session,
        content="Test memory",
        source_type="conversation",
    )
    assert candidate.candidate_id
    assert candidate.content == "Test memory"

    record = await memory_service.confirm_candidate(db_session, candidate.candidate_id)
    assert record.memory_id
    assert record.canonical_text == "Test memory"
    assert record.source_type == "conversation"


async def test_reject_candidate(db_session: AsyncSession):
    candidate = await memory_service.create_candidate(
        db_session,
        content="Rejected memory",
        source_type="conversation",
    )
    await memory_service.reject_candidate(candidate.candidate_id)

    # Confirming after reject should raise
    with pytest.raises(ValueError, match="not found"):
        await memory_service.confirm_candidate(db_session, candidate.candidate_id)


async def test_auto_ingest(db_session: AsyncSession):
    record = await memory_service.auto_ingest(
        db_session,
        content="Auto ingested content",
        source_type="apple_notes",
    )
    assert record.memory_id
    assert record.canonical_text == "Auto ingested content"


async def test_delete_by_memory_id(db_session: AsyncSession):
    record = await memory_service.auto_ingest(
        db_session,
        content="To be deleted",
        source_type="conversation",
    )
    result = await memory_service.delete_memories(
        db_session, DeleteFilter(memory_id=record.memory_id)
    )
    assert result.deleted_count == 1


async def test_delete_by_source_type(db_session: AsyncSession):
    await memory_service.auto_ingest(db_session, "note 1", "apple_notes")
    await memory_service.auto_ingest(db_session, "note 2", "apple_notes")
    await memory_service.auto_ingest(db_session, "keep this", "conversation")

    result = await memory_service.delete_memories(
        db_session, DeleteFilter(source_type="apple_notes")
    )
    assert result.deleted_count == 2


async def test_delete_by_time_before(db_session: AsyncSession):
    await memory_service.auto_ingest(db_session, "old content", "conversation")
    future_cutoff = datetime.now(UTC) + timedelta(minutes=1)

    result = await memory_service.delete_memories(
        db_session, DeleteFilter(time_before=future_cutoff)
    )
    assert result.deleted_count >= 1


async def test_confirm_nonexistent_candidate(db_session: AsyncSession):
    with pytest.raises(ValueError):
        await memory_service.confirm_candidate(db_session, "nonexistent-id")

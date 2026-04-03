from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from assistant.db.engine import create_engine, create_session_factory
from assistant.db.migrations import run_migrations
from assistant.db.models import MemoryRecord
from assistant.db.vector import encode_embedding
from assistant.retrieval import service as retrieval_service
from assistant.retrieval.schemas import RetrievalFilter


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
    with patch(
        "assistant.retrieval.service.generate_embedding",
        new=AsyncMock(return_value=[1.0, 0.0, 0.0]),
    ):
        yield


async def _seed(session: AsyncSession, text: str, embedding: list[float], source: str = "conversation") -> str:
    mid = str(uuid.uuid4())
    record = MemoryRecord(
        memory_id=mid,
        source_type=source,
        canonical_text=text,
        embedding=encode_embedding(embedding),
    )
    session.add(record)
    await session.commit()
    return mid


async def test_returns_ranked_results(db_session: AsyncSession):
    await _seed(db_session, "best match", [1.0, 0.0, 0.0])
    await _seed(db_session, "partial match", [0.7, 0.3, 0.0])
    await _seed(db_session, "poor match", [0.0, 0.0, 1.0])

    result = await retrieval_service.query(db_session, "test query")
    assert len(result.items) == 3
    # First result should have highest score
    assert result.items[0].score >= result.items[1].score >= result.items[2].score


async def test_filter_by_source_type(db_session: AsyncSession):
    await _seed(db_session, "apple note content", [1.0, 0.0], source="apple_notes")
    await _seed(db_session, "browser capture", [0.9, 0.1], source="browser_capture")

    result = await retrieval_service.query(
        db_session,
        "test",
        filters=RetrievalFilter(source_types=["apple_notes"]),
    )
    assert all(item.source.source_type == "apple_notes" for item in result.items)


async def test_empty_results_return_gracefully(db_session: AsyncSession):
    result = await retrieval_service.query(db_session, "nothing here")
    assert result.items == []
    assert result.query_latency_ms >= 0


async def test_latency_tracked(db_session: AsyncSession):
    await _seed(db_session, "content", [1.0, 0.0])
    result = await retrieval_service.query(db_session, "query")
    assert result.query_latency_ms >= 0

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from assistant.db.models import Base, MemoryRecord
from assistant.db.vector import encode_embedding
from assistant.evaluation.recall import evaluate_recall
from assistant.evaluation.schemas import EvalCase


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()


def _make_embedding(value: float, dims: int = 4) -> list[float]:
    """Simple embedding where all dims are the same value."""
    return [value] * dims


def _add_record(session, content: str, source_type: str = "test") -> MemoryRecord:
    memory_id = str(uuid.uuid4())
    emb = _make_embedding(0.5)
    record = MemoryRecord(
        memory_id=memory_id,
        canonical_text=content,
        source_type=source_type,
        embedding=encode_embedding(emb),
    )
    session.add(record)
    return record


async def test_evaluate_recall_perfect(session: AsyncSession):
    r = _add_record(session, "Paris is the capital of France")
    await session.commit()

    with patch(
        "assistant.evaluation.recall.generate_embedding",
        new=AsyncMock(return_value=_make_embedding(0.5)),
    ):
        metrics = await evaluate_recall(session, [
            EvalCase(query="capital of France", expected_memory_ids=[r.memory_id])
        ])

    assert metrics.recall == 1.0


async def test_evaluate_recall_no_overlap(session: AsyncSession):
    _add_record(session, "Irrelevant content")
    await session.commit()

    with patch(
        "assistant.evaluation.recall.generate_embedding",
        new=AsyncMock(return_value=_make_embedding(0.5)),
    ):
        metrics = await evaluate_recall(session, [
            EvalCase(query="unrelated query", expected_memory_ids=["nonexistent-id"])
        ])

    assert metrics.recall == 0.0
    assert metrics.precision == 0.0


async def test_evaluate_recall_empty_eval_set(session: AsyncSession):
    metrics = await evaluate_recall(session, [])
    assert metrics.precision == 0.0
    assert metrics.recall == 0.0
    assert metrics.f1 == 0.0


async def test_evaluate_recall_f1_computed(session: AsyncSession):
    r1 = _add_record(session, "Item one")
    r2 = _add_record(session, "Item two")
    await session.commit()

    with patch(
        "assistant.evaluation.recall.generate_embedding",
        new=AsyncMock(return_value=_make_embedding(0.5)),
    ):
        metrics = await evaluate_recall(session, [
            EvalCase(query="items", expected_memory_ids=[r1.memory_id, r2.memory_id])
        ])

    # f1 should be computed when precision and recall are non-zero
    if metrics.precision > 0 and metrics.recall > 0:
        expected_f1 = 2 * metrics.precision * metrics.recall / (metrics.precision + metrics.recall)
        assert abs(metrics.f1 - expected_f1) < 0.001

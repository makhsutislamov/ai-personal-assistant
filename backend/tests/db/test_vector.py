from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from assistant.db.engine import create_engine, create_session_factory
from assistant.db.migrations import run_migrations
from assistant.db.models import MemoryRecord
from assistant.db.vector import cosine_similarity, decode_embedding, encode_embedding, search_similar


@pytest.fixture
async def db_session():
    engine = create_engine(":memory:")
    await run_migrations(engine)
    factory = create_session_factory(engine)
    async with factory() as session:
        yield session
    await engine.dispose()


def test_encode_decode_roundtrip():
    original = [0.1, 0.2, 0.3, 0.4]
    encoded = encode_embedding(original)
    decoded = decode_embedding(encoded)
    assert all(abs(a - b) < 1e-6 for a, b in zip(original, decoded))


def test_cosine_similarity_identical():
    v = [1.0, 0.0, 0.0]
    assert cosine_similarity(v, v) == pytest.approx(1.0)


def test_cosine_similarity_orthogonal():
    a = [1.0, 0.0]
    b = [0.0, 1.0]
    assert cosine_similarity(a, b) == pytest.approx(0.0)


def test_cosine_similarity_zero_vector():
    assert cosine_similarity([0.0, 0.0], [1.0, 1.0]) == pytest.approx(0.0)


async def test_search_similar_ranking(db_session: AsyncSession):
    # Insert three records with known embeddings
    records = [
        MemoryRecord(
            memory_id=str(uuid.uuid4()),
            source_type="conversation",
            canonical_text="close match",
            embedding=encode_embedding([1.0, 0.0, 0.0]),
        ),
        MemoryRecord(
            memory_id=str(uuid.uuid4()),
            source_type="conversation",
            canonical_text="farther match",
            embedding=encode_embedding([0.0, 1.0, 0.0]),
        ),
        MemoryRecord(
            memory_id=str(uuid.uuid4()),
            source_type="conversation",
            canonical_text="closest match",
            embedding=encode_embedding([0.9, 0.1, 0.0]),
        ),
    ]
    for r in records:
        db_session.add(r)
    await db_session.commit()

    query = [1.0, 0.0, 0.0]
    results = await search_similar(db_session, query, top_k=3)

    assert len(results) == 3
    # First result should be the one with embedding [1.0, 0.0, 0.0]
    assert results[0]["canonical_text"] == "close match"
    # Scores should be descending
    assert results[0]["score"] >= results[1]["score"] >= results[2]["score"]


async def test_search_excludes_deleted(db_session: AsyncSession):
    from datetime import datetime, timezone

    active = MemoryRecord(
        memory_id=str(uuid.uuid4()),
        source_type="conversation",
        canonical_text="active",
        embedding=encode_embedding([1.0, 0.0]),
    )
    deleted = MemoryRecord(
        memory_id=str(uuid.uuid4()),
        source_type="conversation",
        canonical_text="deleted",
        embedding=encode_embedding([1.0, 0.0]),
        deleted_at=datetime.now(timezone.utc),
    )
    db_session.add(active)
    db_session.add(deleted)
    await db_session.commit()

    results = await search_similar(db_session, [1.0, 0.0], top_k=10, exclude_deleted=True)
    texts = [r["canonical_text"] for r in results]
    assert "active" in texts
    assert "deleted" not in texts

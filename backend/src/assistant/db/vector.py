from __future__ import annotations

import struct

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# sqlite-vec stores float32 vectors as raw bytes (little-endian IEEE 754)


def _encode_embedding(embedding: list[float]) -> bytes:
    return struct.pack(f"{len(embedding)}f", *embedding)


def _decode_embedding(data: bytes) -> list[float]:
    n = len(data) // 4
    return list(struct.unpack(f"{n}f", data))


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


async def search_similar(
    session: AsyncSession,
    query_embedding: list[float],
    top_k: int = 10,
    source_type: str | None = None,
    exclude_deleted: bool = True,
) -> list[dict[str, object]]:
    """Return top-k memory records by cosine similarity.

    Falls back to pure-Python scoring because sqlite-vec virtual tables
    require a separate CREATE VIRTUAL TABLE setup. This implementation
    works on the standard memory_records table and is replaced by the
    sqlite-vec accelerated path once the virtual table is set up.
    """
    query = """
        SELECT memory_id, source_type, source_ref, canonical_text,
               sensitivity_class, confidence, embedding, created_at
        FROM memory_records
        WHERE embedding IS NOT NULL
    """
    params: dict[str, object] = {}

    if exclude_deleted:
        query += " AND deleted_at IS NULL"
    if source_type:
        query += " AND source_type = :source_type"
        params["source_type"] = source_type

    result = await session.execute(text(query), params)
    rows = result.fetchall()

    scored: list[tuple[float, object]] = []
    for row in rows:
        emb = _decode_embedding(row.embedding)  # type: ignore[arg-type]
        score = cosine_similarity(query_embedding, emb)
        scored.append((score, row))

    scored.sort(key=lambda x: x[0], reverse=True)

    return [
        {
            "memory_id": row.memory_id,
            "source_type": row.source_type,
            "source_ref": row.source_ref,
            "canonical_text": row.canonical_text,
            "sensitivity_class": row.sensitivity_class,
            "confidence": row.confidence,
            "score": score,
            "created_at": row.created_at,
        }
        for score, row in scored[:top_k]
    ]


def encode_embedding(embedding: list[float]) -> bytes:
    return _encode_embedding(embedding)


def decode_embedding(data: bytes) -> list[float]:
    return _decode_embedding(data)

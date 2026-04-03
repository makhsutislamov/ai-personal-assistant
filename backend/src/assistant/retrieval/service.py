from __future__ import annotations

import time
from datetime import datetime, timezone, UTC

from sqlalchemy.ext.asyncio import AsyncSession

from assistant.db.vector import search_similar
from assistant.memory.embeddings import generate_embedding
from assistant.retrieval.reranker import combined_score
from assistant.retrieval.schemas import (
    RetrievalFilter,
    RetrievalItem,
    RetrievalResult,
    SourceAttribution,
)
from assistant.telemetry.setup import get_meter, get_tracer

_tracer = get_tracer("retrieval")
_meter = get_meter("retrieval")
_retrieval_latency = _meter.create_histogram(
    "assistant.retrieval.latency",
    description="Retrieval query latency in ms",
    unit="ms",
)


async def query(
    session: AsyncSession,
    text: str,
    filters: RetrievalFilter | None = None,
    top_k: int = 10,
) -> RetrievalResult:
    """Retrieve and rank relevant memory records for the given query."""
    with _tracer.start_as_current_span("retrieval.query") as span:
        span.set_attribute("top_k", top_k)
        result = await _query(session, text, filters, top_k)
        span.set_attribute("items_returned", len(result.items))
        _retrieval_latency.record(result.query_latency_ms)
        return result


async def _query(
    session: AsyncSession,
    text: str,
    filters: RetrievalFilter | None = None,
    top_k: int = 10,
) -> RetrievalResult:
    start = time.perf_counter()

    embedding = await generate_embedding(text)

    source_type_filter = None
    if filters and filters.source_types and len(filters.source_types) == 1:
        source_type_filter = filters.source_types[0]

    raw_results = await search_similar(
        session,
        embedding,
        top_k=top_k * 2,  # Fetch more for reranking
        source_type=source_type_filter,
    )

    # Apply multi-source filter manually
    if filters and filters.source_types and len(filters.source_types) > 1:
        raw_results = [r for r in raw_results if r["source_type"] in filters.source_types]

    # Apply time filters
    if filters and filters.time_from:
        raw_results = [
            r for r in raw_results
            if r["created_at"] and r["created_at"] >= filters.time_from
        ]
    if filters and filters.time_to:
        raw_results = [
            r for r in raw_results
            if r["created_at"] and r["created_at"] <= filters.time_to
        ]

    # Rerank
    reranked = []
    for item in raw_results:
        score = combined_score(
            vector_similarity=float(item["score"]),
            created_at=item["created_at"],
            source_type=str(item["source_type"]),
        )
        reranked.append((score, item))

    reranked.sort(key=lambda x: x[0], reverse=True)

    items: list[RetrievalItem] = []
    for score, item in reranked[:top_k]:
        snippet = str(item["canonical_text"])[:300]
        created_at = item["created_at"]
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)
        source = SourceAttribution(
            memory_id=str(item["memory_id"]),
            source_type=str(item["source_type"]),
            title=str(item.get("source_ref") or ""),
            snippet=snippet,
            created_at=created_at,
        )
        items.append(
            RetrievalItem(
                memory_id=str(item["memory_id"]),
                score=score,
                snippet=snippet,
                source=source,
            )
        )

    latency_ms = (time.perf_counter() - start) * 1000
    return RetrievalResult(items=items, query_latency_ms=latency_ms)

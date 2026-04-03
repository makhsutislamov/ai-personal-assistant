from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from assistant.audit.service import log_event
from assistant.db.models import MemoryRecord
from assistant.db.vector import encode_embedding, search_similar
from assistant.memory.dedup import detect_duplicate
from assistant.memory.embeddings import generate_embedding
from assistant.memory.schemas import (
    DeleteFilter,
    DeleteResult,
    DuplicateResult,
    MemoryCandidateIn,
    MemoryCandidateOut,
    MemoryRecordOut,
)

# In-memory store for pending candidates (ask/manual mode)
_pending_candidates: dict[str, dict[str, Any]] = {}


async def create_candidate(
    session: AsyncSession,
    content: str,
    source_type: str,
    metadata: dict[str, Any] | None = None,
    sensitivity_class: str = "none",
    source_ref: str | None = None,
) -> MemoryCandidateOut:
    """Create a pending memory candidate (for ask/manual mode)."""
    candidate_id = str(uuid.uuid4())
    _pending_candidates[candidate_id] = {
        "content": content,
        "source_type": source_type,
        "source_ref": source_ref,
        "metadata": metadata or {},
        "sensitivity_class": sensitivity_class,
        "created_at": datetime.now(timezone.utc),
    }
    return MemoryCandidateOut(
        candidate_id=candidate_id,
        content=content,
        source_type=source_type,
        source_ref=source_ref,
        sensitivity_class=sensitivity_class,
        created_at=_pending_candidates[candidate_id]["created_at"],
    )


async def confirm_candidate(
    session: AsyncSession, candidate_id: str
) -> MemoryRecordOut:
    """Confirm a pending candidate and persist it as a MemoryRecord."""
    candidate = _pending_candidates.pop(candidate_id, None)
    if candidate is None:
        raise ValueError(f"Candidate {candidate_id!r} not found")

    embedding = await generate_embedding(candidate["content"])
    record = MemoryRecord(
        memory_id=str(uuid.uuid4()),
        source_type=candidate["source_type"],
        source_ref=candidate["source_ref"],
        canonical_text=candidate["content"],
        sensitivity_class=candidate["sensitivity_class"],
        embedding=encode_embedding(embedding),
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)

    await log_event(
        session=session,
        action_type="memory.create",
        target_type="memory_record",
        target_id=record.memory_id,
        before_state=None,
        after_state={"source_type": record.source_type, "content_length": len(record.canonical_text)},
    )

    return _to_out(record)


async def reject_candidate(candidate_id: str) -> None:
    """Discard a pending candidate."""
    _pending_candidates.pop(candidate_id, None)


async def auto_ingest(
    session: AsyncSession,
    content: str,
    source_type: str,
    metadata: dict[str, Any] | None = None,
    source_ref: str | None = None,
    sensitivity_class: str = "none",
) -> MemoryRecordOut:
    """Directly ingest content as a memory record (auto mode)."""
    embedding = await generate_embedding(content)
    record = MemoryRecord(
        memory_id=str(uuid.uuid4()),
        source_type=source_type,
        source_ref=source_ref,
        canonical_text=content,
        sensitivity_class=sensitivity_class,
        embedding=encode_embedding(embedding),
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)

    await log_event(
        session=session,
        action_type="memory.create",
        target_type="memory_record",
        target_id=record.memory_id,
        before_state=None,
        after_state={"source_type": source_type, "mode": "auto"},
    )

    return _to_out(record)


async def delete_memories(
    session: AsyncSession, filter: DeleteFilter
) -> DeleteResult:
    """Soft-delete memory records matching the filter."""
    now = datetime.now(timezone.utc)
    stmt = select(MemoryRecord).where(MemoryRecord.deleted_at.is_(None))

    if filter.memory_id:
        stmt = stmt.where(MemoryRecord.memory_id == filter.memory_id)
    if filter.source_type:
        stmt = stmt.where(MemoryRecord.source_type == filter.source_type)
    if filter.time_before:
        stmt = stmt.where(MemoryRecord.created_at < filter.time_before)

    result = await session.execute(stmt)
    records = result.scalars().all()

    for record in records:
        record.deleted_at = now
        await log_event(
            session=session,
            action_type="memory.delete",
            target_type="memory_record",
            target_id=record.memory_id,
            before_state={"source_type": record.source_type},
            after_state={"deleted_at": now.isoformat()},
        )

    await session.commit()
    return DeleteResult(deleted_count=len(records))


async def detect_duplicate_for_content(
    session: AsyncSession,
    content: str,
    embedding: list[float],
) -> DuplicateResult:
    """Check if a near-duplicate already exists in memory."""
    similar = await search_similar(session, embedding, top_k=5)
    # Convert to dict format expected by dedup
    records_for_dedup = []
    for item in similar:
        records_for_dedup.append({
            "memory_id": item["memory_id"],
            "canonical_text": item["canonical_text"],
            "embedding": None,  # Already scored by cosine in search_similar
        })

    # Use score-based duplicate detection
    for item in similar:
        if item["score"] >= 0.95:
            return DuplicateResult(
                is_duplicate=True,
                existing_memory_id=str(item["memory_id"]),
                similarity_score=float(item["score"]),
            )

    return DuplicateResult(is_duplicate=False)


def _to_out(record: MemoryRecord) -> MemoryRecordOut:
    return MemoryRecordOut(
        memory_id=record.memory_id,
        source_type=record.source_type,
        source_ref=record.source_ref,
        canonical_text=record.canonical_text,
        sensitivity_class=record.sensitivity_class,
        confidence=record.confidence,
        created_at=record.created_at,
    )

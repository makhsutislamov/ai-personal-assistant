from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from assistant.deps import get_session
from assistant.memory import service as memory_service
from assistant.memory.schemas import (
    DeleteFilter,
    DeleteResult,
    MemoryCandidateIn,
    MemoryCandidateOut,
    MemoryRecordOut,
)

router = APIRouter(tags=["memory"])


@router.post("/memory/candidates", response_model=MemoryCandidateOut)
async def create_candidate(
    body: MemoryCandidateIn,
    session: AsyncSession = Depends(get_session),
) -> MemoryCandidateOut:
    return await memory_service.create_candidate(
        session=session,
        content=body.content,
        source_type=body.source_type,
        source_ref=body.source_ref,
        metadata=body.metadata,
        sensitivity_class=body.sensitivity_class,
    )


@router.post("/memory/confirm", response_model=MemoryRecordOut)
async def confirm_candidate(
    candidate_id: str,
    session: AsyncSession = Depends(get_session),
) -> MemoryRecordOut:
    try:
        return await memory_service.confirm_candidate(session, candidate_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/memory/reject", status_code=204)
async def reject_candidate(candidate_id: str) -> None:
    await memory_service.reject_candidate(candidate_id)


@router.delete("/memory", response_model=DeleteResult)
async def delete_memory(
    body: DeleteFilter,
    session: AsyncSession = Depends(get_session),
) -> DeleteResult:
    return await memory_service.delete_memories(session, body)


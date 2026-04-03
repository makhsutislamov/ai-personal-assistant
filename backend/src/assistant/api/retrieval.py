from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from assistant.retrieval import service as retrieval_service
from assistant.retrieval.schemas import RetrievalFilter, RetrievalResult

router = APIRouter(tags=["retrieval"])


async def _get_session() -> AsyncSession:  # type: ignore[return]
    raise NotImplementedError("DB session dependency not configured")


class RetrievalRequest(BaseModel):
    text: str
    filters: RetrievalFilter | None = None
    top_k: int = 10


@router.post("/retrieval/query", response_model=RetrievalResult)
async def retrieval_query(
    body: RetrievalRequest,
    session: AsyncSession = Depends(_get_session),
) -> RetrievalResult:
    return await retrieval_service.query(
        session=session,
        text=body.text,
        filters=body.filters,
        top_k=body.top_k,
    )


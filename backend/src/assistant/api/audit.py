from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from assistant.audit import service as audit_service
from assistant.audit.schemas import AuditEventOut, AuditQuery
from assistant.db.models import AuditEvent

router = APIRouter(tags=["audit"])


async def _get_session() -> AsyncSession:  # pragma: no cover
    raise NotImplementedError("Wire up real session factory at startup")


@router.get("/v1/audit/events", response_model=list[AuditEventOut])
async def list_audit_events(
    actor: str | None = None,
    action_type: str | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    session: AsyncSession = Depends(_get_session),
) -> list[AuditEventOut]:
    stmt = select(AuditEvent).order_by(AuditEvent.created_at.desc())
    if actor:
        stmt = stmt.where(AuditEvent.actor == actor)
    if action_type:
        stmt = stmt.where(AuditEvent.action_type == action_type)
    if target_type:
        stmt = stmt.where(AuditEvent.target_type == target_type)
    if target_id:
        stmt = stmt.where(AuditEvent.target_id == target_id)
    result = await session.execute(stmt)
    rows = result.scalars().all()
    out = []
    for row in rows:
        created = row.created_at if hasattr(row.created_at, "year") else row.created_at
        out.append(
            AuditEventOut(
                event_id=row.event_id,
                actor=row.actor,
                action_type=row.action_type,
                target_type=row.target_type,
                target_id=row.target_id,
                before_hash=row.before_hash,
                after_hash=row.after_hash,
                created_at=created,
            )
        )
    return out


@router.get("/v1/audit/integrity")
async def check_integrity(
    session: AsyncSession = Depends(_get_session),
) -> dict[str, object]:
    return await audit_service.verify_chain(session)


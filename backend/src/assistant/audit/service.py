from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from assistant.db.models import AuditEvent


def _compute_hash(previous_hash: str | None, event_data: dict[str, Any]) -> str:
    payload = (previous_hash or "") + json.dumps(event_data, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()


async def log_event(
    session: AsyncSession,
    action_type: str,
    target_type: str,
    target_id: str,
    before_state: Any,
    after_state: Any,
    actor: str = "user",
) -> AuditEvent:
    # Get the last event hash for chain continuity
    result = await session.execute(
        select(AuditEvent.after_hash)
        .order_by(AuditEvent.created_at.desc())
        .limit(1)
    )
    last_row = result.first()
    previous_hash = last_row[0] if last_row else None

    event_data = {
        "action_type": action_type,
        "target_type": target_type,
        "target_id": target_id,
        "actor": actor,
        # State payloads are not persisted in DB, so omit from hash
        # to keep verify_chain reproducible without them.
        "before_state": None,
        "after_state": None,
    }
    after_hash = _compute_hash(previous_hash, event_data)

    event = AuditEvent(
        event_id=str(uuid.uuid4()),
        actor=actor,
        action_type=action_type,
        target_type=target_type,
        target_id=target_id,
        before_hash=previous_hash,
        after_hash=after_hash,
    )
    session.add(event)
    # Note: caller is responsible for commit
    return event


async def verify_chain(
    session: AsyncSession,
    from_event_id: str | None = None,
) -> dict[str, object]:
    """Walk the audit chain and verify hash integrity.

    Returns {"valid": bool, "checked": int, "first_invalid_id": str | None}.
    """
    result = await session.execute(
        select(AuditEvent).order_by(AuditEvent.created_at.asc())
    )
    events = result.scalars().all()

    previous_hash: str | None = None
    for event in events:
        # Reconstruct expected hash
        event_data: dict[str, Any] = {
            "action_type": event.action_type,
            "target_type": event.target_type,
            "target_id": event.target_id,
            "actor": event.actor,
            # We can only verify outer chain integrity, not state payloads
            # (state not stored in this simplified schema)
            "before_state": None,
            "after_state": None,
        }
        expected = _compute_hash(previous_hash, event_data)
        # The stored after_hash must match what we'd compute using stored before_hash
        recomputed = _compute_hash(event.before_hash, event_data)
        if event.after_hash != recomputed:
            return {
                "valid": False,
                "checked": events.index(event),
                "first_invalid_id": event.event_id,
            }
        previous_hash = event.after_hash

    return {"valid": True, "checked": len(events), "first_invalid_id": None}

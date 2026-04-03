from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from assistant.audit.service import log_event
from assistant.db.models import TaskRecord
from assistant.tasks.schemas import TaskOut
from assistant.tasks.state_machine import is_valid_transition

_HIGH_IMPACT_KEYWORDS = ["delete", "remove", "cancel", "terminate", "destroy", "drop"]


def _is_high_impact(objective: str) -> bool:
    lo = objective.lower()
    return any(kw in lo for kw in _HIGH_IMPACT_KEYWORDS)


def _to_out(record: TaskRecord, requires_confirmation: bool = False) -> TaskOut:
    return TaskOut(
        task_id=record.task_id,
        objective=record.objective,
        owner=record.owner,
        due_at=record.due_at,
        status=record.status,
        blocked_reason=record.blocked_reason,
        completion_outcome=record.completion_outcome,
        requires_confirmation=requires_confirmation,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


async def create_task(
    session: AsyncSession,
    objective: str,
    due_context: str | None = None,
    owner: str = "user",
) -> TaskOut:
    requires_confirmation = _is_high_impact(objective)

    record = TaskRecord(
        task_id=str(uuid.uuid4()),
        objective=objective,
        owner=owner,
        status="created",
    )
    session.add(record)
    await session.flush()

    await log_event(
        session=session,
        action_type="task.create",
        target_type="task_record",
        target_id=record.task_id,
        before_state=None,
        after_state={"objective": objective, "status": "created"},
    )
    await session.commit()
    await session.refresh(record)

    return _to_out(record, requires_confirmation=requires_confirmation)


async def update_task(
    session: AsyncSession,
    task_id: str,
    status: str,
    outcome: str | None = None,
    blocked_reason: str | None = None,
) -> TaskOut:
    result = await session.execute(
        select(TaskRecord).where(TaskRecord.task_id == task_id)
    )
    record = result.scalar_one_or_none()
    if record is None:
        raise ValueError(f"Task {task_id!r} not found")

    if not is_valid_transition(record.status, status):
        raise ValueError(
            f"Invalid transition: {record.status!r} → {status!r}"
        )

    old_status = record.status
    record.status = status
    if outcome:
        record.completion_outcome = outcome
    if blocked_reason:
        record.blocked_reason = blocked_reason

    await log_event(
        session=session,
        action_type="task.update",
        target_type="task_record",
        target_id=task_id,
        before_state={"status": old_status},
        after_state={"status": status},
    )
    await session.commit()
    await session.refresh(record)

    return _to_out(record)


async def list_tasks(
    session: AsyncSession,
    status_filter: str | None = None,
) -> list[TaskOut]:
    stmt = select(TaskRecord)
    if status_filter:
        stmt = stmt.where(TaskRecord.status == status_filter)
    result = await session.execute(stmt)
    return [_to_out(r) for r in result.scalars().all()]

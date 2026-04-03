from __future__ import annotations

import statistics
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from assistant.db.models import TaskRecord
from assistant.evaluation.schemas import TaskCompletionMetrics


async def compute_task_completion(
    session: AsyncSession,
    time_from: datetime | None = None,
    time_to: datetime | None = None,
) -> TaskCompletionMetrics:
    """Compute task completion rate and cycle times from task records."""
    stmt = select(TaskRecord)
    if time_from:
        stmt = stmt.where(TaskRecord.created_at >= time_from)
    if time_to:
        stmt = stmt.where(TaskRecord.created_at <= time_to)
    result = await session.execute(stmt)
    tasks = result.scalars().all()

    if not tasks:
        return TaskCompletionMetrics(rate=0.0, by_type={}, median_cycle_time_seconds=None)

    completed = [t for t in tasks if t.status == "completed"]
    rate = len(completed) / len(tasks)

    # by_type: group by objective prefix (simplified: first word)
    type_total: dict[str, int] = {}
    type_completed: dict[str, int] = {}
    for t in tasks:
        kind = t.objective.split()[0].lower() if t.objective else "other"
        type_total[kind] = type_total.get(kind, 0) + 1
        if t.status == "completed":
            type_completed[kind] = type_completed.get(kind, 0) + 1
    by_type = {
        k: type_completed.get(k, 0) / type_total[k]
        for k in type_total
    }

    # Cycle time: updated_at - created_at for completed tasks
    cycle_times: list[float] = []
    for t in completed:
        created = t.created_at
        updated = t.updated_at
        if isinstance(created, str):
            created = datetime.fromisoformat(created)
        if isinstance(updated, str):
            updated = datetime.fromisoformat(updated)
        if updated and created:
            cycle_times.append((updated - created).total_seconds())

    median_cycle = statistics.median(cycle_times) if cycle_times else None

    return TaskCompletionMetrics(
        rate=rate,
        by_type=by_type,
        median_cycle_time_seconds=median_cycle,
    )

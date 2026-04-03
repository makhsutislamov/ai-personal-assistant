from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from assistant.db.models import Base, TaskRecord
from assistant.evaluation.tasks import compute_task_completion


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()


def _add_task(session, objective: str, status: str) -> TaskRecord:
    t = TaskRecord(
        task_id=str(uuid.uuid4()),
        objective=objective,
        status=status,
    )
    session.add(t)
    return t


async def test_completion_rate_all_completed(session: AsyncSession):
    _add_task(session, "Send report", "completed")
    _add_task(session, "Send email", "completed")
    await session.commit()

    metrics = await compute_task_completion(session)
    assert metrics.rate == 1.0


async def test_completion_rate_mixed(session: AsyncSession):
    _add_task(session, "Send report", "completed")
    _add_task(session, "Buy stuff", "created")
    await session.commit()

    metrics = await compute_task_completion(session)
    assert metrics.rate == 0.5


async def test_completion_rate_none(session: AsyncSession):
    _add_task(session, "Do something", "created")
    await session.commit()

    metrics = await compute_task_completion(session)
    assert metrics.rate == 0.0


async def test_empty_tasks(session: AsyncSession):
    metrics = await compute_task_completion(session)
    assert metrics.rate == 0.0
    assert metrics.median_cycle_time_seconds is None


async def test_by_type_grouping(session: AsyncSession):
    _add_task(session, "send email", "completed")
    _add_task(session, "send report", "created")
    _add_task(session, "buy groceries", "completed")
    await session.commit()

    metrics = await compute_task_completion(session)
    # "send" group has 1 completed / 2 total = 0.5
    assert abs(metrics.by_type.get("send", 0) - 0.5) < 0.01
    # "buy" group has 1 completed / 1 total = 1.0
    assert metrics.by_type.get("buy", 0) == 1.0

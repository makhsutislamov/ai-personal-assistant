from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from assistant.db.engine import create_engine, create_session_factory
from assistant.db.migrations import run_migrations
from assistant.tasks import engine as task_engine


@pytest.fixture
async def db_session():
    engine = create_engine(":memory:")
    await run_migrations(engine)
    factory = create_session_factory(engine)
    async with factory() as session:
        yield session
    await engine.dispose()


async def test_create_task(db_session: AsyncSession):
    task = await task_engine.create_task(db_session, "Write unit tests")
    assert task.task_id
    assert task.status == "created"
    assert task.objective == "Write unit tests"


async def test_normal_task_no_confirmation_required(db_session: AsyncSession):
    task = await task_engine.create_task(db_session, "Write documentation")
    assert task.requires_confirmation is False


async def test_high_impact_task_requires_confirmation(db_session: AsyncSession):
    task = await task_engine.create_task(db_session, "Delete all production data")
    assert task.requires_confirmation is True


async def test_valid_state_transition(db_session: AsyncSession):
    task = await task_engine.create_task(db_session, "Fix the bug")
    updated = await task_engine.update_task(db_session, task.task_id, "in_progress")
    assert updated.status == "in_progress"


async def test_complete_task(db_session: AsyncSession):
    task = await task_engine.create_task(db_session, "Send report")
    in_progress = await task_engine.update_task(db_session, task.task_id, "in_progress")  # noqa: F841
    completed = await task_engine.update_task(
        db_session, task.task_id, "completed", outcome="Report sent successfully"
    )
    assert completed.status == "completed"
    assert completed.completion_outcome == "Report sent successfully"


async def test_invalid_state_transition_raises(db_session: AsyncSession):
    task = await task_engine.create_task(db_session, "Test task")
    with pytest.raises(ValueError, match="Invalid transition"):
        await task_engine.update_task(db_session, task.task_id, "completed")


async def test_completed_task_cannot_transition(db_session: AsyncSession):
    task = await task_engine.create_task(db_session, "Test task")
    await task_engine.update_task(db_session, task.task_id, "in_progress")
    await task_engine.update_task(db_session, task.task_id, "completed", outcome="done")
    with pytest.raises(ValueError):
        await task_engine.update_task(db_session, task.task_id, "in_progress")


async def test_list_tasks_with_filter(db_session: AsyncSession):
    await task_engine.create_task(db_session, "Task 1")
    t2 = await task_engine.create_task(db_session, "Task 2")
    await task_engine.update_task(db_session, t2.task_id, "in_progress")

    in_progress = await task_engine.list_tasks(db_session, status_filter="in_progress")
    assert len(in_progress) == 1
    assert in_progress[0].task_id == t2.task_id


async def test_list_all_tasks(db_session: AsyncSession):
    await task_engine.create_task(db_session, "Task A")
    await task_engine.create_task(db_session, "Task B")
    tasks = await task_engine.list_tasks(db_session)
    assert len(tasks) == 2

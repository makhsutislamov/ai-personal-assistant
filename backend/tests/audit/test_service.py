from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from assistant.db.models import Base
from assistant.audit import service as audit_service


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()


async def test_log_event_creates_record(session: AsyncSession):
    event = await audit_service.log_event(
        session, "create", "task", "t-1", None, {"title": "Test"}
    )
    await session.commit()
    assert event.event_id is not None
    assert event.action_type == "create"
    assert event.target_type == "task"
    assert event.target_id == "t-1"
    assert event.after_hash


async def test_log_event_chains_hashes(session: AsyncSession):
    e1 = await audit_service.log_event(session, "create", "task", "t-1", None, {})
    await session.commit()
    e2 = await audit_service.log_event(session, "update", "task", "t-1", {}, {"done": True})
    await session.commit()
    # Second event's before_hash must equal first event's after_hash
    assert e2.before_hash == e1.after_hash


async def test_verify_chain_valid_after_events(session: AsyncSession):
    await audit_service.log_event(session, "create", "memory", "m-1", None, {})
    await session.commit()
    await audit_service.log_event(session, "delete", "memory", "m-1", {}, None)
    await session.commit()
    result = await audit_service.verify_chain(session)
    assert result["valid"] is True
    assert result["checked"] == 2
    assert result["first_invalid_id"] is None


async def test_verify_chain_empty_is_valid(session: AsyncSession):
    result = await audit_service.verify_chain(session)
    assert result["valid"] is True
    assert result["checked"] == 0


async def test_verify_chain_detects_tamper(session: AsyncSession):
    from sqlalchemy import select
    from assistant.db.models import AuditEvent

    await audit_service.log_event(session, "create", "task", "t-1", None, {})
    await session.commit()
    await audit_service.log_event(session, "update", "task", "t-1", {}, {})
    await session.commit()

    # Tamper: corrupt the after_hash of the second event
    result = await session.execute(
        select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(1)
    )
    latest = result.scalar_one()
    latest.after_hash = "deadbeef" * 8
    await session.commit()

    chain = await audit_service.verify_chain(session)
    assert chain["valid"] is False
    assert chain["first_invalid_id"] is not None

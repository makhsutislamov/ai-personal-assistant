from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from assistant.db.engine import create_engine, create_session_factory
from assistant.db.migrations import run_migrations
from assistant.db.models import SourceDocument
from assistant.policy.consent import check_source_consent


@pytest.fixture
async def db_session():
    engine = create_engine(":memory:")
    await run_migrations(engine)
    factory = create_session_factory(engine)
    async with factory() as session:
        yield session
    await engine.dispose()


async def test_no_docs_returns_false(db_session: AsyncSession):
    result = await check_source_consent(db_session, "apple_notes")
    assert result is False


async def test_granted_consent_returns_true(db_session: AsyncSession):
    doc = SourceDocument(
        source_id=str(uuid.uuid4()),
        external_ref="note://root",
        consent_snapshot="granted",
        sync_status="synced",
    )
    db_session.add(doc)
    await db_session.commit()

    result = await check_source_consent(db_session, "apple_notes")
    assert result is True


async def test_disconnected_source_returns_false(db_session: AsyncSession):
    doc = SourceDocument(
        source_id=str(uuid.uuid4()),
        external_ref="note://root",
        consent_snapshot="granted",
        sync_status="disconnected",
    )
    db_session.add(doc)
    await db_session.commit()

    result = await check_source_consent(db_session, "apple_notes")
    assert result is False

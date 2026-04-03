from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from assistant.db.engine import create_engine, create_session_factory
from assistant.db.migrations import run_migrations
from assistant.integrations.apple_notes import connector as apple_connector
from assistant.integrations.apple_notes.schemas import RawNote


@pytest.fixture
async def db_session():
    engine = create_engine(":memory:")
    await run_migrations(engine)
    factory = create_session_factory(engine)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest.fixture(autouse=True)
def mock_embedding():
    with patch(
        "assistant.memory.service.generate_embedding",
        new=AsyncMock(return_value=[0.1, 0.2, 0.3]),
    ):
        yield


async def test_connect_success(db_session: AsyncSession):
    with patch(
        "assistant.integrations.apple_notes.connector.fetch_folders",
        return_value=["Personal", "Work"],
    ):
        result = await apple_connector.connect(db_session)

    assert result.connected is True
    assert result.folder_count == 2


async def test_connect_failure_on_applescript_error(db_session: AsyncSession):
    with patch(
        "assistant.integrations.apple_notes.connector.fetch_folders",
        side_effect=RuntimeError("AppleScript not available"),
    ):
        result = await apple_connector.connect(db_session)

    assert result.connected is False
    assert "AppleScript" in result.message


async def test_sync_creates_memory_records(db_session: AsyncSession):
    notes = [
        RawNote(note_id="note-1", title="Meeting Notes", body="Discussed project launch"),
        RawNote(note_id="note-2", title="Ideas", body="New feature ideas"),
    ]

    with patch(
        "assistant.integrations.apple_notes.connector.fetch_notes",
        return_value=notes,
    ):
        result = await apple_connector.sync_notes(db_session)

    assert result.created == 2
    assert result.errors == []


async def test_sync_handles_note_failure(db_session: AsyncSession):
    notes = [
        RawNote(note_id="bad-note", title="", body=""),
    ]

    with patch(
        "assistant.integrations.apple_notes.connector.fetch_notes",
        return_value=notes,
    ), patch(
        "assistant.memory.service.generate_embedding",
        new=AsyncMock(side_effect=Exception("embedding failed")),
    ):
        result = await apple_connector.sync_notes(db_session)

    assert len(result.errors) > 0


async def test_disconnect_revokes_consent(db_session: AsyncSession):
    with patch(
        "assistant.integrations.apple_notes.connector.fetch_folders",
        return_value=[],
    ):
        await apple_connector.connect(db_session)

    await apple_connector.disconnect(db_session)
    # After disconnect, connect status should be revoked
    from sqlalchemy import select
    from assistant.db.models import SourceDocument

    result = await db_session.execute(
        select(SourceDocument).where(SourceDocument.external_ref == "apple_notes://root")
    )
    doc = result.scalar_one_or_none()
    assert doc is not None
    assert doc.sync_status == "disconnected"

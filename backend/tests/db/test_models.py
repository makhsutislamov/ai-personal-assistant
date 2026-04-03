from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from assistant.db.engine import create_engine, create_session_factory
from assistant.db.migrations import run_migrations
from assistant.db.models import (
    AuditEvent,
    BrowserCapture,
    ConversationMessage,
    ConversationSession,
    MemoryRecord,
    NoteItem,
    RoutingEvent,
    SourceDocument,
    TaskRecord,
    UserSettings,
)


@pytest.fixture
async def db_session():
    engine = create_engine(":memory:")
    await run_migrations(engine)
    factory = create_session_factory(engine)
    async with factory() as session:
        yield session
    await engine.dispose()


async def test_memory_record_insert_query(db_session: AsyncSession):
    record = MemoryRecord(
        memory_id=str(uuid.uuid4()),
        source_type="conversation",
        canonical_text="Test memory content",
        sensitivity_class="none",
        confidence=0.9,
    )
    db_session.add(record)
    await db_session.commit()

    result = await db_session.execute(
        select(MemoryRecord).where(MemoryRecord.source_type == "conversation")
    )
    rows = result.scalars().all()
    assert len(rows) == 1
    assert rows[0].canonical_text == "Test memory content"


async def test_source_document_insert_query(db_session: AsyncSession):
    doc = SourceDocument(
        source_id=str(uuid.uuid4()),
        external_ref="note://abc123",
        title="My Note",
        sync_status="synced",
    )
    db_session.add(doc)
    await db_session.commit()

    result = await db_session.execute(
        select(SourceDocument).where(SourceDocument.title == "My Note")
    )
    row = result.scalar_one()
    assert row.sync_status == "synced"


async def test_browser_capture_insert_query(db_session: AsyncSession):
    capture = BrowserCapture(
        capture_id=str(uuid.uuid4()),
        url="https://example.com",
        title="Example Page",
        selected_text="Some selected text",
    )
    db_session.add(capture)
    await db_session.commit()

    result = await db_session.execute(
        select(BrowserCapture).where(BrowserCapture.url == "https://example.com")
    )
    row = result.scalar_one()
    assert row.title == "Example Page"


async def test_task_record_insert_query(db_session: AsyncSession):
    task = TaskRecord(
        task_id=str(uuid.uuid4()),
        objective="Send report",
        status="created",
    )
    db_session.add(task)
    await db_session.commit()

    result = await db_session.execute(
        select(TaskRecord).where(TaskRecord.status == "created")
    )
    rows = result.scalars().all()
    assert len(rows) == 1
    assert rows[0].objective == "Send report"


async def test_conversation_session_and_messages(db_session: AsyncSession):
    session_id = str(uuid.uuid4())
    conv = ConversationSession(session_id=session_id, topic_tags="[]")
    db_session.add(conv)

    msg = ConversationMessage(
        message_id=str(uuid.uuid4()),
        session_id=session_id,
        role="user",
        content="Hello",
    )
    db_session.add(msg)
    await db_session.commit()

    result = await db_session.execute(
        select(ConversationMessage).where(ConversationMessage.session_id == session_id)
    )
    rows = result.scalars().all()
    assert len(rows) == 1
    assert rows[0].role == "user"


async def test_note_item_insert(db_session: AsyncSession):
    note = NoteItem(
        note_id=str(uuid.uuid4()),
        source="apple_notes",
        content="Meeting notes content",
        tags='["work"]',
    )
    db_session.add(note)
    await db_session.commit()

    result = await db_session.execute(
        select(NoteItem).where(NoteItem.source == "apple_notes")
    )
    row = result.scalar_one()
    assert row.content == "Meeting notes content"


async def test_routing_event_insert(db_session: AsyncSession):
    event = RoutingEvent(
        event_id=str(uuid.uuid4()),
        request_id=str(uuid.uuid4()),
        sensitivity_decision="clean",
        chosen_model="azure_openai",
        latency_ms=123.4,
    )
    db_session.add(event)
    await db_session.commit()

    result = await db_session.execute(
        select(RoutingEvent).where(RoutingEvent.chosen_model == "azure_openai")
    )
    row = result.scalar_one()
    assert row.latency_ms == pytest.approx(123.4)


async def test_audit_event_insert(db_session: AsyncSession):
    ev = AuditEvent(
        event_id=str(uuid.uuid4()),
        actor="user",
        action_type="memory.create",
        target_type="memory_record",
        target_id=str(uuid.uuid4()),
        after_hash="abc123",
    )
    db_session.add(ev)
    await db_session.commit()

    result = await db_session.execute(
        select(AuditEvent).where(AuditEvent.action_type == "memory.create")
    )
    row = result.scalar_one()
    assert row.after_hash == "abc123"


async def test_user_settings_insert(db_session: AsyncSession):
    setting = UserSettings(key="memory_mode", value="ask")
    db_session.add(setting)
    await db_session.commit()

    result = await db_session.execute(
        select(UserSettings).where(UserSettings.key == "memory_mode")
    )
    row = result.scalar_one()
    assert row.value == "ask"

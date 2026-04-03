from __future__ import annotations

import pytest
from sqlalchemy import inspect, text

from assistant.db.engine import create_engine
from assistant.db.migrations import run_migrations
from assistant.db.models import Base


async def test_all_tables_created():
    engine = create_engine(":memory:")
    await run_migrations(engine)

    expected_tables = {
        "memory_records",
        "source_documents",
        "browser_captures",
        "task_records",
        "conversation_sessions",
        "conversation_messages",
        "note_items",
        "routing_events",
        "audit_events",
        "user_settings",
    }

    async with engine.connect() as conn:
        table_names = await conn.run_sync(
            lambda sync_conn: {t for t in inspect(sync_conn).get_table_names()}
        )

    assert expected_tables <= table_names
    await engine.dispose()


async def test_migrations_idempotent():
    """Running migrations twice should not raise."""
    engine = create_engine(":memory:")
    await run_migrations(engine)
    await run_migrations(engine)  # second run must not fail
    await engine.dispose()

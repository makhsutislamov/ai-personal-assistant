from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from assistant.config import Settings
from assistant.db.engine import create_engine, create_session_factory
from assistant.db.migrations import run_migrations
from assistant.integrations.browser.handler import handle_capture
from assistant.integrations.browser.schemas import BrowserCapturePayload


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
        new=AsyncMock(return_value=[0.1, 0.2]),
    ):
        yield


def _payload(**kwargs) -> BrowserCapturePayload:
    defaults = {
        "url": "https://example.com",
        "title": "Example Page",
        "selected_text": "Some text",
    }
    defaults.update(kwargs)
    return BrowserCapturePayload(**defaults)


async def test_auto_mode_immediately_saves(db_session: AsyncSession):
    settings = Settings(memory_mode="auto")
    result = await handle_capture(db_session, _payload(), settings)

    assert result.success is True
    assert result.memory_id is not None
    assert result.candidate_id is None


async def test_ask_mode_creates_candidate(db_session: AsyncSession):
    settings = Settings(memory_mode="ask")
    result = await handle_capture(db_session, _payload(), settings)

    assert result.success is True
    assert result.candidate_id is not None
    assert result.memory_id is None


async def test_manual_mode_no_memory_write(db_session: AsyncSession):
    settings = Settings(memory_mode="manual")
    result = await handle_capture(db_session, _payload(), settings)

    assert result.success is True
    assert result.memory_id is None
    assert result.candidate_id is None
    assert "manual mode" in result.message


async def test_full_page_content_included(db_session: AsyncSession):
    settings = Settings(memory_mode="auto")
    payload = _payload(full_page_content="Full page text here")
    result = await handle_capture(db_session, payload, settings)

    assert result.success is True
    assert result.memory_id is not None

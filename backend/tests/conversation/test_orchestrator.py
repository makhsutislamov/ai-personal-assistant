from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from assistant.config import Settings
from assistant.conversation import orchestrator
from assistant.conversation.schemas import ChatRequest
from assistant.db.engine import create_engine, create_session_factory
from assistant.db.migrations import run_migrations


@pytest.fixture
async def db_session():
    engine = create_engine(":memory:")
    await run_migrations(engine)
    factory = create_session_factory(engine)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest.fixture(autouse=True)
def mock_deps():
    with patch(
        "assistant.retrieval.service.generate_embedding",
        new=AsyncMock(return_value=[0.1, 0.2]),
    ), patch(
        "assistant.routing.providers.ollama.complete",
        new=AsyncMock(return_value=("Test response from model", 10.0)),
    ):
        yield


async def test_respond_returns_chat_response(db_session: AsyncSession):
    settings = Settings(routing_preference="ollama")
    request = ChatRequest(message="What is the weather?")

    response = await orchestrator.respond(db_session, request, settings)

    assert response.session_id
    assert response.response == "Test response from model"
    assert response.model_used == "llama3"


async def test_respond_creates_new_session_when_none(db_session: AsyncSession):
    settings = Settings(routing_preference="ollama")
    request = ChatRequest(session_id=None, message="Hello")

    response = await orchestrator.respond(db_session, request, settings)
    assert response.session_id is not None


async def test_respond_reuses_existing_session(db_session: AsyncSession):
    settings = Settings(routing_preference="ollama")
    req1 = ChatRequest(message="First message")
    resp1 = await orchestrator.respond(db_session, req1, settings)

    req2 = ChatRequest(session_id=resp1.session_id, message="Second message")
    resp2 = await orchestrator.respond(db_session, req2, settings)

    assert resp1.session_id == resp2.session_id


async def test_grounded_response_when_context_retrieved(db_session: AsyncSession):
    """When memory items exist, response should be marked grounded."""
    import uuid as _uuid

    from assistant.db.models import MemoryRecord
    from assistant.db.vector import encode_embedding

    record = MemoryRecord(
        memory_id=str(_uuid.uuid4()),
        source_type="conversation",
        canonical_text="relevant context content",
        embedding=encode_embedding([0.1, 0.2]),
    )
    db_session.add(record)
    await db_session.commit()

    settings = Settings(routing_preference="ollama")
    response = await orchestrator.respond(
        db_session, ChatRequest(message="relevant context"), settings
    )
    assert response.grounded is True
    assert len(response.sources) > 0


async def test_ungrounded_when_no_context(db_session: AsyncSession):
    """When no memory items, response should not be grounded."""
    settings = Settings(routing_preference="ollama")
    response = await orchestrator.respond(
        db_session, ChatRequest(message="unknown topic"), settings
    )
    assert response.grounded is False

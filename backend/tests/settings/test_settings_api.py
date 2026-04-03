from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from assistant.api.settings import (
    SettingPatch,
    _upsert,
    get_settings,
    set_memory_mode,
    set_model_routing,
    set_retrieval,
)
from assistant.db.models import Base


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()


async def test_get_settings_empty(session: AsyncSession):
    result = await get_settings(session)
    assert result.settings == {}


async def test_upsert_and_get(session: AsyncSession):
    await _upsert(session, "memory_mode", "auto")
    result = await get_settings(session)
    assert result.settings["memory_mode"] == "auto"


async def test_upsert_updates_existing(session: AsyncSession):
    await _upsert(session, "memory_mode", "auto")
    await _upsert(session, "memory_mode", "ask")
    result = await get_settings(session)
    assert result.settings["memory_mode"] == "ask"


async def test_set_memory_mode_valid(session: AsyncSession):
    result = await set_memory_mode(SettingPatch(value="manual"), session)
    assert result.settings["memory_mode"] == "manual"


async def test_set_memory_mode_invalid(session: AsyncSession):
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        await set_memory_mode(SettingPatch(value="badvalue"), session)
    assert exc_info.value.status_code == 422


async def test_set_model_routing_valid(session: AsyncSession):
    result = await set_model_routing(SettingPatch(value="ollama"), session)
    assert result.settings["routing_preference"] == "ollama"


async def test_set_model_routing_invalid(session: AsyncSession):
    from fastapi import HTTPException
    with pytest.raises(HTTPException):
        await set_model_routing(SettingPatch(value="invalid"), session)


async def test_set_retrieval_valid(session: AsyncSession):
    result = await set_retrieval(SettingPatch(value="10"), session)
    assert result.settings["retrieval_top_k"] == "10"


async def test_set_retrieval_invalid_non_integer(session: AsyncSession):
    from fastapi import HTTPException
    with pytest.raises(HTTPException):
        await set_retrieval(SettingPatch(value="notanint"), session)

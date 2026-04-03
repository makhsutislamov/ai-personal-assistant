from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from assistant.audit import service as audit_service
from assistant.db.models import UserSettings

router = APIRouter(tags=["settings"])

_ALLOWED_KEYS = {
    "memory_mode",
    "routing_preference",
    "retrieval_top_k",
    "sensitive_local_only",
}


async def _get_session() -> AsyncSession:  # pragma: no cover
    raise NotImplementedError("Wire up real session factory at startup")


class SettingsResponse(BaseModel):
    settings: dict[str, str]


class SettingPatch(BaseModel):
    value: str


async def _upsert(
    session: AsyncSession,
    key: str,
    value: str,
    actor: str = "user",
) -> None:
    result = await session.execute(
        select(UserSettings).where(UserSettings.key == key)
    )
    row = result.scalar_one_or_none()
    before = row.value if row else None
    if row:
        row.value = value
        row.updated_by = actor
    else:
        row = UserSettings(key=key, value=value, updated_by=actor)
        session.add(row)
    await audit_service.log_event(
        session, "update", "settings", key, before, value, actor=actor
    )
    await session.commit()


@router.get("/v1/settings", response_model=SettingsResponse)
async def get_settings(
    session: AsyncSession = Depends(_get_session),
) -> SettingsResponse:
    result = await session.execute(select(UserSettings))
    rows = result.scalars().all()
    return SettingsResponse(settings={r.key: r.value for r in rows})


@router.patch("/v1/settings/memory-mode", response_model=SettingsResponse)
async def set_memory_mode(
    body: SettingPatch,
    session: AsyncSession = Depends(_get_session),
) -> SettingsResponse:
    if body.value not in ("ask", "auto", "manual"):
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="memory_mode must be ask|auto|manual")
    await _upsert(session, "memory_mode", body.value)
    return await get_settings(session)


@router.patch("/v1/settings/model-routing", response_model=SettingsResponse)
async def set_model_routing(
    body: SettingPatch,
    session: AsyncSession = Depends(_get_session),
) -> SettingsResponse:
    if body.value not in ("azure_openai", "ollama", "auto"):
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="routing_preference must be azure_openai|ollama|auto")
    await _upsert(session, "routing_preference", body.value)
    return await get_settings(session)


@router.patch("/v1/settings/retrieval", response_model=SettingsResponse)
async def set_retrieval(
    body: SettingPatch,
    session: AsyncSession = Depends(_get_session),
) -> SettingsResponse:
    try:
        int(body.value)
    except ValueError:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="retrieval_top_k must be an integer")
    await _upsert(session, "retrieval_top_k", body.value)
    return await get_settings(session)


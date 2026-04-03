from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from assistant.config import Settings, get_settings
from assistant.integrations.apple_notes import connector as apple_notes_connector
from assistant.integrations.apple_notes.schemas import ConnectionResult, SyncResult
from assistant.integrations.browser.handler import handle_capture
from assistant.integrations.browser.schemas import BrowserCapturePayload, CaptureResult

router = APIRouter(tags=["integrations"])


async def _get_session() -> AsyncSession:  # type: ignore[return]
    raise NotImplementedError("DB session dependency not configured")


class SyncRequest(BaseModel):
    folder_filter: list[str] | None = None


class IntegrationStatus(BaseModel):
    apple_notes: str
    browser: str


@router.post("/integrations/apple-notes/connect", response_model=ConnectionResult)
async def apple_notes_connect(
    session: AsyncSession = Depends(_get_session),
) -> ConnectionResult:
    return await apple_notes_connector.connect(session)


@router.post("/integrations/apple-notes/sync", response_model=SyncResult)
async def apple_notes_sync(
    body: SyncRequest,
    session: AsyncSession = Depends(_get_session),
) -> SyncResult:
    return await apple_notes_connector.sync_notes(session, body.folder_filter)


@router.delete("/integrations/apple-notes/disconnect", status_code=204)
async def apple_notes_disconnect(
    session: AsyncSession = Depends(_get_session),
) -> None:
    await apple_notes_connector.disconnect(session)


@router.get("/integrations/status", response_model=IntegrationStatus)
async def integrations_status() -> IntegrationStatus:
    return IntegrationStatus(apple_notes="unknown", browser="unknown")


@router.post("/integrations/browser-capture", response_model=CaptureResult)
async def browser_capture(
    body: BrowserCapturePayload,
    session: AsyncSession = Depends(_get_session),
    settings: Settings = Depends(get_settings),
) -> CaptureResult:
    return await handle_capture(session, body, settings)


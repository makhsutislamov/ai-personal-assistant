from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from assistant.config import Settings
from assistant.db.models import BrowserCapture
from assistant.integrations.browser.schemas import BrowserCapturePayload, CaptureResult
from assistant.memory import service as memory_service


async def handle_capture(
    session: AsyncSession,
    payload: BrowserCapturePayload,
    settings: Settings,
) -> CaptureResult:
    """Process an incoming browser capture according to the current memory mode."""
    # Persist the raw capture record
    capture = BrowserCapture(
        capture_id=str(uuid.uuid4()),
        url=payload.url,
        title=payload.title,
        selected_text=payload.selected_text,
        capture_mode=payload.capture_mode,
    )
    session.add(capture)
    await session.flush()

    content_parts = [f"URL: {payload.url}", f"Title: {payload.title}"]
    if payload.selected_text:
        content_parts.append(f"Selected text: {payload.selected_text}")
    if payload.full_page_content:
        content_parts.append(f"Full page: {payload.full_page_content[:2000]}")
    content = "\n".join(content_parts)

    mode = settings.memory_mode

    if mode == "auto":
        record = await memory_service.auto_ingest(
            session=session,
            content=content,
            source_type="browser_capture",
            source_ref=payload.url,
        )
        await session.commit()
        return CaptureResult(
            success=True, memory_id=record.memory_id, message="Captured and saved"
        )

    elif mode == "ask":
        candidate = await memory_service.create_candidate(
            session=session,
            content=content,
            source_type="browser_capture",
            source_ref=payload.url,
        )
        await session.commit()
        return CaptureResult(
            success=True,
            candidate_id=candidate.candidate_id,
            message="Capture pending confirmation",
        )

    else:  # manual — save raw capture only, no memory write
        await session.commit()
        return CaptureResult(
            success=True, message="Capture recorded (manual mode — no memory write)"
        )

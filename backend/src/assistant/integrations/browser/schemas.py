from __future__ import annotations

from pydantic import BaseModel


class BrowserCapturePayload(BaseModel):
    url: str
    title: str
    selected_text: str
    full_page_content: str | None = None
    capture_mode: str = "selection"


class CaptureResult(BaseModel):
    success: bool
    candidate_id: str | None = None
    memory_id: str | None = None
    message: str

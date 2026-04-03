from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class RawNote(BaseModel):
    note_id: str
    title: str
    body: str
    modified_at: datetime | None = None
    folder: str | None = None


class SyncResult(BaseModel):
    created: int
    updated: int
    deleted: int
    errors: list[str]


class ConnectionResult(BaseModel):
    connected: bool
    message: str
    folder_count: int = 0

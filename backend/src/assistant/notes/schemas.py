from __future__ import annotations

from pydantic import BaseModel


class GeneratedNotes(BaseModel):
    summary: str
    decisions: list[str]
    action_items: list[str]
    open_questions: list[str]
    suggested_tags: list[str]

from __future__ import annotations

from pydantic import BaseModel


class EvalCase(BaseModel):
    query: str
    expected_memory_ids: list[str]


class RecallMetrics(BaseModel):
    precision: float
    recall: float
    f1: float
    by_source: dict[str, float]


class TaskCompletionMetrics(BaseModel):
    rate: float
    by_type: dict[str, float]
    median_cycle_time_seconds: float | None

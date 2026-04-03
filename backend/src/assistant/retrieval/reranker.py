from __future__ import annotations

import math
from datetime import datetime, timezone, UTC


def _recency_decay(created_at: datetime | str, half_life_days: float = 30.0) -> float:
    """Exponential decay based on age. Returns 1.0 for new items, decays toward 0."""
    if isinstance(created_at, str):
        created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    now = datetime.now(UTC)
    age_days = (now - created_at).total_seconds() / 86400
    return math.exp(-age_days * math.log(2) / half_life_days)


_SOURCE_PRIORITY: dict[str, float] = {
    "conversation": 1.0,
    "apple_notes": 0.9,
    "browser_capture": 0.8,
    "manual": 0.85,
}


def combined_score(
    vector_similarity: float,
    created_at: datetime | str,
    source_type: str,
) -> float:
    """Combine vector similarity, recency, and source priority weights."""
    recency = _recency_decay(created_at)
    source_priority = _SOURCE_PRIORITY.get(source_type, 0.7)
    return vector_similarity * 0.7 + recency * 0.2 + source_priority * 0.1

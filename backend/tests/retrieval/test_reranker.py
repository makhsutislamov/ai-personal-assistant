from __future__ import annotations

from datetime import datetime, timedelta, timezone, UTC

from assistant.retrieval.reranker import combined_score


def test_score_range():
    now = datetime.now(UTC)
    score = combined_score(
        vector_similarity=0.9,
        created_at=now,
        source_type="conversation",
    )
    assert 0.0 <= score <= 1.0


def test_higher_vector_sim_gives_higher_score():
    now = datetime.now(UTC)
    high = combined_score(0.9, now, "conversation")
    low = combined_score(0.3, now, "conversation")
    assert high > low


def test_older_item_scores_lower():
    now = datetime.now(UTC)
    old = now - timedelta(days=90)
    new_score = combined_score(0.8, now, "conversation")
    old_score = combined_score(0.8, old, "conversation")
    assert new_score > old_score


def test_unknown_source_gets_default_priority():
    now = datetime.now(UTC)
    score = combined_score(0.8, now, "unknown_source")
    # Should not raise, should return a numeric value
    assert isinstance(score, float)

from __future__ import annotations

from assistant.memory.dedup import detect_duplicate


def test_exact_duplicate():
    records = [
        {"memory_id": "id-1", "canonical_text": "Hello world", "embedding": None},
    ]
    is_dup, eid, score = detect_duplicate("Hello world", [1.0, 0.0], records)
    assert is_dup is True
    assert eid == "id-1"
    assert score == 1.0


def test_near_duplicate_by_cosine():
    records = [
        {"memory_id": "id-2", "canonical_text": "Different text", "embedding": [0.99, 0.01]},
    ]
    is_dup, eid, score = detect_duplicate("Some query", [1.0, 0.0], records, similarity_threshold=0.95)
    # cos([1,0], [0.99, 0.01]) ≈ 0.99 → above threshold
    assert is_dup is True
    assert eid == "id-2"
    assert score >= 0.95


def test_not_duplicate():
    records = [
        {"memory_id": "id-3", "canonical_text": "Completely different", "embedding": [0.0, 1.0]},
    ]
    is_dup, eid, score = detect_duplicate("Hello world", [1.0, 0.0], records)
    assert is_dup is False
    assert eid is None


def test_empty_records():
    is_dup, eid, score = detect_duplicate("Hello", [1.0], [])
    assert is_dup is False
    assert score == 0.0

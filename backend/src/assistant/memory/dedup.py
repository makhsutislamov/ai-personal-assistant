from __future__ import annotations

import hashlib


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def detect_duplicate(
    content: str,
    candidate_embedding: list[float],
    existing_records: list[dict[str, object]],
    similarity_threshold: float = 0.95,
) -> tuple[bool, str | None, float]:
    """Check for exact hash match or near-duplicate by cosine similarity.

    Returns (is_duplicate, existing_memory_id, similarity_score).
    """
    from assistant.db.vector import cosine_similarity

    content_hash = _content_hash(content)

    for record in existing_records:
        # Exact content check
        if _content_hash(str(record.get("canonical_text", ""))) == content_hash:
            return True, str(record["memory_id"]), 1.0

        # Near-duplicate by cosine similarity
        emb = record.get("embedding")
        if emb is not None and isinstance(emb, list):
            score = cosine_similarity(candidate_embedding, emb)
            if score >= similarity_threshold:
                return True, str(record["memory_id"]), score

    return False, None, 0.0

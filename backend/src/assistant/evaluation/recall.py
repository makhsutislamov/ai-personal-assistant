from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from assistant.evaluation.schemas import EvalCase, RecallMetrics
from assistant.memory.embeddings import generate_embedding
from assistant.db.vector import search_similar


async def evaluate_recall(
    session: AsyncSession,
    eval_set: list[EvalCase],
    top_k: int = 10,
) -> RecallMetrics:
    """For each eval case, run retrieval and compare against expected ground truth."""
    if not eval_set:
        return RecallMetrics(precision=0.0, recall=0.0, f1=0.0, by_source={})

    true_positives = 0
    total_retrieved = 0
    total_relevant = 0
    source_tp: dict[str, int] = {}
    source_relevant: dict[str, int] = {}

    for case in eval_set:
        embedding = await generate_embedding(case.query)
        results = await search_similar(session, embedding, top_k=top_k)
        retrieved_ids = {r["memory_id"] for r in results}
        expected_ids = set(case.expected_memory_ids)

        tp = len(retrieved_ids & expected_ids)
        true_positives += tp
        total_retrieved += len(retrieved_ids)
        total_relevant += len(expected_ids)

        # Per-source breakdown
        for r in results:
            src = r.get("source_type", "unknown")
            if r["memory_id"] in expected_ids:
                source_tp[src] = source_tp.get(src, 0) + 1
        for eid in expected_ids:
            # We don't have source for expected IDs directly — track by query
            source_relevant["all"] = source_relevant.get("all", 0) + 1

    precision = true_positives / total_retrieved if total_retrieved else 0.0
    recall = true_positives / total_relevant if total_relevant else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )

    by_source = {
        src: source_tp[src] / source_relevant.get("all", 1)
        for src in source_tp
    }

    return RecallMetrics(precision=precision, recall=recall, f1=f1, by_source=by_source)

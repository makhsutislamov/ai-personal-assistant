from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from assistant.evaluation import recall as recall_eval
from assistant.evaluation import tasks as task_eval
from assistant.evaluation.schemas import EvalCase, RecallMetrics, TaskCompletionMetrics

router = APIRouter(tags=["evaluation"])


async def _get_session() -> AsyncSession:  # pragma: no cover
    raise NotImplementedError("Wire up real session factory at startup")


@router.post("/v1/evaluation/recall", response_model=RecallMetrics)
async def run_recall_eval(
    eval_set: list[EvalCase],
    session: AsyncSession = Depends(_get_session),
) -> RecallMetrics:
    return await recall_eval.evaluate_recall(session, eval_set)


@router.get("/v1/evaluation/task-completion", response_model=TaskCompletionMetrics)
async def get_task_completion(
    session: AsyncSession = Depends(_get_session),
) -> TaskCompletionMetrics:
    return await task_eval.compute_task_completion(session)

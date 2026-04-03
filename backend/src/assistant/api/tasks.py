from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from assistant.deps import get_session
from assistant.tasks import engine as task_engine
from assistant.tasks.schemas import TaskOut

router = APIRouter(tags=["tasks"])


class CreateTaskRequest(BaseModel):
    objective: str
    due_context: str | None = None


class UpdateTaskRequest(BaseModel):
    status: str
    outcome: str | None = None
    blocked_reason: str | None = None


@router.post("/tasks", response_model=TaskOut, status_code=201)
async def create_task(
    body: CreateTaskRequest,
    session: AsyncSession = Depends(get_session),
) -> TaskOut:
    return await task_engine.create_task(
        session=session,
        objective=body.objective,
        due_context=body.due_context,
    )


@router.patch("/tasks/{task_id}", response_model=TaskOut)
async def update_task(
    task_id: str,
    body: UpdateTaskRequest,
    session: AsyncSession = Depends(get_session),
) -> TaskOut:
    try:
        return await task_engine.update_task(
            session=session,
            task_id=task_id,
            status=body.status,
            outcome=body.outcome,
            blocked_reason=body.blocked_reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/tasks", response_model=list[TaskOut])
async def list_tasks(
    status: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[TaskOut]:
    return await task_engine.list_tasks(session=session, status_filter=status)


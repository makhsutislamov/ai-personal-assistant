from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from app.models.schemas import SessionResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("", response_model=SessionResponse)
async def create_session(request=None):

    state = _get_state(request)
    session_id = state.session_store.create_session()
    return SessionResponse(session_id=session_id)


@router.delete("/{session_id}", status_code=200)
async def delete_session(session_id: str, request=None):

    state = _get_state(request)
    if not state.session_store.session_exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    state.session_store.delete_session(session_id)
    return {"status": "deleted"}


def _get_state(request):
    from app.main import get_app_state

    if request is None:
        raise HTTPException(status_code=500, detail="No request context")
    return get_app_state(request.app)

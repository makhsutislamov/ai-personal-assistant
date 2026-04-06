from __future__ import annotations

import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.orchestrator import Orchestrator
from app.models.schemas import UserMessagePayload

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    from app.main import get_app_state

    state = get_app_state(websocket.app)
    auth_token = websocket.query_params.get("token") or websocket.headers.get("x-auth-token")

    if state.auth_token and auth_token != state.auth_token:
        await websocket.close(code=4001)
        return

    await websocket.accept()

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                payload = UserMessagePayload.model_validate_json(raw)
            except Exception as exc:
                await websocket.send_text(
                    json.dumps({"type": "error", "code": "invalid_payload", "message": str(exc)})
                )
                continue

            orchestrator: Orchestrator = state.orchestrator
            async for event in await orchestrator.handle_message(
                payload.session_id, payload.content
            ):
                await websocket.send_text(event.model_dump_json())

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as exc:
        logger.exception("Unexpected error in WebSocket handler")
        try:
            await websocket.send_text(
                json.dumps({"type": "error", "code": "server_error", "message": str(exc)})
            )
        except Exception:
            pass

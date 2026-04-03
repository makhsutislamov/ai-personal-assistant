from __future__ import annotations

import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from assistant.telemetry.setup import get_tracer


class TelemetryMiddleware(BaseHTTPMiddleware):
    """Create an OpenTelemetry span for every HTTP request."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self._tracer = get_tracer()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        span_name = f"{request.method} {request.url.path}"

        with self._tracer.start_as_current_span(span_name) as span:
            span.set_attribute("http.method", request.method)
            span.set_attribute("http.route", str(request.url.path))
            span.set_attribute("request.id", request_id)

            start = time.perf_counter()
            response = await call_next(request)
            latency_ms = (time.perf_counter() - start) * 1000

            span.set_attribute("http.status_code", response.status_code)
            span.set_attribute("http.latency_ms", round(latency_ms, 2))

        response.headers["x-request-id"] = request_id
        return response

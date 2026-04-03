from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from assistant.telemetry.setup import setup_telemetry


@pytest.fixture(autouse=True)
def init_telemetry():
    setup_telemetry(export_to_console=False)


def _make_app() -> FastAPI:
    from assistant.telemetry.middleware import TelemetryMiddleware

    app = FastAPI()
    app.add_middleware(TelemetryMiddleware)

    @app.get("/ping")
    def ping():
        return {"pong": True}

    return app


def test_middleware_adds_request_id_header():
    client = TestClient(_make_app())
    response = client.get("/ping")
    assert response.status_code == 200
    assert "x-request-id" in response.headers


def test_middleware_preserves_provided_request_id():
    client = TestClient(_make_app())
    response = client.get("/ping", headers={"x-request-id": "my-id-123"})
    assert response.headers["x-request-id"] == "my-id-123"


def test_middleware_creates_span_without_error():
    """Just verify no exception is raised during span creation."""
    client = TestClient(_make_app())
    response = client.get("/ping")
    assert response.json() == {"pong": True}

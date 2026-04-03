from __future__ import annotations


def test_setup_telemetry_creates_providers():
    from opentelemetry import trace, metrics
    from assistant.telemetry.setup import setup_telemetry, get_tracer, get_meter

    setup_telemetry(export_to_console=False)

    tracer = get_tracer()
    meter = get_meter()

    assert tracer is not None
    assert meter is not None


def test_get_tracer_returns_tracer():
    from opentelemetry.sdk.trace import Tracer
    from assistant.telemetry.setup import get_tracer

    tracer = get_tracer("test-service")
    assert tracer is not None


def test_get_meter_returns_meter():
    from assistant.telemetry.setup import get_meter

    meter = get_meter("test-service")
    assert meter is not None


def test_tracer_creates_spans():
    from assistant.telemetry.setup import setup_telemetry, get_tracer
    from opentelemetry import trace

    setup_telemetry()
    tracer = get_tracer("span-test")
    with tracer.start_as_current_span("test-span") as span:
        assert span is not None
        span.set_attribute("key", "value")
    # No exception = success

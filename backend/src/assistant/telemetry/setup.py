from __future__ import annotations

from opentelemetry import metrics, trace
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
)

_SERVICE_NAME = "ai-personal-assistant"
_tracer_provider: TracerProvider | None = None
_meter_provider: MeterProvider | None = None


def setup_telemetry(export_to_console: bool = False) -> None:
    """Initialise global TracerProvider and MeterProvider.

    When *export_to_console* is False (default) exports are suppressed — spans
    are still recorded in-memory for unit tests and structured logging hooks.
    """
    global _tracer_provider, _meter_provider

    tp = TracerProvider()
    if export_to_console:
        tp.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    _tracer_provider = tp
    trace.set_tracer_provider(tp)

    readers = []
    if export_to_console:
        readers.append(PeriodicExportingMetricReader(ConsoleMetricExporter()))
    mp = MeterProvider(metric_readers=readers)
    _meter_provider = mp
    metrics.set_meter_provider(mp)


def get_tracer(name: str = _SERVICE_NAME) -> trace.Tracer:
    """Return a tracer from the configured provider."""
    return trace.get_tracer(name)


def get_meter(name: str = _SERVICE_NAME) -> metrics.Meter:
    """Return a meter from the configured provider."""
    return metrics.get_meter(name)

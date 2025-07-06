from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.propagate import extract, inject
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from fastapi import FastAPI
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry._logs import set_logger_provider
from opentelemetry.instrumentation.fastapi import OpenTelemetryMiddleware
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

import os


def setup_otel(app: FastAPI):
    provider = TracerProvider()
    trace.set_tracer_provider(provider)

    exporter = OTLPSpanExporter(
        endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"),
        headers={
            "Authorization": f"Bearer {os.getenv('NEW_RELIC_LICENSE_KEY')}",
        },
    )

    span_processor = BatchSpanProcessor(exporter)
    provider.add_span_processor(span_processor)

    FastAPIInstrumentor.instrument_app(app)
    app.add_middleware(OpenTelemetryMiddleware)


def setup_metrics(app: FastAPI):
    metric_exporter = OTLPMetricExporter(
        endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"),
        headers={"api-key": f"{os.getenv('NEW_RELIC_LICENSE_KEY')}"},
    )

    reader = PeriodicExportingMetricReader(metric_exporter)
    provider = MeterProvider(metric_readers=[reader])

    return provider


def setup_logging():
    provider = LoggerProvider()
    set_logger_provider(provider)

    LoggingInstrumentor().instrument(set_logging_format=True)

    exporter = OTLPLogExporter(
        endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"),
        headers={"Authorization": f"Bearer {os.getenv('NEW_RELIC_LICENSE_KEY')}"},
    )

    log_record_processor = BatchLogRecordProcessor(exporter)
    provider.add_log_record_processor(log_record_processor)

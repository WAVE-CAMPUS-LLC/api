from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.asgi import OpenTelemetryMiddleware
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk._logs import LoggingHandler, LoggerProvider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor

import os


def setup_otel(app):
    resource = Resource(
        attributes={"service.name": "wave-api", "deployment.environment": "production"}
    )

    # Tracing setup
    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)
    otlp_exporter = OTLPSpanExporter()
    provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

    # Logging setup (simplified without OTLP exporter)
    log_provider = LoggerProvider(resource=resource)
    LoggingInstrumentor().instrument(set_logging_format=True)

    # Add ASGI middleware instrumentation
    app.add_middleware(OpenTelemetryMiddleware)

    # Attach FastAPI instrumentation
    FastAPIInstrumentor.instrument_app(app)

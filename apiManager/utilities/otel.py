from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.propagate import extract, inject
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry._logs import set_logger_provider

import os


def setup_otel(app, service_name="WAVE. API"):
    resource = Resource.create(
        {
            SERVICE_NAME: service_name,
            "deployment.environment": os.getenv("OTEL_ENVIRONMENT", "production"),
        }
    )
    provider = TracerProvider(resource=resource)

    trace.set_tracer_provider(provider)

    exporter = OTLPSpanExporter(
        endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"),
        headers={
            "Authorization": f"Bearer {os.getenv('GRAFANA_API_KEY')}",
        },
    )

    span_processor = BatchSpanProcessor(exporter)
    provider.add_span_processor(span_processor)

    FastAPIInstrumentor.instrument_app(app)


def setup_logging():
    provider = LoggerProvider()
    set_logger_provider(provider)

    LoggingInstrumentor().instrument(set_logging_format=True)

    exporter = OTLPLogExporter(
        endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"),
        headers={"Authorization": f"Bearer {os.getenv('GRAFANA_API_KEY')}"},
    )

    log_record_processor = BatchLogRecordProcessor(exporter)
    provider.add_log_record_processor(log_record_processor)

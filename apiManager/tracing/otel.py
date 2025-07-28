import logging
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource, SERVICE_NAME

logger = logging.getLogger("otel")
logger.setLevel(logging.INFO)


def configure_tracing(service_name: str, api_key: str):
    if not api_key:
        logger.warning("New Relic API key is missing — telemetry will not be exported.")
        return

    resource = Resource(attributes={SERVICE_NAME: service_name})
    provider = TracerProvider(resource=resource)

    try:
        exporter = OTLPSpanExporter(
            endpoint="https://otlp.nr-data.net:4318/v1/traces",
            headers={"api-key": "d76869a8d0e3b4186f985c1546eaf7acFFFFNRAL"},
        )
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        logger.info(f"Telemetry configured for service: {service_name}")
    except Exception as e:
        logger.error(f"Failed to configure OpenTelemetry: {e}")

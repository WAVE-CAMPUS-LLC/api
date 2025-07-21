from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource, SERVICE_NAME


def configure_tracing(service_name: str, api_key: str):
    print(f"Using API Key: {'SET' if api_key else 'MISSING'}")
    resource = Resource(attributes={SERVICE_NAME: service_name})
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(
        endpoint="https://otlp.nr-data.net/v1/traces",
        headers={"api-key": "2d694e90d7d1002abfe6c0246aa3fe2bFFFFNRAL"},
    )

    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

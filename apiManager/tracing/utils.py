# apiManager/tracing/utils.py

from opentelemetry import trace
from opentelemetry.trace import SpanKind
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any

tracer = trace.get_tracer(__name__)


def record_trace(
    name: str,
    user_id: Optional[str] = None,
    type_: str = "action",
    from_page: Optional[str] = None,
    to_page: Optional[str] = None,
    latency_ms: Optional[float] = None,
    attributes: Optional[Dict[str, Any]] = None,
    timestamp: Optional[str] = None,
):
    start_time = (
        datetime.fromisoformat(timestamp).replace(tzinfo=timezone.utc)
        if timestamp
        else datetime.now(timezone.utc)
    )

    with tracer.start_as_current_span(
        f"{type_.upper()} - {name}",
        kind=SpanKind.CLIENT,
        start_time=int(start_time.timestamp() * 1000),
    ) as span:
        if user_id:
            span.set_attribute("user.id", str(user_id))
        span.set_attribute("trace.type", type_)
        span.set_attribute("trace.from_page", from_page or "unknown")
        span.set_attribute("trace.to_page", to_page or "unknown")
        span.set_attribute("trace.latency_ms", latency_ms or 0)

        if attributes:
            for key, value in attributes.items():
                if isinstance(value, dict):
                    value = json.dumps(value)
                span.set_attribute(f"attr.{key}", value)

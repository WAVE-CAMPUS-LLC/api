from typing import Optional, Dict, List, Any
from channels.db import database_sync_to_async
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
import bleach
import uuid
from datetime import datetime, timezone
from opentelemetry import trace
from opentelemetry.trace import SpanKind
from pydantic import BaseModel
import json
from channels.db import database_sync_to_async

from otelManagementApp.models import TelemetryEvent


router = APIRouter()
tracer = trace.get_tracer(__name__)


class Trace(BaseModel):
    timestamp: str
    type: str
    name: str
    user_id: Optional[str] = None
    from_page: Optional[str] = None
    to_page: Optional[str] = None
    latency_ms: Optional[float] = None
    attributes: Optional[Dict[str, Any]] = None


class TraceBatch(BaseModel):
    traces: List[Trace]


@database_sync_to_async
def create_telemetry_event(item: Trace):
    TelemetryEvent.objects.create(
        timestamp=datetime.fromisoformat(item.timestamp),
        trace_type=item.type,
        name=item.name,
        user_id=item.user_id,
        from_page=item.from_page,
        to_page=item.to_page,
        latency_ms=item.latency_ms,
        attributes=item.attributes,
    )


@router.get("/trace/health")
async def trace_health():
    from apiManager.tracing.utils import record_trace

    record_trace(
        name="telemetry_healthcheck", type_="internal", attributes={"env": "production"}
    )
    return {"status": "telemetry ok"}


@router.post("/trace/batch")
async def receive_trace_batch(batch: TraceBatch, request: Request):
    for item in batch.traces:
        # Save to DB
        await create_telemetry_event(item)

        # Still send to OpenTelemetry
        start_time = datetime.fromisoformat(item.timestamp).replace(tzinfo=timezone.utc)
        duration = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

        with tracer.start_as_current_span(
            f"{item.type.upper()} - {item.name}",
            kind=SpanKind.CLIENT,
            start_time=int(start_time.timestamp() * 1000000),  # Convert to nanoseconds
        ) as span:
            if item.user_id:
                span.set_attribute("user.id", str(item.user_id))
            span.set_attribute("trace.type", item.type)
            span.set_attribute("trace.from_page", item.from_page or "unknown")
            span.set_attribute("trace.to_page", item.to_page or "unknown")
            span.set_attribute("trace.latency_ms", item.latency_ms or duration)

            if item.attributes:
                for key, value in item.attributes.items():
                    if isinstance(value, dict):
                        value = json.dumps(value)
                    span.set_attribute(f"attr.{key}", value)

    return {"status": "ok"}

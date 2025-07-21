from typing import Optional, Dict, List, Any
from channels.db import database_sync_to_async
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
import bleach
import uuid
from datetime import datetime
from opentelemetry import trace
from opentelemetry.trace import SpanKind
from pydantic import BaseModel


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


@router.post("/trace/batch")
async def receive_trace_batch(batch: TraceBatch, request: Request):
    for item in batch.traces:
        with tracer.start_as_current_span(
            f"{item.type.upper()} - {item.name}", kind=SpanKind.CLIENT
        ) as span:
            if item.user_id:
                span.set_attribute("user.id", str(item.user_id))
            span.set_attribute("trace.type", item.type)
            span.set_attribute("trace.from_page", item.from_page or "unknown")
            span.set_attribute("trace.to_page", item.to_page or "unknown")
            span.set_attribute("trace.latency_ms", item.latency_ms or 0)
            if item.attributes:
                for key, value in item.attributes.items():
                    span.set_attribute(f"attr.{key}", value)
    return {"status": "ok"}

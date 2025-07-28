import uuid
import datetime
from django.db import models
from django.utils.timezone import now


# Create your models here.
class TelemetryEvent(models.Model):
    otelId = models.UUIDField(
        default=uuid.uuid4, editable=False, unique=True, primary_key=True
    )
    timestamp = models.DateTimeField(default=now)
    trace_type = models.CharField(max_length=64)
    name = models.CharField(max_length=255)

    user_id = models.CharField(max_length=255, null=True, blank=True)
    from_page = models.CharField(max_length=255, null=True, blank=True)
    to_page = models.CharField(max_length=255, null=True, blank=True)
    latency_ms = models.FloatField(null=True, blank=True)

    attributes = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(default=now)

    def __str__(self):
        return f"TelemetryEvent: {self.name} - {self.trace_type}"

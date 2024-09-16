import uuid
from django.db import models
from django.utils.translation import gettext as _
from django.contrib.auth import get_user_model
from django.conf import settings


class FriendRequest(models.Model):
    STATUS_CHOICES = [
        ("sent", "Sent"),
        ("received", "Received"),
        ("pending", "Pending"),
        ("declined", "Declined"),
        ("accepted", "Accepted"),
    ]

    requestId = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, unique=True
    )

    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="sent_requests", on_delete=models.CASCADE
    )
    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="received_requests",
        on_delete=models.CASCADE,
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="pending",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("sender", "receiver")
        verbose_name = "Friend Request"
        verbose_name_plural = "Friend Requests"

    def __str__(self):
        return f"{self.sender.username} -> {self.receiver.username} ({self.status})"

    def acceptRequest(self):
        self.status = "accepted"
        self.save()

    def declineRequest(self):
        self.status = "declined"
        self.save()

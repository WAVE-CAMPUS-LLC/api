import uuid
from django.db import models
from django.conf import settings
from authenticationApp.models import CustomUser

# Create your models here.


class Notification(models.Model):
    NOTIFICATION_TYPE_CHOICES = [
        ("FRIEND_REQUEST", "Friend Request"),
        ("FRIEND_REQUEST_ACCEPTED", "Friend Request Accepted"),
        ("FRIEND_REQUEST_REJECTED", "Friend Request Rejected"),
        ("FRIEND_REQUEST_CANCELLED", "Friend Request Cancelled"),
        ("FRIEND_REQUEST_EXPIRED", "Friend Request Expired"),
        ("friend_connected", "Friend Connected"),
        ("event_attended", "Event Attended"),
        ("event_rsvp", "Event RSVP"),
        ("crew_joined", "Crew Joined"),
        ("college_joined", "College Joined"),
        ("college_left", "College Left"),
    ]
    notificationId = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, unique=True
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_sent",
        null=True,
        blank=True,
    )
    type = models.CharField(max_length=25, choices=NOTIFICATION_TYPE_CHOICES)
    content = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        default_permissions = ()
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.recipient.username} - {self.type}"


class UserPushyTokeny(models.Model):
    user = models.OneToOneField(
        CustomUser, on_delete=models.CASCADE, to_field="user_id", db_column="user_id"
    )
    token = models.TextField()
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.token}"

    class Meta:
        default_permissions = ()
        ordering = ["-updated_at"]
        verbose_name = "User Push Token"
        verbose_name_plural = "User Push Tokens"


class PushNotification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=255, default="WAVE.")
    message = models.TextField()
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    navigate_to = models.CharField(max_length=255, null=True, blank=True)
    params = models.JSONField(default=dict, blank=True, null=True)

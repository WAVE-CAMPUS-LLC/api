import re
import uuid
from django.db import models
from django.utils.translation import gettext as _
from django.contrib.auth import get_user_model
from django.contrib.postgres.indexes import GinIndex, OpClass
from django.conf import settings


class FriendRequest(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("declined", "Declined"),
        ("accepted", "Accepted"),
        ("canceled", "Canceled"),
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
        constraints = [
            models.UniqueConstraint(
                fields=["sender", "receiver"],
                condition=models.Q(status__in=["pending", "accepted"]),
                name="unique_active_request",
            )
        ]
        verbose_name = "Friend Request"
        verbose_name_plural = "Friend Requests"
        default_permissions = ()
        app_label = "socialApp"

    def __str__(self):
        return f"{self.sender.username} -> {self.receiver.username} ({self.status})"

    def accept_request(self):
        self.status = "accepted"
        self.save()
        return self

    def decline_request(self):
        self.status = "declined"
        self.save()
        return self


class Crew(models.Model):
    crewId = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, unique=True, db_index=True
    )
    name = models.CharField(
        _("Name your crew"), max_length=100, null=False, blank=False, db_index=True
    )
    bio = models.TextField(
        _("Describe your crew"), null=True, blank=True, max_length=150
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="crews_created",  # Updated for clarity
    )
    created_at = models.DateTimeField(auto_now_add=True)
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL, through="CrewMember", related_name="member_of_crews"
    )

    class Meta:
        default_permissions = ()
        app_label = "socialApp"
        indexes = [
            GinIndex(
                [OpClass("name", name="gin_trgm_ops")],
                name="name_gin_trgm_idx",
            ),
            GinIndex(
                [OpClass("crewId", name="gin_trgm_ops")],
                name="crewId_gin_trgm_idx",
            ),
        ]

    def __str__(self):
        return self.name


class CrewMember(models.Model):
    crew = models.ForeignKey(
        Crew, on_delete=models.CASCADE, related_name="crew_members"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="crew_memberships",
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    is_admin = models.BooleanField(default=False)

    class Meta:
        unique_together = ("crew", "user")
        default_permissions = ()
        app_label = "socialApp"

    def __str__(self):
        return f"{self.user.username} in {self.crew.name}"

    def make_admin(self):
        self.is_admin = True
        self.save()

    def remove_admin(self):
        self.is_admin = False
        self.save()


class CrewRequest(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("declined", "Declined"),
        ("accepted", "Accepted"),
    ]

    requestId = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, unique=True
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="sent_crew", on_delete=models.CASCADE
    )
    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="received_crew", on_delete=models.CASCADE
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="pending",
    )
    crew = models.ForeignKey(Crew, on_delete=models.CASCADE, related_name="requests")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("sender", "receiver", "crew")
        verbose_name = "Crew Request"
        verbose_name_plural = "Crew Requests"
        default_permissions = ()
        app_label = "socialApp"

    def __str__(self):
        return f"{self.sender.username} -> {self.receiver.username} ({self.status})"

    def accept_request(self):
        self.status = "accepted"
        self.save()
        return self

    def decline_request(self):
        self.status = "declined"
        self.save()
        return self


class GoWithRequest(models.Model):
    requestId = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, unique=True
    )

    event = models.ForeignKey(
        "eventManagementApp.Event",
        on_delete=models.CASCADE,
        related_name="go_with_requests",
    )

    sender = models.ForeignKey(
        "accountManagementApp.UserProfile",
        related_name="sent_go_with",
        on_delete=models.CASCADE,
    )
    receiver = models.ForeignKey(
        "accountManagementApp.UserProfile",
        related_name="received_go_with",
        on_delete=models.CASCADE,
    )

    status = models.CharField(
        max_length=10,
        choices=[
            ("pending", "Pending"),
            ("declined", "Declined"),
            ("accepted", "Accepted"),
            ("cancelled", "Cancelled"),
        ],
        default="Pending",
    )

    class Meta:
        app_label = "socialApp"

    def __str__(self):
        return f"{self.sender.username} -> {self.receiver.username}"

    def accept_go_with(self):
        self.status = "accepted"
        self.save()
        return self

    def decline_go_with(self):
        self.status = "declined"
        self.save()
        return self

    def cancel_go_with(self):
        self.status = "cancelled"
        self.save()
        return self

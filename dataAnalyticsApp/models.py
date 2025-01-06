from django.db import models
from django.contrib.auth import get_user_model
import datetime
import uuid

from eventManagementApp.models import Event
from authenticationApp.models import CustomUser

# Create your models here.
User = get_user_model()


class GuestUser(models.Model):
    guestId = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, unique=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Guest User {self.guest_id}"



class EventInteractionControl(models.Model):
    INTERACTION_TYPES = [
        ("Clicked", "Clicked"),
        ("Viewed", "Viewed"),
        ("Liked", "Liked"),
        ("Shared", "Shared"),
        ("Ticket Scanned", "Ticket Scanned"),
        ("Ticket Invalid", "Ticket Invalid"),
        ("Ticket Valid", "Ticket Valid"),
        ("Ticket Cancelled", "Ticket Cancelled"),
        ("Ticket Refunded", "Ticket Refunded"),
        ("Ticket Transferred", "Ticket Transferred"),
        ("Ticket Resold", "Ticket Resold"),
    ]

    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, blank=True, null=True)
    guest = models.ForeignKey(
        GuestUser, on_delete=models.CASCADE, blank=True, null=True
    )
    interaction_type = models.CharField(
        max_length=50, default="Clicked", choices=INTERACTION_TYPES
    )
    timestamp = models.DateTimeField(auto_now_add=True)  # Removed the `default` option
    duration = models.FloatField(
        null=True,
        blank=True,
        help_text="Time in seconds the user stayed on the event.",
        default=0,
    )
    date = models.DateField(
        auto_now_add=True, help_text="Date of the interaction."
    )  # Removed the `default` option

    def __str__(self):
        return f"{self.interaction_type} on {self.event} by {self.user or self.guest}"


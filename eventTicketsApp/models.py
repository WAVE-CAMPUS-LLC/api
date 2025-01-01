import uuid
from django.db import models
from django.utils.translation import gettext as _
from django.utils import timezone
from django.db.models.signals import post_save
from datetime import timedelta
from django.dispatch import receiver
from django.conf import settings
import json


# from eventManagementApp.models import Event


# Create your models here.
class Ticket(models.Model):
    TICKET_STATUS_CHOICES = [
        ("Valid", "Valid"),
        ("Scanned", "Scanned"),
        ("Invalid", "Invalid"),
    ]

    mainId = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, unique=True
    )
    ticketId = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey("authenticationApp.CustomUser", on_delete=models.CASCADE, null=True, blank=True)
    guestFirstName = models.CharField(max_length=50, blank=True, null=True)
    guestLastName = models.CharField(max_length=50, blank=True, null=True)
    guestEmail = models.EmailField(max_length=254, blank=True, null=True)
    event = models.ForeignKey("eventManagementApp.Event", on_delete=models.CASCADE)
    qrCodeData = models.TextField(blank=True, null=True)
    qrCodeImage = models.ImageField(upload_to='qr_codes/', blank=True, null=True)
    status = models.CharField(max_length=10, choices=TICKET_STATUS_CHOICES, default="Valid")
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        if self.user:
            return f"Ticket {self.ticketId} for {self.event.title} - {self.status} (User: {self.user.username})"
        return f"Ticket {self.ticketId} for {self.event.title} - {self.status} (Guest: {self.guestFirstName} {self.guestLastName})"
    
    class Meta:
        default_permissions = ()
    
    def save(self, *args, **kwargs):
        if not self.qrCodeData:
            self.qrCodeData = self.generate_qr_code_data()
        super().save(*args, **kwargs)

    def generate_qr_code_data(self):
        """
        Generates JSON data to be embedded in the QR code.
        """
        qr_data = {
            "ticketId": str(self.ticketId),
            "eventId": str(self.event.eventId),
            "guestFirstName": self.guestFirstName  if self.guestFirstName else None,
            "guestLastName": self.guestLastName if self.guestLastName else None,
            "guestEmail": self.guestEmail if self.guestEmail else None,
            "userFirstName": self.user.first_name if self.user else None,
            "userLastName": self.user.last_name if self.user else None,
            "userEmail": self.user.email if self.user else None,
        }
        return json.dumps(qr_data)

class InviteEventOption(models.Model):
    event = models.ForeignKey("eventManagementApp.Event", on_delete=models.CASCADE)
    email = models.EmailField()
    token = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, unique=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    
    class Meta:
        default_permissions = ()

    def save(self, *args, **kwargs):
        if not self.expires_at:
            time_now = timezone.now()
            delta = timedelta(hours=48)
            self.expires_at = time_now + delta
        super().save(*args, **kwargs)


class RSVPTicket(models.Model):
    event = models.ForeignKey(
        "eventManagementApp.Event",
        on_delete=models.CASCADE,
        related_name="rsvp_tickets",
    )
    email = models.EmailField(_("Email"), max_length=254)
    first_name = models.CharField(_("First Name"), max_length=50)
    last_name = models.CharField(_("Last Name"), max_length=50)
    display_on_guestlist = models.BooleanField(
        _("Do you want to be displayed on the guest list?"), default=False
    )
    created_at = models.DateTimeField(auto_now_add=True)
    ticket_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    class Meta:
        default_permissions = ()

    def __str__(self):
        return f"{self.first_name} {self.last_name} RSVP'd for {self.event.title}"
    


class PaidFreeTicket(models.Model):
    event = models.ForeignKey(
        "eventManagementApp.Event",
        verbose_name=_("Related Event"),
        on_delete=models.CASCADE,
        related_name="tickets",
    )
    ticket_id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, unique=True
    )
    stripePriceId = models.CharField(max_length=100, blank=True, null=True)
    ticket_name = models.CharField(_("Ticket Name"), max_length=50)
    
    ticket_price = models.DecimalField(
        _("Ticket Price"), max_digits=10, decimal_places=2, null=True, blank=True
    )
    ticket_description = models.TextField(
        _("Describe ticket. Are there any perks?"), max_length=300
    )
    ticket_quantity = models.PositiveIntegerField(
        _("How many tickets should be made available?"), default=1
    )
    ticket_sold = models.PositiveIntegerField(
        _("Tickets Sold"), default=0, null=True, blank=True
    )
    # created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("event", "ticket_name")
        default_permissions = ()

    def __str__(self):
        return f"{self.ticket_name} for {self.event.title}"

    def available_tickets(self):
        return self.ticket_quantity - self.ticket_sold

    def save(self, *args, **kwargs):
        if self.ticket_price is None:
            raise ValueError("Ticket price must be set for paid tickets")
        super().save(*args, **kwargs)



class UserPayment(models.Model):
    user = models.ForeignKey("authenticationApp.CustomUser", on_delete=models.CASCADE)
    success = models.BooleanField(default=False)
    stripe_checkout_id = models.CharField(max_length=500)
    
    class Meta:
        default_permissions = ()
    
    @receiver(post_save, sender="authenticationApp.CustomUser")
    def create_user_payment(sender, instance, created, **kwargs):
        if created:
            UserPayment.objects.create(user=instance)


class StripePlatformSettings(models.Model):
    salesTaxPercentage = models.DecimalField("Sales Tax Percentage", max_digits=5, decimal_places=2, default=7.0)
    salesFeeAmount = models.DecimalField("Sales Fee Amount", max_digits=10, decimal_places=2, default=0.99)
    percentageMadeAvailableToHost = models.DecimalField("Percentage Made Available to Host", max_digits=5, decimal_places=2, default=50.0)
    percentageStayingOnPlatform = models.DecimalField("Percentage Staying on Platform", max_digits=5, decimal_places=2, default=50.0)
    
    class Meta:
        default_permissions = ()
        
    def __str__(self):
        return "Stripe Platform Settings"
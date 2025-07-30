import uuid
from django.db import models
from django.utils.translation import gettext as _
from django.utils import timezone
from django.db.models.signals import post_save
from datetime import timedelta
from django.dispatch import receiver
from django.conf import settings
from django.db.models import Index
from decimal import Decimal
import json
import qrcode
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile


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
    user = models.ForeignKey(
        "authenticationApp.CustomUser", on_delete=models.CASCADE, null=True, blank=True
    )
    guestFirstName = models.CharField(max_length=50, blank=True, null=True)
    guestLastName = models.CharField(max_length=50, blank=True, null=True)
    guestEmail = models.EmailField(max_length=254, blank=True, null=True)
    event = models.ForeignKey("eventManagementApp.Event", on_delete=models.CASCADE)
    status = models.CharField(
        max_length=10, choices=TICKET_STATUS_CHOICES, default="Valid"
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    stripe_session_id = models.CharField(max_length=100, blank=True, null=True)
    
    # Individual QR code fields (restored from legacy system)
    qrCodeData = models.TextField(blank=True, null=True)
    qrCodeImage = models.FileField(upload_to='qr_codes/', blank=True, null=True)

    def __str__(self):
        if self.user:
            return f"Ticket {self.ticketId} for {self.event.title} - {self.status} (User: {self.user.username})"
        return f"Ticket {self.ticketId} for {self.event.title} - {self.status} (Guest: {self.guestFirstName} {self.guestLastName})"

    class Meta:
        default_permissions = ()
        indexes = [
            # Composite indexes for analytics queries
            Index(fields=["event", "created_at"], name="ticket_event_created_idx"),
            Index(fields=["created_at", "status"], name="ticket_created_status_idx"),
            # Index for user ticket lookups
            Index(fields=["user", "event"], name="ticket_user_event_idx"),
        ]

    def save(self, *args, **kwargs):
        """
        Generate individual QR code for this specific ticket.
        """
        # Generate QR code data if not exists
        if not self.qrCodeData:
            # Create QR code data containing ticket and event information
            qr_data = {
                "ticketId": str(self.ticketId),
                "eventId": str(self.event.eventId) if self.event else None,
                "status": self.status
            }
            self.qrCodeData = json.dumps(qr_data)
        
        # Call parent save first
        super().save(*args, **kwargs)
        
        # Generate QR code image if not exists
        if not self.qrCodeImage and self.qrCodeData:
            self.generate_qr_code_image()

    def generate_qr_code_image(self):
        """
        Generate QR code image for this specific ticket.
        """
        try:
            # Create QR code with optimal settings for ticket scanning
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=8,
                border=4,
            )
            qr.add_data(self.qrCodeData)
            qr.make(fit=True)

            # Create QR code image
            qr_image = qr.make_image(fill_color="black", back_color="white")

            # Save to BytesIO buffer
            img_io = BytesIO()
            qr_image.save(img_io, format="PNG", optimize=True)
            img_io.seek(0)

            # Generate filename
            filename = f"ticket_{self.ticketId}.png"

            # Save the image to the model field
            self.qrCodeImage.save(
                filename,
                InMemoryUploadedFile(
                    img_io,
                    None,
                    filename,
                    "image/png",
                    img_io.tell(),
                    None,
                ),
                save=True,
            )

            print(f"Generated QR code for ticket: {self.ticketId}")
            return True

        except Exception as e:
            print(f"Error generating QR code for ticket {self.ticketId}: {e}")
            return False

    # Remove universal QR code methods (these are no longer needed)
    # def get_universal_qr_code(self):
    # def get_universal_qr_code_image_url(self):
    # def has_universal_qr_access(self):


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
        _("Be displayed on guest list?"), default=False
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    ticket_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    class Meta:
        default_permissions = ()
        indexes = [
            # Composite indexes for analytics queries
            Index(fields=["event", "created_at"], name="rsvp_event_created_idx"),
            Index(
                fields=["created_at", "display_on_guestlist"],
                name="rsvp_created_display_idx",
            ),
        ]

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
        _("Tickets Sold"), default=0, null=True, blank=True, db_index=True
    )
    crew_discounted_price = models.DecimalField(
        _("Discounted Price for Crews"),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    # created_at = models.DateTimeField(auto_now_add=True)
    deadline = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("event", "ticket_name")
        default_permissions = ()
        indexes = [
            # Composite indexes for analytics queries
            Index(fields=["event", "ticket_sold"], name="paidfree_event_sold_idx"),
            Index(
                fields=["ticket_sold", "ticket_price"], name="paidfree_sold_price_idx"
            ),
        ]

    def __str__(self):
        return f"{self.ticket_name} for {self.event.title}"

    def available_tickets(self):
        return self.ticket_quantity - self.ticket_sold

    def generate_discount(self):
        if self.event.crew_discount_percentage:
            discount_amount = (
                self.ticket_price * self.event.crew_discount_percentage
            ) / 100
            self.crew_discounted_price = self.ticket_price - discount_amount
        else:
            self.crew_discounted_price = None

    def save(self, *args, **kwargs):
        if self.ticket_price is None:
            raise ValueError("Ticket price must be set for paid tickets")
        else:
            self.generate_discount()

        # Set deadline to 12 hours after event date and start time if not already set
        if not self.deadline and self.event:
            from datetime import datetime, timedelta

            event_datetime = datetime.combine(self.event.date, self.event.start_time)
            self.deadline = event_datetime + timedelta(hours=12)

        super().save(*args, **kwargs)


class UserPayment(models.Model):
    user = models.ForeignKey("authenticationApp.CustomUser", on_delete=models.CASCADE)
    success = models.BooleanField(default=False)

    class Meta:
        default_permissions = ()

    @receiver(post_save, sender="authenticationApp.CustomUser")
    def create_user_payment(sender, instance, created, **kwargs):
        if created:
            UserPayment.objects.create(user=instance)


class StripePlatformSettings(models.Model):
    salesTaxPercentage = models.DecimalField(
        "Sales Tax Percentage", max_digits=5, decimal_places=2, default=Decimal("7.0")
    )
    salesFeeAmount = models.DecimalField(
        "Sales Fee Amount", max_digits=10, decimal_places=2, default=Decimal("0.99")
    )
    percentageMadeAvailableToHost = models.DecimalField(
        "Percentage Made Available to Host",
        max_digits=5,
        decimal_places=2,
        default=Decimal("50.0"),
    )
    percentageStayingOnPlatform = models.DecimalField(
        "Percentage Staying on Platform",
        max_digits=5,
        decimal_places=2,
        default=Decimal("50.0"),
    )

    class Meta:
        default_permissions = ()

    def __str__(self):
        return "Stripe Platform Settings"

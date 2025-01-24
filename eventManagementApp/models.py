import uuid
import json
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils import timezone
from django.db.models.signals import post_save
from datetime import timedelta
from django.dispatch import receiver
from django.conf import settings
from adminDashboardApp.models import College
from socialApp.models import Crew

from collegeManagementApp.models import Organization
from eventTicketsApp.models import InviteEventOption


class HostApplication(models.Model):
    EVENT_TYPE_CHOICES = [
        ("conference", "Conference"),
        ("workshop", "Workshop"),
        ("seminar", "Seminar"),
        ("webinar", "Webinar"),
        ("networking", "Networking Event"),
    ]

    APPROVAL_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("denied", "Denied"),
    ]

    firstName = models.CharField(
        verbose_name="First Name", max_length=70, null=False, blank=False
    )
    lastName = models.CharField(
        verbose_name="Last Name", max_length=70, null=False, blank=False
    )
    email = models.EmailField(verbose_name="Email", null=False, blank=False)
    phone = models.CharField(
        verbose_name="Phone", max_length=10, null=False, blank=False
    )

    organizationName = models.CharField(
        verbose_name="Organization Name", max_length=150
    )
    organizationEmail = models.EmailField(verbose_name="Organization Email")
    organizationLocation = models.CharField(
        verbose_name="Organization Location", max_length=150
    )

    eventTypes = models.ManyToManyField(
        "EventType", related_name="applications", null=False, blank=False
    )

    approval_status = models.CharField(
        verbose_name="Approval Status",
        max_length=100,
        choices=APPROVAL_STATUS_CHOICES,
        default="pending",
    )

    eventHostedAnnually = models.CharField(
        verbose_name="How many events do you plan on hosting annually?",
        max_length=100,
        null=False,
    )
    eventPopulation = models.CharField(
        verbose_name="How many people do you expect at each event?", max_length=1000
    )

    created_at = models.DateTimeField(auto_now_add=True)
    applicationId = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, unique=True
    )

    class Meta:
        default_permissions = ()  # Removing default permissions

    def __str__(self):
        return f"{self.firstName} {self.lastName}"


class EventType(models.Model):
    name = models.CharField(max_length=50, unique=True)

    class Meta:
        default_permissions = ()  # Removing default permissions

    def __str__(self):
        return self.name


class Event(models.Model):
    STATUS_CHOICES = [
        ("incomplete", "Incomplete"),
        ("active", "Active"),
        ("live", "Live"),
        ("archived", "Archived"),
    ]

    ADMIN_STATUS_CHOICES = [
        ("paused", "Paused"),
        ("active", "Active"),
    ]

    EVENT_TYPE_CHOICES = [
        ("Social", "Social"),
        ("Academic", "Academic"),
        ("Adventure", "Adventure"),
        ("Art", "Art"),
        ("Conference", "Conference"),
        ("Dance", "Dance"),
        ("Exhibition", "Exhibition"),
        ("Fashion", "Fashion"),
        ("Fundraiser", "Fundraiser"),
        ("Greek", "Greek"),
        ("Health", "Health"),
        ("Music", "Music"),
        ("Networking", "Networking"),
        ("Photography", "Photography"),
        ("Spiritual", "Spiritual"),
        ("Sports", "Sports"),
        ("Technology", "Technology"),
        ("Volunteer", "Volunteer"),
        ("Workshop", "Workshop"),
    ]

    PRIVACY_CHOICES = [
        ("Discoverable", "Discoverable"),
        ("Invite Only", "Invite Only"),
        ("Private (College)", "Private (College)"),
        ("Private (Organization)", "Private (Organization)"),
    ]

    TICKET_CHOICES = [
        ("Paid/Free", "Paid/Free"),
        ("RSVP Required", "RSVP Required"),
        ("Invite Required", "Invite Required"),
    ]

    COUNTRY_CHOICES = [("United States", "United States")]

    STATE_CHOICES = [
        ("AL", "Alabama"),
        ("AK", "Alaska"),
        ("AZ", "Arizona"),
        ("AR", "Arkansas"),
        ("CA", "California"),
        ("CO", "Colorado"),
        ("CT", "Connecticut"),
        ("DE", "Delaware"),
        ("FL", "Florida"),
        ("GA", "Georgia"),
        ("HI", "Hawaii"),
        ("ID", "Idaho"),
        ("IL", "Illinois"),
        ("IN", "Indiana"),
        ("IA", "Iowa"),
        ("KS", "Kansas"),
        ("KY", "Kentucky"),
        ("LA", "Louisiana"),
        ("ME", "Maine"),
        ("MD", "Maryland"),
        ("MA", "Massachusetts"),
        ("MI", "Michigan"),
        ("MN", "Minnesota"),
        ("MS", "Mississippi"),
        ("MO", "Missouri"),
        ("MT", "Montana"),
        ("NE", "Nebraska"),
        ("NV", "Nevada"),
        ("NH", "New Hampshire"),
        ("NJ", "New Jersey"),
        ("NM", "New Mexico"),
        ("NY", "New York"),
        ("NC", "North Carolina"),
        ("ND", "North Dakota"),
        ("OH", "Ohio"),
        ("OK", "Oklahoma"),
        ("OR", "Oregon"),
        ("PA", "Pennsylvania"),
        ("RI", "Rhode Island"),
        ("SC", "South Carolina"),
        ("SD", "South Dakota"),
        ("TN", "Tennessee"),
        ("TX", "Texas"),
        ("UT", "Utah"),
        ("VT", "Vermont"),
        ("VA", "Virginia"),
        ("WA", "Washington"),
        ("WV", "West Virginia"),
        ("WI", "Wisconsin"),
        ("WY", "Wyoming"),
    ]

    EXPLORE_TYPE_CHOICES = [
        ("academic", "Academic"),
        ("adventure", "Adventure"),
        ("art", "Art"),
        ("conference", "Conference"),
        ("dance", "Dance"),
        ("exhibition", "Exhibition"),
        ("fashion", "Fashion"),
        ("fundraiser", "Fundraiser"),
        ("greek", "Greek"),
        ("health", "Health"),
        ("music", "Music"),
        ("networking", "Networking"),
        ("photography", "Photography"),
        ("social", "Social"),
        ("spiritual", "Spiritual"),
        ("sports", "Sports"),
        ("technology", "Technology"),
        ("volunteer", "Volunteer"),
        ("workshop", "Workshop"),
    ]

    eventId = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, unique=True
    )

    stripeProductId = models.CharField(max_length=255, blank=True, null=True)

    host = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="events"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="incomplete",
        null=False,
        blank=False,
    )

    admin_status = models.CharField(
        max_length=20, choices=ADMIN_STATUS_CHOICES, default="active"
    )

    title = models.CharField(
        _("Title the experience"),
        max_length=200,
        null=False,
        blank=False,
        default="",
    )

    event_type = models.CharField(
        _("Decide what type of experience this is"),
        max_length=100,
        choices=EVENT_TYPE_CHOICES,
        null=False,
        blank=False,
        default="",
    )

    date = models.DateField(
        _("Date your experience"), null=False, blank=False, default=timezone.now
    )
    start_time = models.TimeField(
        _("End time"), null=False, blank=False, default=timezone.now
    )
    end_time = models.TimeField(
        _("Choose time"), null=False, blank=False, default=timezone.now
    )
    description = models.TextField(
        _("Describe your event"), null=False, blank=False, default=""
    )
    privacy = models.CharField(
        _("Determine the visibility of your event."),
        max_length=23,
        choices=PRIVACY_CHOICES,
        null=False,
        blank=False,
        default="",
    )

    ticketing = models.CharField(
        _("What type of ticketing do you want?"),
        max_length=16,
        choices=TICKET_CHOICES,
        null=False,
        blank=False,
        default="",
    )

    building_name = models.CharField(
        _("Building Name"), max_length=250, null=False, blank=False, default=""
    )

    display_event_on_college = models.BooleanField(
        _("Do you want this event displayed on your campus?"),
        null=False,
        blank=False,
        default=False,
    )

    country = models.CharField(
        _("Country"),
        max_length=100,
        null=True,
        blank=True,
        default="United States",
        choices=COUNTRY_CHOICES,
    )

    building_name = models.CharField(
        _("Building Name"), max_length=250, null=False, blank=False, default=""
    )

    display_event_on_college = models.BooleanField(
        _("Do you want this event displayed on your campus?"),
        null=False,
        blank=False,
        default=False,
    )

    street = models.CharField(
        _("Street address"), max_length=500, null=False, blank=False, default=""
    )

    apt_suite_unit = models.CharField(
        _("Appt, suite, unit (optional)"),
        max_length=150,
        blank=False,
        null=False,
        default="",
    )

    city = models.CharField(
        _("City / town"), max_length=100, null=False, blank=False, default=""
    )
    state = models.CharField(
        _("State"),
        max_length=100,
        null=False,
        blank=False,
        default="",
        choices=STATE_CHOICES,
    )
    zip_code = models.CharField(
        _("ZIP code"), max_length=5, null=False, blank=False, default=""
    )
    
    hide_address = models.BooleanField(_("Hide address from users?"), blank=False, null=False, default=False)

    header_photo = models.ImageField(
        _("Add a cover photo"),
        upload_to="event_images/header/",
        null=True,
        blank=False,
        max_length=500,
    )

    body_photo_one = models.ImageField(
        _("(Optional)"),
        upload_to="event_images/body/one/",
        null=True,
        blank=True,
        max_length=500,
    )
    body_photo_two = models.ImageField(
        _("(Optional)"),
        upload_to="event_images/body/two/",
        null=True,
        blank=True,
        max_length=500,
    )
    body_photo_three = models.ImageField(
        _("(Optional)"),
        upload_to="event_images/body/three",
        null=True,
        blank=True,
        max_length=500,
    )
    body_photo_four = models.ImageField(
        _("(Optional)"),
        upload_to="event_images/body/four/",
        null=True,
        blank=True,
        max_length=500,
    )
    body_photo_five = models.ImageField(
        _("(Optional)"),
        upload_to="event_images/body/five/",
        null=True,
        blank=True,
        max_length=500,
    )

    AGE_CHOICES = (
        ("", "No Age Restriction"),
        ("18+", "18+"),
        ("21+", "21+"),
    )

    age_restriction = models.CharField(
        max_length=5,
        choices=AGE_CHOICES,
        null=True,
        blank=True,
        default="",
    )

    crew_discount = models.BooleanField(
        _("Do you want to offer discounts for crew purchases?"),
        null=False,
        blank=False,
        default=False,
    )

    minimum_crew_size = models.PositiveIntegerField(
        _("Minimum crew size"),
        null=True,
        blank=True,
        default=None,
        help_text=_(
            "Minimum number of people needed in a crew to qualify for the discount"
        ),
    )

    crew_discount_percentage = models.DecimalField(
        _("Discounts percentage"),
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        default=None,
        help_text=_("Percentage discount for crew purchases (e.g., 10.00 for 10%)"),
    )

    created_at = models.DateTimeField(auto_now=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    class Meta:
        default_permissions = ()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)


class EventPrivacy(models.Model):
    event = models.OneToOneField(
        "Event", on_delete=models.CASCADE, related_name="privacy_details"
    )
    display_on_explore = models.BooleanField(
        _("Do you want this event displayed on the explore page?"),
        null=True,
        blank=True,
        default=False,
    )
    require_invitation = models.BooleanField(
        _("Require invitation?"),
        null=True,
        blank=True,
        default=False,
    )
    restricted_college = models.ForeignKey(
        College, on_delete=models.SET_NULL, blank=True, null=True
    )
    restricted_organization = models.ForeignKey(
        Organization, on_delete=models.SET_NULL, blank=True, null=True
    )

    class Meta:
        default_permissions = ()

    def __str__(self):
        return f"{self.event.title} Privacy Settings"


class HostProfile(models.Model):
    hostProfileId = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, unique=True
    )
    user = models.OneToOneField(
        "authenticationApp.CustomUser",
        on_delete=models.CASCADE,
        related_name="host_profile",
    )
    stripe_account_id = models.CharField(
        max_length=255, blank=True, null=True, help_text="Stripe account ID"
    )
    bank_account_details = models.TextField(null=True, blank=True)
    cashapp_id = models.CharField(
        max_length=255, blank=True, null=True, help_text="CashApp ID"
    )
    google_pay_id = models.CharField(
        max_length=255, blank=True, null=True, help_text="Google Pay ID"
    )
    apple_pay_id = models.CharField(
        max_length=255, blank=True, null=True, help_text="Apple Pay ID"
    )
    connected_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    def set_bank_account_details(self, details):
        # Save bank account details as plain text (no encryption)
        self.bank_account_details = json.dumps(details)
        self.save()

    def get_bank_account_details(self):
        if not self.bank_account_details:
            return None
        try:
            # Just return the details as plain text
            return json.loads(self.bank_account_details)
        except Exception as e:
            print(f"Error loading bank account details: {e}")
        return None

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}'s Host Profile"


class SharedEvent(models.Model):
    sender = models.ForeignKey(
        "accountManagementApp.UserProfile",
        on_delete=models.CASCADE,
        related_name="sent_shared_events",
    )
    receiver = models.ForeignKey(
        "accountManagementApp.UserProfile",
        on_delete=models.CASCADE,
        related_name="received_shared_events",
        null=True,
        blank=True,
    )
    crew = models.ForeignKey(Crew, on_delete=models.CASCADE, null=True, blank=True)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    shared_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["receiver", "event"], name="unique_event_per_receiver"
            )
        ]

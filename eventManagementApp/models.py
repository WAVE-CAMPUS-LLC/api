import uuid
from django.db import models
from django.utils.translation import gettext as _
from django.utils import timezone
from django.conf import settings
from adminDashboardApp.models import College

from collegeManagementApp.models import Organization


class HostApplication(models.Model):
    EVENT_TYPE_CHOICES = [
        ("conference", "Conference"),
        ("workshop", "Workshop"),
        ("seminar", "Seminar"),
        ("webinar", "Webinar"),
        ("networking", "Networking Event"),
    ]

    firstName = models.CharField(verbose_name="First Name", max_length=70)
    lastName = models.CharField(verbose_name="Last Name", max_length=70)
    email = models.EmailField(verbose_name="Email")
    phone = models.CharField(verbose_name="Phone", max_length=10)

    organizationName = models.CharField(
        verbose_name="Organization Name", max_length=150
    )
    organizationEmail = models.EmailField(verbose_name="Organization Email")
    organizationLocation = models.CharField(
        verbose_name="Organization Location", max_length=150
    )

    eventTypes = models.ManyToManyField("EventType", related_name="applications")

    eventHostedAnnually = models.CharField(
        verbose_name="How many events do you plan on hosting annually?", max_length=100
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

    EVENT_TYPE_CHOICES = [
        ("sports", "Sports"),
        ("social", "Social"),
        ("networking", "Networking"),
        ("greek", "Greek"),
        ("music", "Music"),
        ("conference", "Conference"),
        ("workshop", "Workshop"),
        ("exhibition", "Exhibition"),
        ("technology", "Technology"),
        ("health", "Health"),
        ("fundraiser", "Fundraiser"),
        ("volunteer", "Volunteer"),
        ("fashion", "Fashion"),
        ("adventure", "Adventure"),
        ("spiritual", "Spiritual"),
        ("academic", "Academic"),
        ("photography", "Photography"),
        ("art", "Art"),
        ("dance", "Dance"),
    ]

    PRIVACY_CHOICES = [
        ("Discoverable", "Discoverable"),
        ("Invite Only", "Invite Only"),
        ("College Only", "College Only"),
        ("Org Only", "Org Only"),
    ]

    COUNTRY_CHOICES = [("United States", "United States")]

    EXPLORE_TYPE_CHOICES = [
        ("sports", "Sports"),
        ("social", "Social"),
        ("networking", "Networking"),
        ("greek", "Greek"),
        ("music", "Music"),
        ("conference", "Conference"),
        ("workshop", "Workshop"),
        ("exhibition", "Exhibition"),
        ("technology", "Technology"),
        ("health", "Health"),
        ("fundraiser", "Fundraiser"),
        ("volunteer", "Volunteer"),
        ("fashion", "Fashion"),
        ("adventure", "Adventure"),
        ("spiritual", "Spiritual"),
        ("academic", "Academic"),
        ("photography", "Photography"),
        ("art", "Art"),
        ("dance", "Dance"),
    ]

    eventId = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, unique=True
    )
    # publicId = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    host = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="events"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="incomplete",
        null=True,
        blank=True,
    )

    title = models.CharField(
        _("What would you like to title the event?"),
        max_length=200,
        null=True,
        blank=True,
        default="",
    )

    event_type = models.CharField(
        _("What type of event is it?"),
        max_length=100,
        choices=EVENT_TYPE_CHOICES,
        null=True,
        blank=True,
        default="",
    )

    date = models.DateField(
        _("Choose date"), null=True, blank=True, default=timezone.now
    )
    start_time = models.TimeField(
        _("End time"), null=True, blank=True, default=timezone.now
    )
    end_time = models.TimeField(
        _("Choose time"), null=True, blank=True, default=timezone.now
    )
    description = models.TextField(
        _("Describe your event"), null=True, blank=True, default=""
    )
    privacy = models.CharField(
        _("Is this a public event or restricted event?"),
        max_length=23,
        choices=PRIVACY_CHOICES,
        null=True,
        blank=True,
        default="",
    )

    country = models.CharField(
        _("Country"),
        max_length=100,
        null=True,
        blank=True,
        default="",
        choices=COUNTRY_CHOICES,
    )

    building_name = models.CharField(
        _("Building Name"), max_length=250, null=True, blank=True, default=""
    )

    display_event_on_college = models.BooleanField(
        _("Do you want this event displayed on your campus?"),
        null=True,
        blank=True,
        default=False,
    )

    street = models.CharField(
        _("Street address"), max_length=500, null=True, blank=True, default=""
    )

    apt_suite_unit = models.CharField(
        _("Appt, suite, unit (optional)"),
        max_length=150,
        blank=True,
        null=True,
        default="",
    )

    city = models.CharField(
        _("City / town"), max_length=100, null=True, blank=True, default=""
    )
    state = models.CharField(
        _("State"), max_length=100, null=True, blank=True, default=""
    )
    zip_code = models.CharField(
        _("ZIP code"), max_length=6, null=True, blank=True, default=""
    )

    contact_email = models.EmailField(_("Email"), null=True, blank=True, default="")
    contact_phone = models.CharField(
        _("Phone"), max_length=20, null=True, blank=True, default=""
    )
    contact_website = models.URLField(_("Website"), blank=True, null=True, default="")
    contact_instagram = models.CharField(
        _("Instagram"), max_length=100, blank=True, null=True, default=""
    )

    header_photo = models.ImageField(
        _("Add a cover photo"),
        upload_to="event_images/header/",
        null=True,
        blank=True,
    )

    body_photo_one = models.ImageField(
        _("(Optional)"), upload_to="event_images/body/one/", null=True, blank=True
    )
    body_photo_two = models.ImageField(
        _("(Optional)"), upload_to="event_images/body/two/", null=True, blank=True
    )
    body_photo_three = models.ImageField(
        _("(Optional)"), upload_to="event_images/body/three", null=True, blank=True
    )
    body_photo_four = models.ImageField(
        _("(Optional)"), upload_to="event_images/body/four/", null=True, blank=True
    )
    body_photo_five = models.ImageField(
        _("(Optional)"), upload_to="event_images/body/five/", null=True, blank=True
    )

    def __str__(self):
        return self.title


class EventPrivacy(models.Model):
    event = models.OneToOneField(
        "Event", on_delete=models.CASCADE, related_name="privacy_details"
    )

    DISCOVERABILITY_CHOICES = [
        ("open", "Open to Anyone"),
        ("rsvp", "RSVP Required"),
    ]

    RESTRICTION_CHOICES = [
        ("invite_only", "Invite Only"),
        ("college", "Restricted to College"),
        ("organization", "Restricted to Organization"),
    ]

    discoverability_level = models.CharField(
        max_length=10, choices=DISCOVERABILITY_CHOICES, blank=True, null=True
    )
    restriction_type = models.CharField(
        max_length=20, choices=RESTRICTION_CHOICES, blank=True, null=True
    )
    restricted_college = models.ForeignKey(
        College, on_delete=models.SET_NULL, blank=True, null=True
    )
    restricted_organization = models.ForeignKey(
        Organization, on_delete=models.SET_NULL, blank=True, null=True
    )

    def __str__(self):
        return f"{self.event.title} Privacy Settings"


class EventTicket(models.Model):
    TYPE_CHOICES = [
        ("Free", "Free"),
        ("Priced", "Priced"),
    ]

    event = models.ForeignKey(
        Event, verbose_name=_("Related Event"), on_delete=models.CASCADE
    )
    privateTicketId = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, unique=True
    )
    ticket_name = models.CharField(_("Ticket Name"), max_length=50)
    ticket_type = models.CharField(
        _("Pricing Type"),
        max_length=6,
        null=False,
        blank=False,
        default="Free",
        choices=TYPE_CHOICES,
    )
    ticket_price = models.DecimalField(
        _("Ticket Price"), max_digits=10, decimal_places=2, null=True, blank=True
    )
    ticket_description = models.TextField(
        _("Describe ticket. Are there any perks?"), max_length=300
    )
    ticket_quantity = models.PositiveIntegerField(
        _("How many tickets should be made available?")
    )

    class Meta:
        unique_together = ("event", "ticket_name")

    def __str__(self):
        return f"{self.ticket_name} for {self.event.title}"

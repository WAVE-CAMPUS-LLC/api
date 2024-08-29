import uuid
from django.db import models
from django.utils.translation import gettext as _
from django.utils import timezone
from django.conf import settings
from multiupload.fields import MultiImageField


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
        ("archived", "Archived")
    ]

    PRIVACY_CHOICES = [
        ("Invite-Only", "Invite-Only"),
        ("Public", "Public"),
        ("Private", "Private"),
    ]

    COUNTRY_CHOICES = [("United States", "United States")]

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
        null=False,
        blank=True,
        default="",
    )

    EVENT_TYPE_CHOICES = [
        ("music", "music"),
        ("party", "party"),
        ("concert", "concert"),
        ("sports", "sports"),
        ("games", "games"),
        ("greek", "greek"),
    ]

    EVENT_IMG_PATH = "images/eventManagementApp/host/images/selectors/"

    EVENT_TYPE_IMAGES = {
        "music": f"{EVENT_IMG_PATH}music.svg",
        "party": f"{EVENT_IMG_PATH}party.svg",
        "concert": f"{EVENT_IMG_PATH}concert.svg",
        "sports": f"{EVENT_IMG_PATH}sports.svg",
        "games": f"{EVENT_IMG_PATH}games.svg",
        "greek": f"{EVENT_IMG_PATH}greek.png",
    }

    EXPLORE_TYPE_CHOICES = [
        ("music", "music"),
        ("party", "party"),
        ("concert", "concert"),
        ("sports", "sports"),
        ("games", "games"),
        ("greek", "greek"),
    ]

    EXPLORE_CATEGORY_IMG_PATH = "images/explore/categories/"

    EXPLORE_CATEGORY_TYPE_IMAGES = {
        "music": f"{EXPLORE_CATEGORY_IMG_PATH}music.png",
        "party": f"{EXPLORE_CATEGORY_IMG_PATH}party.png",
        "concert": f"{EXPLORE_CATEGORY_IMG_PATH}concert.png",
        "sports": f"{EXPLORE_CATEGORY_IMG_PATH}sports.png",
        "games": f"{EXPLORE_CATEGORY_IMG_PATH}games.png",
        "greek": f"{EXPLORE_CATEGORY_IMG_PATH}greek.png",
    }

    event_type = models.CharField(
        _("What type of event is it?"),
        max_length=100,
        choices=EVENT_TYPE_CHOICES,
        null=False,
        blank=True,
        default="",
    )
    date = models.DateField(
        _("Choose date"), null=False, blank=True, default=timezone.now
    )
    start_time = models.TimeField(
        _("End time"), null=False, blank=True, default=timezone.now
    )
    end_time = models.TimeField(
        _("Choose time"), null=False, blank=True, default=timezone.now
    )
    description = models.TextField(
        _("Describe your event"), null=False, blank=True, default=""
    )
    privacy = models.CharField(
        _("Would this event be invite-only, private, or public?"),
        max_length=20,
        choices=PRIVACY_CHOICES,
        null=False,
        blank=True,
        default="",
    )

    country = models.CharField(
        _("Country"),
        max_length=100,
        null=False,
        blank=True,
        default="",
        choices=COUNTRY_CHOICES,
    )
    building_name = models.CharField(
        _("Building Name"), max_length=250, null=False, blank=False, default=""
    )
    street = models.CharField(
        _("Street address"), max_length=500, null=False, blank=True, default=""
    )
    apt_suite_unit = models.CharField(
        _("Appt, suite, unit (optional)"),
        max_length=150,
        blank=True,
        null=True,
        default="",
    )
    city = models.CharField(
        _("City / town"), max_length=100, null=False, blank=True, default=""
    )
    state = models.CharField(
        _("State"), max_length=100, null=False, blank=True, default=""
    )
    zip_code = models.CharField(
        _("ZIP code"), max_length=6, null=False, blank=True, default=""
    )

    contact_email = models.EmailField(_("Email"), null=False, blank=True, default="")
    contact_phone = models.CharField(
        _("Phone"), max_length=20, null=False, blank=True, default=""
    )
    contact_website = models.URLField(_("Website"), blank=True, null=True, default="")
    contact_instagram = models.CharField(
        _("Instagram"), max_length=100, blank=True, null=True, default=""
    )

    header_photo = models.ImageField(
        _("Add a cover photo"),
        upload_to="event_images/header/",
        null=False,
        blank=True,
    )

    body_photo_one = models.ImageField(
        _("First"), upload_to="event_images/body/one/", null=False, blank=False
    )
    body_photo_two = models.ImageField(
        _("Second"), upload_to="event_images/body/two/", null=False, blank=False
    )
    body_photo_three = models.ImageField(
        _("Third"), upload_to="event_images/body/three", null=False, blank=False
    )
    body_photo_four = models.ImageField(
        _("Fourth"), upload_to="event_images/body/four/", null=False, blank=False
    )
    body_photo_five = models.ImageField(
        _("Fifth"), upload_to="event_images/body/five/", null=False, blank=False
    )

    def get_event_type_image(self):
        return self.EVENT_TYPE_IMAGES.get(
            self.event_type,
            "images/eventManagementApp/host/images/selectors/default.svg",
        )

    def __str__(self):
        return self.title


class EventTicket(models.Model):
    event = models.ForeignKey(
        Event, verbose_name=_("Related Event"), on_delete=models.CASCADE
    )
    ticket_total = models.CharField(
        _("How many tickets should be made available?"), max_length=100000000000000000
    )
    type_total = models.PositiveIntegerField(
        _("How many types of tickets do you want?")
    )
    type_name = models.CharField(_("Type Name"), max_length=100)
    type_quantity = models.PositiveIntegerField(_("Type Quantity"))

    class Meta:
        unique_together = ("event", "type_name")

import uuid
from django.db import models
from django.utils.translation import gettext as _
from django.utils import timezone
from django.conf import settings
from urllib.parse import urlparse
from django.core.exceptions import ValidationError


# Create your models here.
class College(models.Model):
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

    COUNTRY_CHOICES = [("USA", "United States of America")]

    collegeId = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, unique=True
    )
    name = models.CharField(_("College name"), max_length=150)
    address = models.CharField(_("Address"), max_length=500)
    city = models.CharField(_("City"), max_length=20, default="")
    state = models.CharField(
        _("State"), max_length=2, choices=STATE_CHOICES, default=""
    )
    zip_code = models.CharField(_("ZIP Code"), max_length=5)
    country = models.CharField(_("Country"), max_length=5, choices=COUNTRY_CHOICES)

    logo = models.ImageField(
        _("Upload the college logo"), upload_to="college_logos/", blank=True, null=False
    )
    motto = models.CharField(_("What's your college's motto?"), max_length=200)

    contact_website = models.URLField(_("College website"), blank=True, null=True)
    email_domain = models.CharField(
        _("College email domain"), max_length=100, blank=True
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="college_created",
    )

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.email_domain and self.contact_website:
            self.email_domain = self.extract_email_domain_from_website(
                self.contact_website
            )
        super().save(*args, **kwargs)

    @staticmethod
    def extract_email_domain_from_website(url):
        parsed_url = urlparse(url)

        domain = parsed_url.netloc
        if domain.startswith("www."):
            domain = domain[4:]
        if not domain:
            raise ValidationError("Invalid link. Enter your college's website.")
        return domain


class Organization(models.Model):
    PRIVACY_CHOICES = [("Private", "Private"), ("Public", "Public")]

    college = models.ForeignKey(
        College, on_delete=models.CASCADE, related_name="organizations"
    )
    orgId = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, unique=True
    )

    name = models.CharField(_("Organization name"),max_length=100)
    description = models.TextField(_("Describe your org"),)
    privacy = models.CharField(_("Organization privacy?"),max_length=30, choices=PRIVACY_CHOICES)

    logo = models.ImageField(_("Upload an image to represent the org"),upload_to="organization_logos/", blank=True, null=True)

    contact_name = models.CharField(_("Who can we contact? e.g. president, etc"),max_length=100)
    contact_email = models.EmailField(_("What email can we contact?"),)
    contact_website = models.URLField(_("Does the organization have a website?"),blank=True, null=True)

    instagram = models.CharField(_("Connect via Instagram"),max_length=50, blank=True, null=True)

    date_added = models.DateTimeField(auto_now_add=True, editable=False)
    date_modified = models.DateTimeField(auto_now=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="organization_created",
    )

    def __str__(self):
        return self.name

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name", "college"], name="unique_organization_per_college"
            )
        ]


class Membership(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    college = models.ForeignKey(College, on_delete=models.CASCADE)
    date_joined = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'college')
        
    def __str__(self):
        return f'{self.user} - {self.college}'
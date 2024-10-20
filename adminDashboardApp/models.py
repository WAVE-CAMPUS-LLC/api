from datetime import timedelta
from django.db import models
from django.conf import settings
from urllib.parse import urlparse
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext as _
from django.contrib.auth.models import Group
from django.contrib.auth.models import User
from django.apps import apps
import uuid


# Create your models here.

class UserActivity(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    action = models.CharField(max_length=100)
    timestamp = models.DateTimeField()

    def __str__(self):
        return f'{self.user} - {self.action} at {self.timestamp}'


class Department(models.Model):
    name = models.CharField("Department Name", max_length=100)
    departmentID = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, unique=True
    )
    lead_name = models.CharField("Department Lead", max_length=100)
    lead_email = models.EmailField("Lead Email")
    capacity = models.IntegerField("Capacity")
    location = models.CharField("Location", max_length=300)
    description = models.TextField("Description")

    class Meta:
        default_permissions = ()

    def __str__(self):
        return self.name


class CareerRole(models.Model):
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name="admin_dashboard_career_roles",
    )
    roleID = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, unique=True
    )
    roleTitle = models.CharField("Name", max_length=100)
    roleDescription = models.TextField("Description")
    # companyOverview = models.TextField("Company Summary")
    roleExpectations = models.TextField("What's expected")
    roleRequirements = models.TextField("Requirements")
    roleLocation = models.CharField("Role Location", max_length=100)
    roleType = models.CharField(
        "Role Type",
        max_length=20,
        choices=[("Remote", "remote"), ("In-person", "in-person")],
    )
    # roleExperience = models.TextField("What you need to have")
    advertisementLength = models.IntegerField("Advertisement Length (in days)")
    advertisementStartDate = models.DateField(
        "Advertisement Start Date", default=timezone.now
    )
    roleCapacity = models.CharField(
        "Role Capacity",
        max_length=20,
        choices=[("Full-Time", "full-time"), ("Part-Time", "part-time")],
    )

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    def is_ad_expired(self):
        expiry_date = self.advertisementStartDate + timedelta(
            days=self.advertisementLength
        )
        return expiry_date <= timezone.now()

    class Meta:
        default_permissions = ()  # Removing default permissions

    def __str__(self):
        return self.roleTitle


class LoginHistoryModel(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    email = models.EmailField()
    login_time = models.DateTimeField(default=timezone.now)
    logout_time = models.DateTimeField(null=True, blank=True)
    ip_address = models.CharField(max_length=50)
    session_duration_minutes = models.IntegerField(null=True, blank=True)
    session_duration_seconds = models.IntegerField(
        null=True, blank=True
    )  # New field for session duration in seconds
    role = models.CharField(
        max_length=4, null=True, blank=True
    )  # New field for user role

    def save(self, *args, **kwargs):
        if self.logout_time:
            session_duration = self.logout_time - self.login_time
            self.session_duration_minutes = session_duration.total_seconds() // 60
            self.session_duration_seconds = (
                session_duration.total_seconds() % 60
            )  # Calculate remaining seconds
            print(f"Session duration: {session_duration}")

        super().save(*args, **kwargs)

    @property
    def is_active(self):
        return not self.logout_time

    def end_session(self):
        if not self.logout_time:
            self.logout_time = timezone.now()
            self.save()

    class Meta:
        default_permissions = ()  # Removing default permissions

    def __str__(self):
        return f"{self.user} - {self.login_time} - Active: {self.is_active}"


class Permission(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField()

    class Meta:
        default_permissions = ()  # Removing default permissions
        permissions = [
            # Member Permissions
            ("view_profile_overview", "View profile overview - WAVE."),
            ("view_account_settings", "View account settings - WAVE."),
            ("view_support_portal", "View support portal - WAVE."),
            # Super Admin Permissions
            ("view_users", "View users - WAVE."),  # Regular Admin
            ("manage_users", "Manage users - WAVE."),  # Super Admin
            ("view_applications", "View applications - WAVE."),  # Regular admin
            ("manage_applications", "Manage applications - WAVE."),  # Super admin
            ("view_departments", "View departments - WAVE."),  # Regular admin
            ("manage_departments", "Manage departments - WAVE."),
            # Event Manager
            ("view_all_events", "View all events - WAVE."),
            ("manage_all_events", "Manage all events - WAVE."),
            # Support Staff
            ("view_support_tickets", "View support tickets - WAVE."),
            ("manage_support_tickets", "Manage support tickets - WAVE."),
            # Event Host Member
            ("create_event", "Create events - WAVE."),
            ("manage_host_event", "Manage host event - WAVE."),
            ("view_host_event", "View host event - WAVE."),
            # Suspend Group Permissions
            ("user_suspension", "Member has been suspended - WAVE."),
        ]

    def __str__(self):
        return self.name


class Group(models.Model):
    name = models.CharField(max_length=100)
    permissions = models.ManyToManyField(Permission)
    role_color = models.CharField(max_length=7, blank=True, null=True)

    def __str__(self):
        return self.name


class Newsroom(models.Model):
    NEWS_TYPE_CHOICES = [("The HQ", "HQ"), ("Product & Features", "Product & Features")]
    URGENCY_TYPE_CHOICES = [("THE LATEST", "THE LATEST"), ("REGULAR", "REGULAR")]
    newsId = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, unique=True
    )
    title = models.CharField(max_length=500)
    body = models.TextField(max_length=10000)
    created_at = models.DateTimeField(editable=False, auto_now_add=True)

    newsCategory = models.CharField(
        _("News Category"), max_length=20, choices=NEWS_TYPE_CHOICES, default=""
    )

    urgencyLevel = models.CharField(
        _("A headline news item or regular?"),
        max_length=20,
        choices=URGENCY_TYPE_CHOICES,
        default="",
    )

    headerImage = models.ImageField(
        _("Header Image"),
        upload_to="newsroom/images/header/",
        blank=False,
        null=False,
    )

    imageOne = models.ImageField(
        _("Body Image"),
        upload_to="newsroom/images/body/",
        blank=True,
        null=True,
    )

    imageTwo = models.ImageField(
        _("Body Image"),
        upload_to="newsroom/images/body/",
        blank=True,
        null=True,
    )

    imageThree = models.ImageField(
        _("Body Image"),
        upload_to="newsroom/images/body/",
        blank=True,
        null=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="news_created",
    )

    class Meta:
        default_permissions = ()  # Removing default permissions
        permissions = [
            # Member Permissions
            ("manage_newsroom", "Manage newsroom content. Admin only."),
        ]

    def __str__(self):
        return self.title


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
    name = models.CharField("College name", max_length=150)
    address = models.CharField("Address", max_length=500)
    city = models.CharField("City", max_length=20, default="")
    state = models.CharField("State", max_length=2, choices=STATE_CHOICES, default="")
    zip_code = models.CharField("ZIP Code", max_length=5)
    country = models.CharField("Country", max_length=5, choices=COUNTRY_CHOICES)

    logo = models.ImageField(
        "Upload the college logo", upload_to="college_logos/", blank=True, null=False
    )
    motto = models.CharField("What's your college's motto?", max_length=200)
    contact_website = models.URLField("College website", blank=True, null=True)
    email_domain = models.CharField("College email domain", max_length=100, blank=True)
    
    managers = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name="managed_colleges"
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


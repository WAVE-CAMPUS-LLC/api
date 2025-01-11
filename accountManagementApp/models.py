import uuid
import re
import qrcode
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
from PIL import Image
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone

from eventManagementApp.models import Event, SharedEvent
from eventTicketsApp.models import InviteEventOption
from .utils import generate_profile_picture
from django.contrib.auth.models import Group
from collegeManagementApp.models import College
from socialApp.models import CrewMember, CrewRequest, FriendRequest, Crew
from wave_v1.supabase_storage import upload_to_supabase
from django.core.files.storage import default_storage
import os


# Create your models here.


class EventTypePreferences(models.Model):
    name = models.CharField(max_length=50, unique=True)

    class Meta:
        default_permissions = ()

    def __str__(self):
        return self.name


class UserProfile(models.Model):
    USER_STATUS_OPTION = [
        ("Happy 😊", "Happy 😊"),
        ("Excited 🎉", "Excited 🎉"),
        ("Grateful 🙏", "Grateful 🙏"),
        ("Motivated 💪", "Motivated 💪"),
        ("Blessed ✨", "Blessed ✨"),
        ("Inspired 🌈", "Inspired 🌈"),
        ("Just here 🤙", "Just here 🤙"),
        ("Living 🌿", "Living 🌿"),
        ("Relaxing ☕", "Relaxing ☕"),
        ("Chillin' 😎", "Chillin' 😎"),
        ("Unbothered 🌊", "Unbothered 🌊"),
        ("Taking it easy 🌼", "Taking it easy 🌼"),
        ("Focused 🧠", "Focused 🧠"),
        ("Grinding 🚀", "Grinding 🚀"),
        ("Busy 💼", "Busy 💼"),
        ("Hustling 🏃‍♂️", "Hustling 🏃‍♂️"),
        ("Creating 🎨", "Creating 🎨"),
        ("In my zone 🎯", "In my zone 🎯"),
        ("Meh 😐", "Meh 😐"),
        ("Just okay 🤷‍♂️", "Just okay 🤷‍♂️"),
        ("Could be better 😕", "Could be better 😕"),
        ("Waiting... ⏳", "Waiting... ⏳"),
        ("Confused 🤔", "Confused 🤔"),
        ("Tired 😴", "Tired 😴"),
        ("Stressed 😓", "Stressed 😓"),
        ("Overwhelmed 🌪️", "Overwhelmed 🌪️"),
        ("Feeling low 😔", "Feeling low 😔"),
        ("Need a break 🛑", "Need a break 🛑"),
        ("Not today 🙅‍♂️", "Not today 🙅‍♂️"),
        ("Exploring 🗺️", "Exploring 🗺️"),
        ("On the move 🚶‍♂️", "On the move 🚶‍♂️"),
        ("Seeking new things 🔍", "Seeking new things 🔍"),
        ("Wanderlust 🌍", "Wanderlust 🌍"),
        ("Chasing dreams ✈️", "Chasing dreams ✈️"),
        ("Hanging out 🍻", "Hanging out 🍻"),
        ("Party time 🎉", "Party time 🎉"),
        ("Game on 🎮", "Game on 🎮"),
        ("Vibing with friends 👫", "Vibing with friends 👫"),
        ("Making memories 📸", "Making memories 📸"),
        ("Grateful 🧘‍♂️", "Grateful 🧘‍♂️"),
        ("Deep in thought 🤔", "Deep in thought 🤔"),
        ("Reflecting 🪞", "Reflecting 🪞"),
        ("Taking it all in 🌱", "Taking it all in 🌱"),
        ("Growing 🌱", "Growing 🌱"),
        ("It's complicated 🤯", "It's complicated 🤯"),
        ("Undefined 🤷‍♂️", "Undefined 🤷‍♂️"),
        ("TBD (To Be Determined) 🕵️", "TBD (To Be Determined) 🕵️"),
        ("Can't explain 🌀", "Can't explain 🌀"),
    ]
    GENDER_OPTIONS = [
        ("Male", "Male"),
        ("Female", "Female"),
        ("Other", "Other"),
        ("Prefer not to say", "Prefer not to say"),
    ]
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
    EVENT_SIZE_CHOICES = [
        ("Intimate (1-30 people)", "Intimate (1-30 people)"),
        ("Medium (50-100 people)", "Medium (50-100 people)"),
        ("Large (100+ people)", "Large (100+ people)"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="user_profile",
        null=True,
    )
    group = models.ManyToManyField(Group, related_name="user_group")
    college = models.ForeignKey(
        College, null=True, blank=True, on_delete=models.SET_NULL
    )
    friends = models.ManyToManyField("self", symmetrical=True, blank=True)
    is_campus_manager = models.BooleanField(default=False)

    status = models.TextField(
        _("How do you feel right now?"), blank=True, choices=USER_STATUS_OPTION
    )
    gender = models.CharField(
        _("What gender do you indentify as?"),
        max_length=17,
        blank=True,
        choices=GENDER_OPTIONS,
    )
    profile_photo = models.ImageField(
        _("Profile picture"),
        upload_to="profile/profilePictures/",
        null=True,
        blank=True,
    )

    home_state = models.CharField(
        "What's your home state?", max_length=2, choices=STATE_CHOICES, default=""
    )

    college_name = models.CharField(
        _("Enter your college name"), max_length=150, blank=True
    )
    current_year = timezone.now().year
    graduation_year = models.PositiveIntegerField(
        _("Enter your graduation year"),
        validators=[
            MinValueValidator(current_year),
            MaxValueValidator(current_year + 10),
        ],
        null=True,
        blank=True,
    )
    major = models.CharField(_("What's your major?"), max_length=150, blank=True)

    # Event Preferences
    event_types = models.ManyToManyField(
        EventTypePreferences, related_name="user_preferences", blank=True
    )

    # Social Media Profiles
    instagram = models.CharField(max_length=100, blank=True, default="")
    tiktok = models.CharField(max_length=100, blank=True, default="")

    was_host = models.BooleanField(default=False)

    # Invited Events
    invited_events = models.ManyToManyField(
        Event, related_name="invited_events", blank=True
    )
    invitations = models.ManyToManyField(
        InviteEventOption, related_name="invitations", blank=True
    )

    profile_qr_code = models.ImageField(
        upload_to="profile/qr_code/", null=True, blank=True
    )
    
    favorite_events = models.ManyToManyField(
        Event, related_name="favorited_by", blank=True, null=True
    )

    class Meta:
        default_permissions = ()
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

    def __str__(self):
        return self.user.username

    def generate_qr_code(self):
        part_url = reverse("social:publicProfile", kwargs={"username": self.user.username})
        
        url = f"{settings.SITE_URL}{part_url}"
        qr = qrcode.make(url)

        img_io = BytesIO()
        qr.save(img_io, "PNG")
        img_io.seek(0)

        self.profile_qr_code.save(
            f"{self.user.username}_qr_code.png",
            InMemoryUploadedFile(
                img_io,
                None,
                f"{self.user.username}_qr_code.png",
                "image/png",
                img_io.tell(),
                None,
            ),
            save=False,
        )

    def save(self, *args, event_types=None, **kwargs):
        # Handle profile photo upload to Supabase
        if self.profile_photo and hasattr(self.profile_photo, 'file'):
            # Create a temporary file
            temp_path = f"temp_{self.user.username}_profile.{self.profile_photo.name.split('.')[-1]}"
            with open(temp_path, 'wb+') as destination:
                for chunk in self.profile_photo.chunks():
                    destination.write(chunk)
            
            try:
                # Upload to Supabase and get URL
                destination_path = f"profile_pictures/{self.user.username}/{os.path.basename(self.profile_photo.name)}"
                public_url = upload_to_supabase('wave', temp_path, destination_path)
                self.profile_photo.name = public_url
            finally:
                # Clean up temporary file
                if os.path.exists(temp_path):
                    os.remove(temp_path)

        # Handle event types and QR code
        if event_types is not None:
            event_type_preferences = []
            for event_type_name in event_types:
                event_type, created = EventTypePreferences.objects.get_or_create(
                    name=event_type_name
                )
                event_type_preferences.append(event_type)
            self.event_types.set(event_type_preferences)

        if not self.profile_qr_code:
            self.generate_qr_code()

        super(UserProfile, self).save(*args, **kwargs)

    def is_friends_with(self, other_user):
        return self.friends.filter(
            user=other_user
        ).exists() and not self.has_pending_request(other_user)

    def has_pending_request(self, other_user):
        return (
            FriendRequest.objects.filter(
                sender=self.user, receiver=other_user, status="pending"
            ).exists()
            or FriendRequest.objects.filter(
                sender=other_user, receiver=self.user, status="pending"
            ).exists()
        )

    def has_declined_request(self, other_user):
        return (
            FriendRequest.objects.filter(
                sender=self.user, receiver=other_user, status="declined"
            ).exists()
            or FriendRequest.objects.filter(
                sender=other_user, receiver=self.user, status="declined"
            ).exists()
        )

    def is_in_crew(self, crewId):
        receiver = get_object_or_404(CrewMember, user__username=self.user.username)
        if receiver is None:
            return False
        else:
            return Crew.objects.filter(crewId=crewId, members=receiver).exists()

    def has_pending_crew_request(self, other_user):
        return (
            CrewRequest.objects.filter(
                sender=self.user, receiver=other_user, status="pending"
            ).exists()
            or CrewRequest.objects.filter(
                sender=other_user, receiver=self.user, status="pending"
            ).exists()
        )

    def has_declined_crew_request(self, other_user):
        return (
            CrewRequest.objects.filter(
                sender=self.user, receiver=other_user, status="declined"
            ).exists()
            or CrewRequest.objects.filter(
                sender=other_user, receiver=self.user, status="declined"
            ).exists()
        )

    def is_crew_owner(self, crewId):
        crew = get_object_or_404(Crew, crewId=crewId)
        return crew.created_by == self.user

    def get_all_crews(self):
        all_crew_members = CrewMember.objects.filter(user=self.user).all()
        all_crews = []
        for member in all_crew_members:
            all_crews.append(member.crew)
        return all_crews

    def get_shared_events(self):
        return SharedEvent.objects.filter(receiver=self.user)
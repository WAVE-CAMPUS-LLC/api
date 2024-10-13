import re
from django.db import models
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.contrib.auth.models import Group
from collegeManagementApp.models import College
from socialApp.models import CrewMember, CrewRequest, FriendRequest, Crew


# Create your models here.
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
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="user_profile"
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
    birthday = models.DateField(_("Enter your birthday"), null=True, blank=True)
    gender = models.CharField(
        _("What gender do you indentify as?"),
        max_length=17,
        blank=True,
        choices=GENDER_OPTIONS,
    )
    profile_photo = models.ImageField(
        _("Upload a profile picture"),
        upload_to="profile/pfp/",
        null=False,
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
    event_size = models.CharField(
        _("What's your preferred event size?"),
        max_length=22,
        choices=EVENT_SIZE_CHOICES,
        default="Medium (50-100 people)",
    )
    eventTypes = models.ManyToManyField("EventTypePreferences", related_name="user_preferences")
    
    # Communication Preferences
    email_communication = models.BooleanField(_("Email notifications"), default=True)
    text_communication = models.BooleanField(_("Text notifications"), default=True)

    class Meta:
        default_permissions = ()
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

    def __str__(self):
        return self.user.username

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

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


class EventTypePreferences(models.Model):
    name = models.CharField(max_length=50, unique=True)

    class Meta:
        default_permissions = ()

    def __str__(self):
        return self.name
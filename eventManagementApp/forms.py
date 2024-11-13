from django import forms
from .models import HostApplication, Event
from django.utils.translation import gettext_lazy as _
from adminDashboardApp.models import College
from accountManagementApp.models import UserProfile
from collegeManagementApp.models import OrganizationMembership, Organization


class HostApplicationForm(forms.ModelForm):
    EVENT_TYPE_CHOICES = [
        ("conference", "Conference"),
        ("workshop", "Workshop"),
        ("seminar", "Seminar"),
        ("webinar", "Webinar"),
        ("networking", "Networking Event"),
    ]

    eventTypes = forms.MultipleChoiceField(
        choices=EVENT_TYPE_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=True,
        label="What type of events do you want to host?",
    )

    class Meta:
        model = HostApplication
        fields = [
            "firstName",
            "lastName",
            "email",
            "phone",
            "organizationName",
            "organizationEmail",
            "organizationLocation",
            "eventTypes",
            "eventHostedAnnually",
            "eventPopulation",
        ]


class EventForm(forms.ModelForm):
    date = forms.DateField(
        label=_("Choose date"),
        required=False,
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
        input_formats=["%Y-%m-%d"],
    )

    start_time = forms.TimeField(
        label=_("Start time"),
        required=False,
        widget=forms.TimeInput(format="%H:%M", attrs={"type": "time"}),
        input_formats=["%H:%M"],
    )

    end_time = forms.TimeField(
        label=_("End time"),
        required=False,
        widget=forms.TimeInput(format="%H:%M", attrs={"type": "time"}),
        input_formats=["%H:%M"],
    )

    class Meta:
        model = Event

        fields = [
            "status",
            "title",
            "event_type",
            "date",
            "start_time",
            "end_time",
            "description",
            "privacy",
            "ticketing",
            "country",
            "building_name",
            "street",
            "apt_suite_unit",
            "city",
            "state",
            "zip_code",
            "contact_email",
            "contact_phone",
            "contact_website",
            "contact_instagram",
            "header_photo",
            "body_photo_one",
            "body_photo_two",
            "body_photo_three",
            "body_photo_four",
            "body_photo_five",
        ]

        widgets = {
            "country": forms.Select(),
            "status": forms.HiddenInput(),
        }


class EventTitleForm(forms.ModelForm):
    title = forms.CharField(max_length=200, required=False)
        
    class Meta:
        model = Event
        fields = ["title"]  

class EventTypeForm(forms.ModelForm):
    EVENT_TYPE_CHOICES = [
        ("Sports", "Sports"),
        ("Social", "Social"),
        ("Networking", "Networking"),
        ("Greek", "Greek"),
        ("Music", "Music"),
        ("Conference", "Conference"),
        ("Workshop", "Workshop"),
        ("Exhibition", "Exhibition"),
        ("Technology", "Technology"),
        ("Health", "Health"),
        ("Fundraiser", "Fundraiser"),
        ("Volunteer", "Volunteer"),
        ("Fashion", "Fashion"),
        ("Adventure", "Adventure"),
        ("Spiritual", "Spiritual"),
        ("Academic", "Academic"),
        ("Photography", "Photography"),
        ("Art", "Art"),
        ("Dance", "Dance"),
    ]
        
    event_type = forms.ChoiceField(
        choices=EVENT_TYPE_CHOICES,
        required=False,
        initial="",
    )
    
    class Meta:
        model = Event
        fields = ["event_type"]
    
class EventDateForm(forms.ModelForm):
    date = forms.DateField(
        label=_("Choose date"),
        required=False,
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
        input_formats=["%Y-%m-%d"],
    )
    
    class Meta:
        model = Event
        fields = ["date"]
        
class EventStartTimeForm(forms.ModelForm):
    start_time = forms.TimeField(
        label=_("Start time"),
        required=False,
        widget=forms.TimeInput(format="%H:%M", attrs={"type": "time"}),
        input_formats=["%H:%M"],
    )

    class Meta:
        model = Event
        fields = ["start_time"]

class EventEndTimeForm(forms.ModelForm):
    end_time = forms.TimeField(
        label=_("End time"),
        required=False,
        widget=forms.TimeInput(format="%H:%M", attrs={"type": "time"}),
        input_formats=["%H:%M"],
    )

    class Meta:
        model = Event
        fields = ["end_time"]
        
class EventDescriptionForm(forms.ModelForm):
    description = forms.CharField(max_length=2000, required=False)
        
    class Meta:
        model = Event
        fields = ["description"]
        
class EventPrivacyForm(forms.ModelForm):
    PRIVACY_CHOICES = [
        ("Discoverable", "Discoverable"),
        ("Invite Only", "Invite Only"),
        ("Private (College)", "Private (College)"),
        ("Private (Organization)", "Private (Organization)"),
    ]
    
    privacy = forms.ChoiceField(
        choices=PRIVACY_CHOICES,
        required=False,
        initial="",
    )
    
    class Meta:
        model = Event
        fields = ["privacy"]

class EventLocationForm(forms.ModelForm):
    building_name = forms.CharField(max_length=200, required=False)
    street = forms.CharField(max_length=200, required=False)
    apt_suite_unit = forms.CharField(
        max_length=200, 
        required=False, 
        widget=forms.TextInput(attrs={'placeholder': 'Input your apt here (optional)'})
    )
    city = forms.CharField(max_length=200, required=False)
    state = forms.CharField(max_length=200, required=False)
    zip_code = forms.CharField(max_length=200, required=False)
    
    class Meta:
        model = Event
        fields = ["building_name", "street", "apt_suite_unit", "city", "state", "zip_code"]
        
class EventHeaderImageForm(forms.ModelForm):
    header_photo = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'custom-file-input'})
    )
    
    class Meta:
        model = Event
        fields = ["header_photo"]
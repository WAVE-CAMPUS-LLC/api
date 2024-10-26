from django import forms
from .models import HostApplication, Event, EventTicket
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
        
    # def __init__(self, *args, **kwargs):
    #     user = kwargs.pop("user", None)
    #     super().__init__(*args, **kwargs)
        
    #     PRIVACY_CHOICES = [
    #         ("Discoverable", "Discoverable"),
    #         ("Invite Only", "Invite Only"),
    #     ]
        
    #     if user:
    #         user_profile = UserProfile.objects.filter(user=user).first()
    #         if user_profile and user_profile.college:
    #             PRIVACY_CHOICES.append(("College Only", "College Only"))
            
    #         organizations = OrganizationMembership.objects.filter(user=user)
    #         if organizations.exists():
    #             PRIVACY_CHOICES.append(("Organization Only", "Organization Only"))
                
    #     self.fields["privacy"].choices = PRIVACY_CHOICES

class EventTicketForm(forms.ModelForm):
    class Meta:
        model = EventTicket
        fields = [
            "ticket_name",
            "ticket_type",
            "ticket_price",
            "ticket_description",
            "ticket_quantity",
        ]

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
            "discoverability_level",
            "restricted_college",
            "restricted_organization",
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
            "privacy": forms.Select(attrs={"class": "event-privacy"}),
            "country": forms.Select(),
            "status": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        privacy = kwargs.pop("privacy", None)
        super(EventForm, self).__init__(*args, **kwargs)

        if user:
            # Check if user has a college
            user_profile = UserProfile.objects.filter(user=user).first()
            if user_profile and user_profile.college:
                # User is in a college, show college restriction option
                self.fields["restricted_college"].queryset = College.objects.filter(
                    collegeId=user_profile.college.collegeId
                )
            else:
                # User is not in a college, remove college restriction option
                self.fields.pop("restricted_college")

            # Check if user has organizations
            organizations = OrganizationMembership.objects.filter(
                user=user
            ).select_related("organization")
            if organizations.exists():
                # Show organizations in the queryset
                self.fields["restricted_organization"].queryset = (
                    Organization.objects.filter(
                        orgId__in=organizations.values_list("organization", flat=True)
                    )
                )
            else:
                # User has no organizations, remove organization restriction option
                self.fields.pop("restricted_organization")
            if privacy != "discoverable":
                self.fields.pop("discoverability_level")


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

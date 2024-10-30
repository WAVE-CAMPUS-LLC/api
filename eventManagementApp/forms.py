from django import forms
from .models import HostApplication, Event, PaidFreeTicket
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


class InvitationForm(forms.Form):
    invite_emails = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "id": "inviteEmails",
                "placeholder": "Enter email addresses separated by commas!",
                # temporary
                "value": "enoshlartey3@gmail.com, michaelabate819@gmail.com",
            }
        ),
        label="To",
    )
    invite_subject = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "id": "inviteSubject",
                "placeholder": "Set your subject line!",
                "value": "Help me test WAVE!!",
            }
        ),
        label="Subject",
    )
    invite_message = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "id": "inviteMessage",
                "value": "You have been invited to {{ event.title }}! Please view the attached PDF file for your ticket in QR Code format.",
            }
        ),
        label="Message",
        initial="You have been invited to an event! Please check the details in the attachment.",
    )


class EventTicketForm(forms.ModelForm):
    class Meta:
        model = PaidFreeTicket
        fields = [
            "ticket_name",
            "ticket_type",
            "ticket_price",
            "ticket_description",
            "ticket_quantity",
        ]


class PaidFreeTicketForm(forms.ModelForm):
    class Meta:
        model = PaidFreeTicket
        fields = [
            "ticket_name",
            "ticket_type",
            "ticket_price",
            "ticket_description",
            "ticket_quantity",
        ]

    def clean(self):
        cleaned_data = super().clean()
        ticket_type = cleaned_data.get("ticket_type")
        ticket_price = cleaned_data.get("ticket_price")

        # Validate ticket price for 'Priced' tickets
        if ticket_type == "Priced" and (ticket_price is None or ticket_price <= 0):
            self.add_error(
                "ticket_price",
                "Ticket price must be greater than zero for priced tickets.",
            )

        return cleaned_data

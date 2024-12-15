from django import forms
from .models import PaidFreeTicket
from django.utils.translation import gettext_lazy as _
from adminDashboardApp.models import College
from accountManagementApp.models import UserProfile
from collegeManagementApp.models import OrganizationMembership, Organization


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


class PaidFreeTicketForm(forms.ModelForm):
    class Meta:
        model = PaidFreeTicket
        fields = [
            "ticket_name",
            "ticket_price",
            "ticket_description",
            "ticket_quantity",
        ]

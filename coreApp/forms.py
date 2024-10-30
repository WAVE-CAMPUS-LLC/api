from django import forms
from django.utils.translation import gettext_lazy as _

from eventManagementApp.models import RSVPTicket

class RSVPForm(forms.ModelForm):
    class Meta:
        model = RSVPTicket
        fields = ["email", "first_name", "last_name", "display_on_guestlist"]
from django import forms
from django.utils.translation import gettext_lazy as _

from eventTicketsApp.models import RSVPTicket

class RSVPForm(forms.ModelForm):
    class Meta:
        model = RSVPTicket
        fields = ["email", "first_name", "last_name", "display_on_guestlist"]
        
    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if user and user.is_authenticated:
            self.fields['first_name'].required = False
            self.fields['last_name'].required = False
            self.fields['email'].required = False
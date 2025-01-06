from django.utils import timezone
from django import forms
from adminDashboardApp.models import College
from django.utils.translation import gettext_lazy as _


class EditCampusAsManagerForm(forms.ModelForm):
    """
    The `EditCampusAsManagerForm` class is a form that allows users to update their profile information, including their status and country.
    """

    class Meta:
        model = College
        fields = [
            "name",
            "address",
            "city",
            "state",
            "zip_code",
            "country",
            "contact_website",
            "motto",
            "logo",
        ]

        labels = {
            "name": _("College Name"),
            "address": _("Address"),
            "city": _("City"),
            "state": _("State"),
            "zip_code": _("Zip Code"),
            "country": _("Country"),
            "contact_website": _("Website"),
            "motto": _("Motto"),
            "logo": _("Logo"),
        }
        widgets = {"state": forms.Select(), "country": forms.Select()}

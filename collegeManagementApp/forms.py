from django import forms
from .models import College, Organization


class CollegeForm(forms.ModelForm):
    class Meta:
        model = College
        fields = [
            "name",
            "address",
            "city",
            "state",
            "zip_code",
            "country",
            "logo",
            "motto",
            "contact_website",
        ]
        
        widgets = {
            "state": forms.Select(), 
            "country": forms.Select()
        }

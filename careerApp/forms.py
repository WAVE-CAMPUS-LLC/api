from django import forms
from .models import CareerRoleApplication

class CareerRoleApplicationForm(forms.ModelForm):
    class Meta:
        model = CareerRoleApplication
        fields = ['role','applicantFirstName','applicantLastName','applicantEmail','applicantResume','applicantCoverLetter']
from django import forms
from .models import CareerRoleApplication


class CareerRoleApplicationForm(forms.ModelForm):
    class Meta:
        model = CareerRoleApplication
        fields = [
            "applicantFirstName",
            "applicantLastName",
            "applicantEmail",
            "applicantPhone",
            "applicantGithub",
            "applicantPortfolio",
            "applicantLinkedIn",
            "applicantResume",
            "applicantLocation",
            "applicantCoverLetter",
            "whatYouBring",
            "workAuthorization",
        ]

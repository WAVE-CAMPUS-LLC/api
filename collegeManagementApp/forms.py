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

        widgets = {"state": forms.Select(), "country": forms.Select()}


class JoinCollegeForm(forms.Form):
    email = forms.EmailField(
        label="College Email",
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter your college email",
                "required": "required",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        self.college = kwargs.pop("college", None)
        super().__init__(*args, **kwargs)

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if self.college:
            email_domain = email.split("@")[1]

            if self.college.email_domain not in email_domain:
                raise forms.ValidationError(
                    f"Please use your school email ending in @{self.college.email_domain}"
                )
        return email


class VerifyCollegeJoinForm(forms.Form):
    code = forms.CharField(
        label="Code",
        max_length=6,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter the verification code",
                "required": "required",
            }
        ),
    )


class OrganizationForm(forms.ModelForm):
    class Meta:
        model = Organization
        fields = [
            "name",
            "description",
            "privacy",
            "logo",
            "contact_name",
            "contact_email",
            "contact_website",
            "instagram",
        ]

        widgets = {"privacy": forms.Select()}

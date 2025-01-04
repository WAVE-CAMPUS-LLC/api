from django import forms
from .models import College, CollegeRequest, Organization, Membership
from django.forms.widgets import ClearableFileInput

class CustomClearableFileInput(ClearableFileInput):
    template_name = 'custom_clearable_file_input.html'  # Custom template for the widget


class CollegeRequestForm(forms.ModelForm):
    name = forms.CharField(
        label="College Name",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Tennessee State University, Fisk University, etc.",
                "required": "required",
            }
        ),
    )
    yourEmail = forms.EmailField(
        label="Your Email",
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "example@college.edu",
                "required": "required",
            }
        ),
    )

    class Meta:
        model = CollegeRequest
        fields = ["name", "yourName", "yourEmail"]


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
        self.user = kwargs.pop("user", None) 
        super().__init__(*args, **kwargs)

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if self.college:
            email_domain = email.split("@")[1]

            if self.college.email_domain not in email_domain:
                raise forms.ValidationError(
                    f"Use school email ending in @{self.college.email_domain}"
                )
                
            user = self.user
            
            if Membership.objects.filter(college=self.college, user=user).exists():
                raise forms.ValidationError("You are already a member of this college")
        
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
        
class EditOrganizationForm(forms.ModelForm):
    class Meta:
        model = Organization
        fields = [
            "description",
            "privacy",
            "logo",
            "contact_name",
            "contact_email",
            "contact_website",
            "instagram",
        ]

        widgets = {
            "privacy": forms.Select(choices=Organization.PRIVACY_CHOICES),
            "logo": forms.ClearableFileInput(attrs={"class": "custom-file-input"})
        }
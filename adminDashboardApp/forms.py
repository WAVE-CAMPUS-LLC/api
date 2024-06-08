from django import forms
from django.contrib.auth.models import Permission, Group
from authenticationApp.models import CustomUser
from .models import Department, CareerRole


class CreateGroupForm(forms.ModelForm):
    permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )
    role_color = forms.CharField(
        label="Role Color",
        max_length=7,
        required=True,
        widget=forms.TextInput(attrs={"type": "color"}),
    )
    display_on_profile = forms.BooleanField(required=True, label="Profile display")

    class Meta:
        model = Group
        fields = ["name", "permissions", "role_color", "display_on_profile"]

    def save(self, commit=True):
        group = super().save(commit=False)
        if commit:
            group.save()
            group.permissions.set(self.cleaned_data["permissions"])
            group.role_color = self.cleaned_data['role_color']
            group.display_on_profile = self.cleaned_data['display_on_profile']
            group.save()
        return group


class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = [
            "name",
            "lead_name",
            "lead_email",
            "capacity",
            "location",
            "description",
        ]


class CareerRoleCreationForm(forms.ModelForm):
    class Meta:
        model = CareerRole
        fields = [
            "roleTitle",
            "roleDescription",
            "roleExpectations",
            "roleRequirements",
            "roleLocation",
            "roleType",
            "advertisementLength",
            "roleCapacity",
        ]

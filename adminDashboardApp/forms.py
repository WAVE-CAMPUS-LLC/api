from django import forms
from django.contrib.auth.models import Permission, Group
from authenticationApp.models import CustomUser
from .models import Department, CareerRole
from django.utils.translation import gettext_lazy as translate


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

    class Meta:
        model = Group
        fields = ["name", "permissions", "role_color",]

    def save(self, commit=True):
        group = super().save(commit=False)
        if commit:
            group.save()
            group.permissions.set(self.cleaned_data["permissions"])
            group.role_color = self.cleaned_data["role_color"]
            group.save()
        return group


class UpdateGroupForm(forms.ModelForm):
    name = forms.CharField(max_length=150, required=False, help_text="Name", label="Name")
    permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        help_text="Permissions",
        label="Permissions",
    )
    role_color = forms.CharField(
        max_length=7,
        required=True,
        widget=forms.TextInput(attrs={"type": "color"}),
        help_text="Role Color",
        label="Role Color"
    )
    
    class Meta:
        model = Group
        fields = ['name', 'permissions', 'role_color',]


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


class SuspendUserForm(forms.Form):
    hours = forms.IntegerField(label=translate("Hours"), min_value=0, max_value=23, initial=0)
    
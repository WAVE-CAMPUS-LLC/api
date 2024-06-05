from django import forms
from django.contrib.auth.models import Permission, Group
from authenticationApp.models import CustomUser
from .models import Department, CareerRole



class CreateRoleForm(forms.ModelForm):
    permissions = forms.ModelMultipleChoiceField(queryset=Permission.objects.all(), widget=forms.CheckboxSelectMultiple, required=False)
    
    class Meta:
        model = Group
        fields = ['name', 'permissions']


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

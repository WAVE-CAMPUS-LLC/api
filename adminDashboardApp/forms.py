from django import forms
from .models import Department, CareerRole


class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ['name', 'lead_name', 'lead_email', 'capacity', 'location', 'description']
        

class CareerRoleCreationForm(forms.ModelForm):
    class Meta:
        model = CareerRole
        fields = ['roleTitle', 'roleDescription', 'roleExpectations', 'roleRequirements', 'roleLocation', 'roleType', 'advertisementLength', 'roleCapacity']
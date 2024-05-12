from django import forms
from .models import Department


class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ['name', 'lead_name', 'lead_email', 'capacity', 'location', 'description']
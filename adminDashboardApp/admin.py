from django.contrib import admin
from .models import LoginHistoryModel, Department

class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'departmentID', 'lead_name', 'lead_email', 'capacity', 'location', 'description')

# Register your models here.
admin.site.register(Department, DepartmentAdmin)
admin.site.register(LoginHistoryModel)
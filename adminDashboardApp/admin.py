from django.contrib import admin
from .models import LoginHistoryModel, Department, CareerRole

class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'departmentID', 'lead_name', 'lead_email', 'capacity', 'location', 'description')
    
class CareersAdmin(admin.ModelAdmin):
    list_display = ('department', 'roleTitle', 'roleDescription', 'roleExpectations', 'roleRequirements', 'roleLocation', 'roleType', 'advertisementLength', 'roleCapacity')



# Register your models here.
admin.site.register(Department, DepartmentAdmin)
admin.site.register(CareerRole, CareersAdmin)
admin.site.register(LoginHistoryModel)
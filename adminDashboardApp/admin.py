from django.contrib import admin
from .models import College, LoginHistoryModel, Department, CareerRole, Newsroom


class DepartmentAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "departmentID",
        "lead_name",
        "lead_email",
        "capacity",
        "location",
        "description",
    )

@admin.register(College)
class CollegeAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "address",
        "city",
        "state",
        "zip_code",
        "country",
        "logo",
        "motto",
        "contact_website",
    )

class CareersAdmin(admin.ModelAdmin):
    list_display = (
        "department",
        "roleTitle",
        "roleDescription",
        "roleExpectations",
        "roleRequirements",
        "roleLocation",
        "roleType",
        "advertisementLength",
        "roleCapacity",
    )


class NewsroomAdmin(admin.ModelAdmin):
    # should we change this to match with the model and forms?
    list_display = (
        "title",
        "body",
        "headerImage",
        "imageOne",
        "imageTwo",
        "imageThree",
    )
    
    readonly_fields = ('created_at', 'created_by')

    list_filter = ("created_at", "created_by")

    search_fields = ("title",)


# Register your models here.
admin.site.register(Department, DepartmentAdmin)
admin.site.register(CareerRole, CareersAdmin)
admin.site.register(LoginHistoryModel)
admin.site.register(Newsroom, NewsroomAdmin)

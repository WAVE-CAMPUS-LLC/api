from django.contrib import admin
from .models import College, Organization


# Register your models here.
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


admin.site.register(College, CollegeAdmin)
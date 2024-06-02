from django.contrib import admin
from .models import HostApplication


# Register your models here.
class HostApplicationAdmin(admin.ModelAdmin):
    list_display = (
        "firstName",
        "lastName",
        "organizationName",
    )



admin.site.register(HostApplication, HostApplicationAdmin)
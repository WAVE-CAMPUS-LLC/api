from django.contrib import admin
from authenticationApp.admin import super_admin_restricted_site

from .models import InteractiveEventControl, GuestUser


# Register your models here.
class InteractiveEventControlAdmin(admin.ModelAdmin):
    list_display = (
        "event",
        "user",
        "guest",
        "interaction_type",
        "timestamp",
        "duration",
        "date",
    )


# class GuestUserAdmin(admin.ModelAdmin):
#     list_display = ("guestId", "created_at")
#     search_fields = ("guestId", "created_at")


super_admin_restricted_site.register(
    InteractiveEventControl, InteractiveEventControlAdmin
)
# super_admin_restricted_site.register(GuestUser, GuestUserAdmin)

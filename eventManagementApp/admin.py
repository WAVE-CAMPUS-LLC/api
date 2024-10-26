from django.contrib import admin
from .models import HostApplication, Event, EventPrivacy


# Register your models here.
class HostApplicationAdmin(admin.ModelAdmin):
    list_display = (
        "firstName",
        "lastName",
        "organizationName",
    )


class EventAdmin(admin.ModelAdmin):
    list_display = (
        "eventId",
        "title",
        "event_type",
        "date",
        "start_time",
        "end_time",
        "description",
        "privacy",
        "ticketing",
        "country",
        "building_name",
        "street",
        "apt_suite_unit",
        "city",
        "state",
        "zip_code",
        "contact_email",
        "contact_phone",
        "contact_website",
        "contact_instagram",
        "header_photo",
    )

class EventPrivacyAdmin(admin.ModelAdmin):
    list_display = (
        "event",
        "display_on_explore",
        "require_invitation",
        "restricted_college",
        "restricted_organization"
    )


admin.site.register(Event, EventAdmin)
admin.site.register(EventPrivacy, EventPrivacyAdmin)    
admin.site.register(HostApplication, HostApplicationAdmin)

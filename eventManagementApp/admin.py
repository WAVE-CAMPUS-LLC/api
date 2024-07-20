from django.contrib import admin
from .models import HostApplication, Event, EventTicket


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

class EventTicketAdmin(admin.ModelAdmin):
    list_display = ('event', 'type_name', 'type_quantity')

admin.site.register(Event, EventAdmin)
admin.site.register(EventTicket, EventTicketAdmin)
admin.site.register(HostApplication, HostApplicationAdmin)

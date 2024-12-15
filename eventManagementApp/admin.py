from django.contrib import admin
from .models import HostApplication, Event, EventPrivacy, HostProfile
from eventTicketsApp.models import RSVPTicket, PaidFreeTicket, Ticket


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
        "restricted_organization",
    )


class RSVPTicketAdmin(admin.ModelAdmin):
    list_display = (
        "event",
        "email",
        "first_name",
        "last_name",
        "created_at",
        "ticket_id",
    )


class PaidFreeTicketAdmin(admin.ModelAdmin):
    list_display = (
        "event",
        "ticket_id",
        "ticket_name",
        "ticket_price",
        "ticket_quantity",
        "ticket_description",
        # "created_at",
    )


class TicketAdmin(admin.ModelAdmin):
    list_display = (
        "ticketId",
        "user",
        "guestFirstName",
        "guestLastName",
        "guestEmail",
        "event",
        "status",
        "created_at",
        "qrCodeImage",
    )


class HostProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "stripe_account_id",
        # "bank_account_details",
        "cashapp_id",
        "google_pay_id",
        "apple_pay_id",
        
    )

admin.site.register(Ticket, TicketAdmin)
admin.site.register(HostProfile, HostProfileAdmin)


admin.site.register(Event, EventAdmin)
admin.site.register(EventPrivacy, EventPrivacyAdmin)
admin.site.register(RSVPTicket, RSVPTicketAdmin)
admin.site.register(PaidFreeTicket, PaidFreeTicketAdmin)
admin.site.register(HostApplication, HostApplicationAdmin)

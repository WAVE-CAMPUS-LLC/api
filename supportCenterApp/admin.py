from django.contrib import admin
from .models import SupportTicket

# Register your models here.
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ('ticket_id', 'email', 'created_at')
    search_fields = ('ticket_id', 'email')
    list_filter = ('status', 'created_at')


admin.site.register(SupportTicket, SupportTicketAdmin)
from django.contrib import admin
from .models import SupportTicket, FeedbackModel

# Register your models here.
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ('ticket_id', 'email', 'created_at')
    search_fields = ('ticket_id', 'email')
    list_filter = ('status', 'created_at')


class FeedbackModelAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'subject', 'created_at')
    search_fields = ('full_name', 'email')
    list_filter = ('email', 'created_at')

admin.site.register(SupportTicket, SupportTicketAdmin)
admin.site.register(FeedbackModel, FeedbackModelAdmin)
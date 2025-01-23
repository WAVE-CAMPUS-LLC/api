from authenticationApp.admin import super_admin_restricted_site
from django.contrib import admin
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from .models import SupportTicket, SupportTicketMessage, FeedbackModel

# Register your models here.
class SupportTicketMessageInline(admin.TabularInline):
    model = SupportTicketMessage
    extra = 1
    readonly_fields = ('sent_at', 'sender')

class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ('ticket_id', 'email', 'created_at', 'status', 'reply')
    search_fields = ('ticket_id', 'email')
    list_filter = ('status', 'created_at')
    inlines = [SupportTicketMessageInline]
# Fields that are editable in the admin detail view
    fields = ('status', 'reply')  # Added 'reply'

 # Make 'reply' editable and 'replied_at' automatically set when a reply is added
    def save_model(self, request, obj, form, change):
        if obj.reply and not obj.replied_at:  # Update replied_at if there is a new reply
            obj.replied_at = timezone.now()
        if 'reply' in form.changed_data:
            # Send an email to the user notifying them about the admin's reply
            subject = f"Reply to Your Support Ticket #{obj.ticket_id}"
            message = f"Dear {obj.email},\n\nYou have received a new reply to your support ticket:\n\n{form.cleaned_data['reply']}\n\nBest regards,\nSupport Team"
            recipient_email = obj.email
            

            send_mail(
                subject,
                message,
                settings.EMAIL_HOST_USER,  # From email address
                [recipient_email],  # Recipient's email address
                fail_silently=False,
            )
            print(f"Email sent to {recipient_email} for ticket {obj.ticket_id}.")

            SupportTicketMessage.objects.create(
                ticket=obj,
                sender=request.user,
                message=form.cleaned_data['reply']
            )
            print(f"Admin has replied to ticket {obj.ticket_id}.")
        super().save_model(request, obj, form, change)

class FeedbackModelAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'subject', 'created_at')
    search_fields = ('full_name', 'email')
    list_filter = ('email', 'created_at')

super_admin_restricted_site.register(SupportTicket, SupportTicketAdmin)
super_admin_restricted_site.register(FeedbackModel, FeedbackModelAdmin)
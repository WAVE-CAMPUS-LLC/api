from enum import unique
from django.utils import timezone
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.core.validators import validate_email

# Create your models here.
def generate_unique_ticket_id():
    import uuid
    return str(uuid.uuid4())[:10]

class SupportTicket(models.Model):
    TITLE_CHOICES = [
        ('help', 'Help & Support'),
        ('hacked_account', 'Hacked Account'),
        ('appeals', 'Appeals'),
        ('account_updates', 'Account Updates'),
        ('billing', 'Account Billing'),
        ('bugs', 'Bug Reports'),
        ('creators_support', 'Support for Creators'),
        ('privacy_support', 'Privacy Support'),
        ('community_support', 'Community Programs')
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True)
    title = models.CharField(_("How can we help you?"), max_length=20, choices=TITLE_CHOICES)
    email = models.EmailField(_("Email"))
    subject = models.CharField(_("Subject"), max_length=200)
    description = models.TextField(_("Description"), max_length=1000)
    status = models.CharField(max_length=20, default="Open")
    created_at = models.DateTimeField(auto_now_add=True)
    ticket_id = models.CharField(max_length=10, unique=True, default=generate_unique_ticket_id)
    
     # New fields for admin reply
    reply = models.TextField(_("Admin Reply"), max_length=2000, blank=True, null=True)
    replied_at = models.DateTimeField(_("Replied At"), blank=True, null=True)

    class Meta:
        default_permissions = () # Removing default permissions
        verbose_name = "Member Support Ticket"
        verbose_name_plural = "Member Support Tickets"
    
    def save(self, *args, **kwargs):
        # We generate a unique Identifier(ID) before saving the form to create the ticket. 
        if not self.ticket_id:
            self.ticket_id = generate_unique_ticket_id()
        # We update the replied_at field with the time the timestamp is added.
        if self.reply and not self.replied_at:
            self.replied_at = timezone.now()
        return super().save(*args, **kwargs)
    
    def __str__(self):
        return self.title
    
    
    def return_title(self):
        # Returns the verbose name of the title field based on its value.
        return dict(self.TITLE_CHOICES).get(self.title, self.title)
    
    def time_elapsed_since_created(self):
        time_now = timezone.now()
        time_elapsed = time_now - self.created_at
        days = time_elapsed.days
        hours, rem = divmod(time_elapsed.seconds, 3600)
        minutes, seconds = divmod(rem, 60)
        
        if days == 0:
            if hours == 0:
                if minutes == 0:
                    if seconds == 1:
                        return f'{seconds} second ago'
                    elif seconds > 1:
                        return f'{seconds} seconds ago'
                if minutes == 1:
                    if seconds < 1:
                        return f'{minutes} minute ago'
                    if seconds == 1:
                        return f'{minutes} minute {seconds} second ago'
                    elif seconds > 1:
                        return f'{minutes} minute {seconds} seconds ago'
                elif minutes > 1:
                    if seconds < 1:
                        return f'{minutes} minutes ago'
                    if seconds == 1:
                        return f'{minutes} minutes {seconds} second ago'
                    elif seconds > 1:
                        return f'{minutes} minutes {seconds} seconds ago'
            elif hours == 1:
                if minutes == 0:
                    return f'{hours} hour ago'
                elif minutes == 1:
                    return f'{hours} hour {minutes} minute ago'
                elif minutes > 1:
                    return f'{hours} hour {minutes} minutes ago'
            elif hours > 1:
                if minutes == 1:
                    return f'{hours} hours {minutes} minute ago'
                elif minutes > 1:
                    return f'{hours} hours {minutes} minutes ago'

        else:
            if days == 1:
                return f'{days} day ago'
            else:
                return f'{days} days ago'
            
class SupportTicketMessage(models.Model):
    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    message = models.TextField()
    sent_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['sent_at']  # Display messages in the order they were sent

    def __str__(self):
        return f"Message by {self.sender} on {self.sent_at}"
           
            
# A model for the feedback page. 
class FeedbackModel(models.Model):
    full_name = models.CharField(_("Full Name"), max_length=100, blank=False)
    email = models.EmailField(_("Email"), max_length=254, blank=False, validators=[validate_email])
    subject = models.CharField(_("Subject"), max_length=200, blank=False)
    body = models.TextField(_("Body"), blank=False, max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        default_permissions = () # Removing default permissions
        verbose_name = "User Feedback"
        verbose_name_plural = "User Feedbacks"
        
    def __str__(self):
        return self.subject
from enum import unique
from django.utils import timezone
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings

from wave_v1 import settings

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
    
    def save(self, *args, **kwargs):
        # We generate a unique Identifier(ID) before saving the form to create the ticket. 
        if not self.ticket_id:
            self.ticket_id = generate_unique_ticket_id()
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
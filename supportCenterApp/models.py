from enum import unique
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings

from wave_v1 import settings

# Create your models here.
def generate_unique_ticket_id():
    import uuid
    return str(uuid.uuid4())[:7]

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
    ticket_id = models.CharField(max_length=7, unique=True, default=generate_unique_ticket_id)
    
    def save(self, *args, **kwargs):
        # We generate a unique Identifier(ID) before saving the form to create the ticket. 
        if not self.ticket_id:
            self.ticket_id = generate_unique_ticket_id()
        return super().save(*args, **kwargs)
    
    def __str__(self):
        return self.title
    


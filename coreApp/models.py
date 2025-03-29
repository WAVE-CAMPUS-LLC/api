from django.db import models
from django.conf import settings
import uuid
from eventManagementApp.models import Event

# Create your models here.
class Visitor(models.Model):
    ip_address = models.GenericIPAddressField(unique=True)
    first_visit = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.ip_address

class EventView(models.Model):
    """
    Tracks unique views of events by users or anonymous visitors.
    Used to ensure each user/session only counts once toward an event's view count.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='event_views')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, 
                            null=True, blank=True, related_name='event_views')
    session_key = models.CharField(max_length=40, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        # Ensure a user can only view an event once (for counting purposes)
        # For anonymous users, use session key and IP address
        constraints = [
            models.UniqueConstraint(
                fields=['event', 'user'],
                condition=models.Q(user__isnull=False),
                name='unique_user_event_view'
            ),
            models.UniqueConstraint(
                fields=['event', 'session_key', 'ip_address'],
                condition=models.Q(user__isnull=True),
                name='unique_session_ip_event_view'
            ),
        ]
        
    def __str__(self):
        if self.user:
            return f"{self.user.username} viewed {self.event.title}"
        return f"Anonymous viewed {self.event.title}"
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.db import models
from django.conf import settings
from django.utils import timezone
from accountManagementApp.models import UserProfile  # Import the UserRole model from the account management app

# Create your models here.

# Create your models here.
class LoginHistoryModel(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    email = models.EmailField()
    login_time = models.DateTimeField(default=timezone.now)
    logout_time = models.DateTimeField(null=True, blank=True)
    ip_address = models.CharField(max_length=50)
    session_duration_minutes = models.IntegerField(null=True, blank=True)
    session_duration_seconds = models.IntegerField(null=True, blank=True)  # New field for session duration in seconds
    role = models.ForeignKey(UserProfile, on_delete=models.CASCADE, null=True, blank=True)  # Add a foreign key to the UserRole model


    def save(self, *args, **kwargs):
        if self.logout_time:
            session_duration = self.logout_time - self.login_time
            self.session_duration_minutes = session_duration.total_seconds() // 60
            self.session_duration_seconds = session_duration.total_seconds() % 60  # Calculate remaining seconds
            print(f'Session duration: {session_duration}')
        super().save(*args, **kwargs)
        
    @property
    def is_active(self):
        return not self.logout_time
    
    def end_session(self):
        if not self.logout_time:
            self.logout_time = timezone.now()
            self.save()
    
    def __str__(self):
        return f'{self.user} - {self.login_time} - Active: {self.is_active}'
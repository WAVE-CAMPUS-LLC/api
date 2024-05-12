from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid

# Create your models here.
class Department(models.Model):
    name = models.CharField("Department Name", max_length=100)
    departmentID = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    lead_name = models.CharField("Department Lead", max_length=100)
    lead_email = models.EmailField("Lead Email")
    capacity = models.IntegerField("Capacity")
    location = models.CharField("Location", max_length=300)
    description = models.TextField("Description")
    
    def __str__(self):
        return self.name


class LoginHistoryModel(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    email = models.EmailField()
    login_time = models.DateTimeField(default=timezone.now)
    logout_time = models.DateTimeField(null=True, blank=True)
    ip_address = models.CharField(max_length=50)
    session_duration_minutes = models.IntegerField(null=True, blank=True)
    session_duration_seconds = models.IntegerField(null=True, blank=True)  # New field for session duration in seconds

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
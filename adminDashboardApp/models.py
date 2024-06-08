from datetime import timedelta
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.models import Group
import uuid
from authenticationApp.models import CustomUser



# Create your models here.

class Department(models.Model):
    name = models.CharField("Department Name", max_length=100)
    departmentID = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    lead_name = models.CharField("Department Lead", max_length=100)
    lead_email = models.EmailField("Lead Email")
    capacity = models.IntegerField("Capacity")
    location = models.CharField("Location", max_length=300)
    description = models.TextField("Description")
    
    
    class Meta:
        default_permissions = ()
    
    def __str__(self):
        return self.name
    
class CareerRole(models.Model):
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="admin_dashboard_career_roles")
    roleID = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    roleTitle = models.CharField("Name",max_length=100)
    roleDescription = models.TextField("Description")
    # companyOverview = models.TextField("Company Summary")
    roleExpectations = models.TextField("What's expected")
    roleRequirements = models.TextField("Requirements")
    roleLocation = models.CharField("Role Location", max_length=100)
    roleType = models.CharField("Role Type", max_length=20, choices=[("Remote", "remote"), ("In-person", "in-person")])
    # roleExperience = models.TextField("What you need to have")
    advertisementLength = models.IntegerField("Advertisement Length (in days)")
    advertisementStartDate = models.DateField("Advertisement Start Date", default=timezone.now)
    roleCapacity = models.CharField("Role Capacity", max_length=20, choices=[("Full-Time", "full-time"), ("Part-Time", "part-time")])

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True)
    
    def is_ad_expired(self):
        expiry_date = self.advertisementStartDate + timedelta(days=self.advertisementLength)
        return expiry_date <= timezone.now()
    
    class Meta:
        default_permissions = () # Removing default permissions
    
    def __str__(self):
        return self.roleTitle


class LoginHistoryModel(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    email = models.EmailField()
    login_time = models.DateTimeField(default=timezone.now)
    logout_time = models.DateTimeField(null=True, blank=True)
    ip_address = models.CharField(max_length=50)
    session_duration_minutes = models.IntegerField(null=True, blank=True)
    session_duration_seconds = models.IntegerField(null=True, blank=True)  # New field for session duration in seconds
    role = models.CharField(max_length=4, null=True, blank=True) # New field for user role


    def save(self, *args, **kwargs):
        if self.logout_time:
            session_duration = self.logout_time - self.login_time
            self.session_duration_minutes = session_duration.total_seconds() // 60
            self.session_duration_seconds = session_duration.total_seconds() % 60  # Calculate remaining seconds
            print(f'Session duration: {session_duration}')

        # set the role
        
        if not self.role:
            try:
                user_info = CustomUser()    
                self.role = user_info.role
            except CustomUser.DoesNotExist:
                self.role = 'user' # default role
        super().save(*args, **kwargs)
        
    @property
    def is_active(self):
        return not self.logout_time
    
    def end_session(self):
        if not self.logout_time:
            self.logout_time = timezone.now()
            self.save()
    
    class Meta:
        default_permissions = () # Removing default permissions
    
    def __str__(self):
        return f'{self.user} - {self.login_time} - Active: {self.is_active}'
    
    


class Permission(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField()
    
    class Meta:
        default_permissions = () # Removing default permissions
        permissions = [
            # Member Permissions
            ('view_profile_overview', 'View profile overview - WAVE.'),
            ('view_account_settings', 'View account settings - WAVE.'),
            ('view_support_portal', 'View support portal - WAVE.'),
            
            
            # Super Admin Permissions
            ('view_users', 'View users - WAVE.'), # Regular Admin
            ('manage_users', 'Manage users - WAVE.'), # Super Admin
            
            
            ('view_applications', 'View applications - WAVE.'), # Regular admin
            ('manage_applications', 'Manage applications - WAVE.'), # Super admin
            
            ('view_departments', 'View departments - WAVE.'), # Regular admin
            ('manage_departments', 'Manage departments - WAVE.'),
            
            
            # Event Manager
            ('view_all_events', 'View all events - WAVE.'),
            ('manage_all_events', 'Manage all events - WAVE.'),
            
            
            # Support Staff
            ('view_support_tickets', 'View support tickets - WAVE.'),
            ('manage_support_tickets', 'Manage support tickets - WAVE.'),
            
            
            # Event Host Member
            ('create_event', 'Create events - WAVE.'),
            ('manage_host_event', 'Manage host event - WAVE.'),
            ('view_host_event', 'View host event - WAVE.')
        ]
    
    
    def __str__(self):
        return self.name
    
    
    
class Group(models.Model):
    name = models.CharField(max_length=100)
    permissions = models.ManyToManyField(Permission)
    role_color = models.CharField(max_length=7, blank=True, null=True)
    display_on_profile = models.BooleanField(default=False)

    def __str__(self):
        return self.name
    
    
    
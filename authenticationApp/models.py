import datetime
from datetime import timedelta
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, Group
from django.utils import timezone
import uuid
import threading
from django.dispatch import receiver
from django.db.models.signals import pre_save, post_save
from django.utils.translation import gettext_lazy as _

from accountManagementApp.models import UserProfile


from .managers import CustomUserManager


# Create your models here.
class CustomUser(AbstractBaseUser, PermissionsMixin):
    GENDER_OPTIONS = [
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other')
    ]
    
    first_name = models.CharField(
        _("First Name"),
        max_length=50,
        blank=False,
        null=False,
        help_text=(_("First Name")),
    )
    last_name = models.CharField(
        _("Last Name"),
        max_length=50,
        blank=False,
        null=False,
        help_text=(_("Last Name")),
    )
    email = models.EmailField(
        _("Email"), unique=True, blank=False, null=False, help_text=(_("Email"))
    )
    username = models.CharField(
        _("Username"),
        max_length=15,
        blank=False,
        null=False,
        unique=True,
        help_text=(_("Username")),
    )
    phone_number = models.CharField(
        _("Phone Number"),
        max_length=15,
        blank=False,
        null=False,
        unique=False,
        help_text=(_("Phone Number")),
    )
    
    # Birthday Information
    birthday_day = models.PositiveIntegerField(_("Day"), null=True, blank=True)
    birthday_month = models.PositiveIntegerField(_("Month"), null=True, blank=True)
    birthday_year = models.PositiveIntegerField(_("Year"), null=True, blank=True)

    date_joined = models.DateField(auto_now_add=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    
    # The generation of a random user id for every user that signs up. 
    user_id = models.UUIDField(_("User ID"), default=uuid.uuid4, editable=False, unique=True)
    
    
    is_suspended = models.BooleanField(default=False)
    suspension_end_date = models.DateTimeField(null=True, blank=True)

    user_preferences_completed = models.BooleanField(default=False, null=False)
    
    def suspend(self, hours):
        suspend_group, created = Group.objects.get_or_create(name="Suspend")
        member_group = Group.objects.get(name="Member")
        self.groups.remove(member_group)
        self.groups.add(suspend_group)
        self.is_suspended = True
        self.suspension_end_date = timezone.now() + timedelta(hours=hours)
        self.save()
        
    def remove_suspension_OR_ban(self):
        if self.is_suspended or self.is_banned:
            suspend_group = Group.objects.get(name="Suspend")
            member_group = Group.objects.get(name="Member")
            
            if self.is_suspended:
                self.groups.remove(suspend_group)
                self.is_suspended = False
                self.suspension_end_date = None
                
            self.groups.add(member_group)
            self.save()
        
    

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = [
        "first_name",
        "last_name",
        "username",
        "phone_number",
    ]
    
    # user_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    class Meta:
        default_permissions = () # Removing default permissions
        
        
        verbose_name = "Member Account"
        verbose_name_plural = "Member Accounts"
        
        

    def __str__(self):
        return self.email

@receiver(pre_save, sender=CustomUser)
def generate_user_id(sender, instance, **kwargs):
    if not instance.user_id:
        instance.user_id = uuid.uuid4()
        

@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

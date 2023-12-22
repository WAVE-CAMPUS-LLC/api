from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


from .managers import CustomUserManager


# Create your models here.
class CustomUser(AbstractBaseUser, PermissionsMixin):
    first_name = models.CharField(_("First Name"),max_length=100)
    last_name = models.CharField(_("Last Name"),max_length=100)
    email = models.EmailField(_("Email"), unique=True)
    birthday = models.DateField(_("Birthday"),null=True, blank=False)
    gender = models.CharField(_("Gender"),max_length=10)
    phone_number = models.CharField(_("Phone Number"),max_length=15, blank=True, unique=False)
    
    date_joined = models.DateField(auto_now_add=True)
    
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    
    objects = CustomUserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'birthday', 'gender', 'phone_number',]
    
    class Meta:
        verbose_name = "Current Waver"
        verbose_name_plural = 'Current Wavers'
    
    
    def __str__(self):
        return self.email
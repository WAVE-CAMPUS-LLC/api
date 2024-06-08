import random
import string
from django.db import models
from django.utils.translation import gettext_lazy as translate
from django.conf import settings
from django.utils import timezone

# Create your models here.
class UserProfile(models.Model):
    ROLES = [
        ('host', 'Host'),
        ('user', 'User'), # no admin field here, because this is an extension of AUTH_USER_MODEL
    ]
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    # user_tag = models.CharField(primary_key = True, max_length=4, editable=False)
    status = models.TextField(blank=True)
    country = models.CharField(max_length=100,blank=True)
    role = models.CharField(max_length=4, choices=ROLES, default='user')
    
    class Meta:
        default_permissions = () # Removing default permissions
        
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"
        
        
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        
    
    def __str__(self):
        return self.user.email    

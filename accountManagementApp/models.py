from django.db import models
from django.utils.translation import gettext_lazy as translate
from django.conf import settings
from django.contrib.auth.models import Group


# Create your models here.
class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    status = models.TextField(blank=True)
    country = models.CharField(max_length=100,blank=True)
    group = models.ManyToManyField(Group, related_name='user_group')
    
    class Meta:
        default_permissions = ()
        
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"
        
        
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        
    
    def __str__(self):
        return self.user.email    

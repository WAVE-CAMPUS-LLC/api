from django.db import models
from django.utils.translation import gettext_lazy as translate
from django.conf import settings
from authenticationApp.models import CustomUser


# Create your models here.
class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    status = models.TextField(blank=True)
    country = models.CharField(max_length=100,blank=True)
    
    class Meta:
        verbose_name = "Waver Profile"
        verbose_name_plural = "Waver Profiles"
    
    def __str__(self):
        return self.user.email    
    
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
        ('user', 'User'),
    ]
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    user_tag = models.CharField(primary_key = True, max_length=4, editable=False)
    status = models.TextField(blank=True)
    country = models.CharField(max_length=100,blank=True)
    role = models.CharField(max_length=4, choices=ROLES, default='user')
    
    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"
    
    def save(self, *args, **kwargs):
        if not self.user_tag:
            self.user_tag = self.generate_unique_user_tag()
        super().save(*args, **kwargs)
        
    def generate_unique_user_tag(self):
        while True:
            user_tag = self.generate_random_code()
            if not UserProfile.objects.filter(user_tag=user_tag).exists():
                return user_tag
    def generate_random_code(self):
        return ''.join(random.choices(string.ascii_letters + string.digits, k=4))
    
    def __str__(self):
        return self.user.email    

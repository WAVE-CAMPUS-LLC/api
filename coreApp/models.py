from django.db import models

# Create your models here.
class Visitor(models.Model):
    ip_address = models.GenericIPAddressField(unique=True)
    first_visit = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.ip_address
import uuid
from django.db import models

class HostApplication(models.Model):
    EVENT_TYPE_CHOICES = [
        ('conference', 'Conference'),
        ('workshop', 'Workshop'),
        ('seminar', 'Seminar'),
        ('webinar', 'Webinar'),
        ('networking', 'Networking Event'),
    ]

    firstName = models.CharField(verbose_name="First Name", max_length=70)
    lastName = models.CharField(verbose_name="Last Name", max_length=70)
    email = models.EmailField(verbose_name="Email")
    phone = models.CharField(verbose_name="Phone", max_length=10)
    
    organizationName = models.CharField(verbose_name="Organization Name", max_length=150)
    organizationEmail = models.EmailField(verbose_name="Organization Email")
    organizationLocation = models.CharField(verbose_name="Organization Location", max_length=150)
    
    eventTypes = models.ManyToManyField('EventType', related_name='applications')
    
    eventHostedAnnually = models.CharField(verbose_name="How many events do you plan on hosting annually?", max_length=100)
    eventPopulation = models.CharField(verbose_name="How many people do you expect at each event?", max_length=1000)
    
    created_at = models.DateTimeField(auto_now_add=True)
    applicationId = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    
    def __str__(self):
        return f'{self.firstName} {self.lastName}'

class EventType(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name

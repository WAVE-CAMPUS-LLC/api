from django.db import models
from django.contrib.auth import get_user_model
import datetime
import uuid

from eventManagementApp.models import Event
from authenticationApp.models import CustomUser

# Create your models here.
User = get_user_model()


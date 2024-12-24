from .models import UserProfile
from authenticationApp.admin import super_admin_restricted_site
# Register your models here.


super_admin_restricted_site.register(UserProfile)
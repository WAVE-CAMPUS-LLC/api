from authenticationApp.admin import super_admin_restricted_site
from django.contrib import admin
from .models import CampusManagerInvite


# Register your models here.
class CampusManagerInviteAdmin(admin.ModelAdmin):
    list_display = ("college", "email", "token", "invited_at", "accepted")


super_admin_restricted_site.register(CampusManagerInvite, CampusManagerInviteAdmin)
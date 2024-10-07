from django.contrib import admin
from .models import CampusManagerInvite


# Register your models here.
@admin.register(CampusManagerInvite)
class CampusManagerInviteAdmin(admin.ModelAdmin):
    list_display = ("college", "email", "token", "invited_at", "accepted")

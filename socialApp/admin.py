from django.contrib import admin
from .models import FriendRequest


# Register your models here.
class FreindRequestAdmin(admin.ModelAdmin):
    list_display = ("sender", "receiver", "status")


admin.site.register(FriendRequest, FreindRequestAdmin)

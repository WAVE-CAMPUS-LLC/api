from django.contrib import admin
from .models import Crew, CrewMember, CrewRequest, FriendRequest


# Register your models here.
class FreindRequestAdmin(admin.ModelAdmin):
    list_display = ("sender", "receiver", "status")


@admin.register(CrewMember)
class CrewMemberAdmin(admin.ModelAdmin):
    list_display = ("crew", "user", "is_admin") 
    

@admin.register(CrewRequest)
class CrewRequestAdmin(admin.ModelAdmin):
    list_display = ("sender", "receiver", "crew", "status")
    
@admin.register(Crew)
class CrewAdmin(admin.ModelAdmin):
    list_display = ("name", "created_by", "created_at")

admin.site.register(FriendRequest, FreindRequestAdmin)

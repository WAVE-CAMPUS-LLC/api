from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group #Importing default so I can unregister it in the admin panel. 

from .forms import CustomUserJoinForm, CustomUserChangeForm
from .models import CustomUser


# Register your models here.
class CustomUserAdmin(UserAdmin):
    add_form = CustomUserJoinForm
    form = CustomUserChangeForm
    model = CustomUser
    list_display = ("first_name", "last_name", "email", "is_active",)
    list_filter = ("email", "last_name", )
    readonly_fields = ("date_joined", "user_id", "birthday")
    
    fieldsets = (
        ("Account Information", {"fields": (("first_name", "last_name"), "email", "password", "user_id", "birthday", "gender")}),
        ("Access Data", {"fields": ("date_joined","last_login",)}),
        ("Permissions", {"fields": ("is_staff", "is_active", "groups", "user_permissions")}),
    )
    
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "email", "password1", "password2", "is_staff","first_name", "last_name",  "phone_number",
                "is_active", "groups", "user_permissions"
            )}
        ),
    )
    
    search_fields = ("email", )
    ordering = ("email", )
    
    
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.unregister([Group])
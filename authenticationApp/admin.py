from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group #Importing default so I can unregister it in the admin panel. 
from django.core.exceptions import PermissionDenied
from .forms import CustomUserJoinForm, CustomUserChangeForm
from .models import CustomUser
from django.shortcuts import redirect


# Register your models here.
class CustomUserAdmin(UserAdmin):
    add_form = CustomUserJoinForm
    form = CustomUserChangeForm
    model = CustomUser
    list_display = ("first_name", "last_name", "email", "is_active",)
    list_filter = ("email", "last_name", )
    readonly_fields = ("date_joined",)
    
    fieldsets = (
        ("Account Information", {"fields": (("first_name", "last_name"), "email", ("username","birthday", "age"),  "password", "email_verified", "customer_id", "connectAccountCreated", "connectAccountID" )}),
        ("Access Data", {"fields": ("date_joined","last_login",)}),
        ("Permissions", {"fields": ("is_staff", "is_active", "groups", "user_permissions")}),
    )
    
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "email", "password1", "password2", "is_staff","first_name", "last_name",  "phone_number", "birthday",
                "is_active", "groups", "user_permissions"
            )}
        ),
    )
    
    search_fields = ("email", "username")
    ordering = ("email", "username")
    

class SuperAdminRestrictedAdminSite(admin.AdminSite):
    site_header = "Super Admin Restricted Admin Site"
    site_title = "Super Admin Restricted Admin Site"
    index_title = "Welcome to the Super Admin Restricted Admin Site"
    
    def has_permission(self, request):
        if not request.user.is_authenticated:
            return False
        
        if request.user.is_superadmin:
            return True
            
        
        raise PermissionDenied("You do not have permission to access this area.")
        # return redirect("core:explore")

super_admin_restricted_site = SuperAdminRestrictedAdminSite(name="super_admin_restricted_site")

super_admin_restricted_site.register(CustomUser, CustomUserAdmin)

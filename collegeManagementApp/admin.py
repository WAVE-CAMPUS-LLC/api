from django.contrib import admin
from .models import CollegeRequest, Organization, Membership
from authenticationApp.admin import super_admin_restricted_site


# Register your models here.
class CollegeRequestAdmin(admin.ModelAdmin):
    list_display = ("name", "yourName", "yourEmail")

class OrganizationAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "description",
        "privacy",
        "logo",
        "contact_name",
        "contact_email",
        "contact_website",
        "instagram",
    )

class MembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "college", "date_joined")


super_admin_restricted_site.register(Organization, OrganizationAdmin)
super_admin_restricted_site.register(Membership, MembershipAdmin)
super_admin_restricted_site.register(CollegeRequest, CollegeRequestAdmin)

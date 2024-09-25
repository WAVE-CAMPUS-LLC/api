from django.contrib import admin
from .models import CollegeRequest, Organization, Membership


# Register your models here.
@admin.register(CollegeRequest)
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


admin.site.register(Organization, OrganizationAdmin)
admin.site.register(Membership, MembershipAdmin)

from django.contrib import admin
from .models import College, Organization, Membership


# Register your models here.
class CollegeAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "address",
        "city",
        "state",
        "zip_code",
        "country",
        "logo",
        "motto",
        "contact_website",
    )


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


admin.site.register(College, CollegeAdmin)
admin.site.register(Organization, OrganizationAdmin)
admin.site.register(Membership, MembershipAdmin)

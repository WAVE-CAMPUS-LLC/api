from authenticationApp.admin import super_admin_restricted_site
from django.contrib import admin

from .models import CareerRoleApplication


# Register your models here.
class CareerAppAdmin(admin.ModelAdmin):
    list_display = (
        "applicantFirstName",
        "applicantLastName",
        "applicantEmail",
        "applicantPhone",
        "applicantGithub",
        "applicantPortfolio",
        "applicantLinkedIn",
        "applicantResume",
        "applicantLocation",
        "applicantCoverLetter",
        "whatYouBring",
        "workAuthorization",
    )


super_admin_restricted_site.register(CareerRoleApplication, CareerAppAdmin)

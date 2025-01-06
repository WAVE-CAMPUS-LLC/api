from authenticationApp.admin import super_admin_restricted_site
from django.contrib import admin

from .models import Blog

# Register your models here.
class BlogAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "body",
        "imageOne",
        "imageTwo",
        "imageThree",
    )
    

super_admin_restricted_site.register(Blog, BlogAdmin)
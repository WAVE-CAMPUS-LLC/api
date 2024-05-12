from django.contrib import admin
from .models import LoginHistoryModel, Department

# Register your models here.
admin.site.register(Department)
admin.site.register(LoginHistoryModel)
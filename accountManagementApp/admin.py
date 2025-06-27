from .models import UserProfile, AccountDeletionReason
from authenticationApp.admin import super_admin_restricted_site
from django.contrib import admin
# Register your models here.


@admin.register(AccountDeletionReason)
class AccountDeletionReasonAdmin(admin.ModelAdmin):
    list_display = ['username', 'user_email', 'deleted_at', 'platform', 'reason_preview']
    list_filter = ['deleted_at', 'platform']
    search_fields = ['username', 'user_email', 'user_id', 'reason']
    readonly_fields = ['user_email', 'username', 'user_id', 'deleted_at', 'reason', 'platform', 'user_agent']
    ordering = ['-deleted_at']
    
    def reason_preview(self, obj):
        return obj.reason[:100] + "..." if len(obj.reason) > 100 else obj.reason
    reason_preview.short_description = "Reason (Preview)"
    
    def has_add_permission(self, request):
        return False  # Don't allow manual creation
    
    def has_change_permission(self, request, obj=None):
        return False  # Don't allow editing
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser  # Only superusers can delete


super_admin_restricted_site.register(UserProfile)
super_admin_restricted_site.register(AccountDeletionReason, AccountDeletionReasonAdmin)
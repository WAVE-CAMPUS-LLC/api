from django.core.management.base import BaseCommand
from django.contrib.auth.models import Permission, ContentType
from accountManagementApp.models import UserProfile


class Command(BaseCommand):
    help = 'Remove default permissions for UserProfile model'

    def handle(self, *args, **kwargs):
        content_type = ContentType.objects.get_for_model(UserProfile)
        permissions = Permission.objects.filter(content_type=content_type, codename__in=[
            'add_userprofile', 'change_userprofile', 'delete_userprofile', 'view_userprofile'
        ])
        count = permissions.count()
        permissions.delete()
        self.stdout.write(self.style.SUCCESS(f'Successfully removed {count} default permissions for UserProfile model'))
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Permission, ContentType
from django.apps import apps

class Command(BaseCommand):
    help = 'Remove default permissions for all models in the specified app'

    def handle(self, *args, **kwargs):
        app_label = 'eventManagementApp'  # Replace with your actual app label
        app_config = apps.get_app_config(app_label)
        models = app_config.get_models()
        
        total_permissions_removed = 0
        
        for model in models:
            content_type = ContentType.objects.get_for_model(model)
            permissions = Permission.objects.filter(content_type=content_type, codename__in=[
                f'add_{model._meta.model_name}',
                f'change_{model._meta.model_name}',
                f'delete_{model._meta.model_name}',
                f'view_{model._meta.model_name}',
            ])
            count = permissions.count()
            permissions.delete()
            total_permissions_removed += count
            self.stdout.write(self.style.SUCCESS(
                f'Successfully removed {count} default permissions for {model._meta.model_name} model'
            ))
        
        self.stdout.write(self.style.SUCCESS(
            f'Total default permissions removed: {total_permissions_removed}'
        ))

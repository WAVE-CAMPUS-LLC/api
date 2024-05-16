from django.core.management.base import BaseCommand
from adminDashboardApp.models import Department

class Command(BaseCommand):
    help = "Deletes all existing departments from the database"
    
    def handle(self, *args, **kwargs):
        Department.objects.all().delete()
        self.stdout.write(self.style.SUCCESS('All existing departments have been deleted successfully.'))
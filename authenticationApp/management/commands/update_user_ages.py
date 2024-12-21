from django.core.management.base import BaseCommand
from authenticationApp.models import CustomUser
from datetime import date


class Command(BaseCommand):
    help = "Update the age of all users in the database"

    def handle(self, *args, **kwargs):
        today = date.today()
        users = CustomUser.objects.all()
        
        for user in users:
            if user.birthday:
                user.age = today.year - user.birthday.year - ((today.month, today.day) < (user.birthday.month, user.birthday.day))
                user.save()

        self.stdout.write(self.style.SUCCESS('Successfully updated user ages'))
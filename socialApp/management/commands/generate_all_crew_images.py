from django.core.management.base import BaseCommand
from socialApp.models import Crew
from socialApp.utilities.crew_tasks import generate_crew_image


class Command(BaseCommand):
    help = "Autogenerate images for all existing crews"

    def handle(self, *args, **options):
        crews = Crew.objects.all()
        for crew in crews:
            if not crew.crew_image:
                self.stdout.write(
                    f"Generating image for crew: {crew.name} (ID: {crew.crewId})"
                )
                generate_crew_image(crew.crewId)
                self.stdout.write(
                    self.style.SUCCESS(f"Image generated for {crew.name}")
                )
            else:
                self.stdout.write(f"Skipping {crew.name}, image already exists.")

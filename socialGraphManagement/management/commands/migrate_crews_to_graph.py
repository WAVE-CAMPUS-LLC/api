from django.core.management.base import BaseCommand
from socialApp.models import Crew, CrewMember
from socialGraphManagement.graph.crew_graph import (
    sync_crew_node,
    sync_crew_membership,
    aggregate_crew_interests,
)


class Command(BaseCommand):
    help = "Migrate all existing crews and their members to the graph database, including interests aggregation."

    def handle(self, *args, **kwargs):
        self.stdout.write("Migrating crews and members to graph...")
        crew_count = 0
        member_count = 0
        for crew in Crew.objects.all():
            sync_crew_node(
                str(crew.crewId),
                crew.name,
                crew.bio,
                crew.crew_image.url if crew.crew_image else "",
            )
            crew_count += 1
            members = CrewMember.objects.filter(crew=crew)
            for member in members:
                sync_crew_membership(str(member.user.user_id), str(crew.crewId))
                member_count += 1
            aggregate_crew_interests(str(crew.crewId))
        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Migrated {crew_count} crews and {member_count} memberships to the graph."
            )
        )

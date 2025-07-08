from django.core.management.base import BaseCommand
from django.conf import settings
from accountManagementApp.models import UserProfile
from socialGraphManagement.campus.college import sync_user_college
from django.db import transaction
from neo4j import GraphDatabase


class Command(BaseCommand):
    help = "Migrate user-college relationships to the graph"

    def handle(self, *args, **kwargs):
        self.stdout.write("🎓 Migrating college relationships to graph...")

        driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
        )

        with driver.session() as session:
            with transaction.atomic():
                profiles = UserProfile.objects.select_related("user", "college")

                count = 0
                for profile in profiles:
                    if not profile.user or not profile.user.user_id:
                        continue

                    if profile.college:
                        session.run(
                            """
                            MERGE (u:User {user_id: $user_id})
                            MERGE (c:College {collegeId: $college_id, name: $college_name})
                            MERGE (u)-[:ATTENDS]->(c)
                            """,
                            {
                                "user_id": str(profile.user.user_id),
                                "college_id": str(profile.college.collegeId),
                                "college_name": profile.college.name,
                            },
                        )
                        count += 1

        self.stdout.write(self.style.SUCCESS(f"✅ Synced {count} users with colleges."))

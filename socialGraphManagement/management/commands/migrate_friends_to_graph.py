from django.core.management.base import BaseCommand
from django.db import transaction
from accountManagementApp.models import UserProfile
from neo4j import GraphDatabase
from django.conf import settings


class Command(BaseCommand):
    help = "Migrate friends to graph database"

    def handle(self, *args, **kwargs):
        self.stdout.write("Migrating friends to graph database...")

        driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
        )

        with driver.session() as session:
            with transaction.atomic():
                profiles = UserProfile.objects.prefetch_related("friends", "user")

                count = 0
                for profile in profiles:
                    if not profile.user or not profile.user.user_id:
                        continue

                    user1_id = str(profile.user.user_id)
                    for friend_profile in profile.friends.all():
                        if not friend_profile.user or not friend_profile.user.user_id:
                            continue

                        user2_id = str(friend_profile.user.user_id)

                        # Avoid duplicating edges (A->B and B->A once)
                        if user1_id >= user2_id:
                            continue

                        session.run(
                            """
                            MERGE (u1:User {id: $user1_id})
                            MERGE (u2:User {id: $user2_id})
                            MERGE (u1)-[:FRIEND]->(u2)
                            MERGE (u2)-[:FRIEND]->(u1)
                            """,
                            {"user1_id": user1_id, "user2_id": user2_id},
                        )
                        count += 1

        self.stdout.write(
            self.style.SUCCESS(f"✅ Migrated {count} friend pairs to the graph.")
        )

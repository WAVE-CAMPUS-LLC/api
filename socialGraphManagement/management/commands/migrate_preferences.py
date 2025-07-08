from django.core.management.base import BaseCommand
from django.conf import settings
from accountManagementApp.models import UserPreferences
from socialGraphManagement.social.preferences import sync_user_preferences
from neo4j import GraphDatabase
from django.db import transaction


class Command(BaseCommand):
    help = "Migrate existing user preferences to the graph database"

    def handle(self, *args, **kwargs):
        self.stdout.write(
            "📦 Starting migration of user preferences to graph database..."
        )

        driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
        )

        with driver.session() as session:
            with transaction.atomic():
                preferences_qs = UserPreferences.objects.select_related("user")

                count = 0
                for pref in preferences_qs:
                    user = pref.user
                    if not user or not user.user_id:
                        continue

                    user_id = str(user.user_id)
                    vibe = pref.vibe or ""
                    interests = pref.interests or []
                    times = pref.preferred_times or []
                    people = pref.people_to_meet or []

                    session.run(
                        """
                        MERGE (u:User {user_id: $user_id})
                        SET u.vibe = $vibe
                        WITH u
                        UNWIND $interests AS interest
                            MERGE (i:Interest {name: interest})
                            MERGE (u)-[:INTERESTED_IN]->(i)
                        WITH u
                        UNWIND $times AS time
                            MERGE (t:Time {name: time})
                            MERGE (u)-[:PREFERRED_TIME]->(t)
                        WITH u
                        UNWIND $people AS person
                            MERGE (p:Person {name: person})
                            MERGE (u)-[:WANTS_TO_MEET]->(p)
                        """,
                        {
                            "user_id": user_id,
                            "vibe": vibe,
                            "interests": interests,
                            "times": times,
                            "people": people,
                        },
                    )
                    count += 1

        self.stdout.write(
            self.style.SUCCESS(f"✅ Migrated preferences for {count} users.")
        )

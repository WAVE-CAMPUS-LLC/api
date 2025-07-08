from django.core.management.base import BaseCommand
from django.conf import settings
from eventManagementApp.models import Event
from socialGraphManagement.event.event_based_preferences import sync_event_preferences
from neo4j import GraphDatabase
from django.db import transaction
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Migrate existing events to the graph database with preference relationships"

    def handle(self, *args, **kwargs):
        self.stdout.write(
            "📦 Starting migration of events to graph database with preferences..."
        )

        driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
        )

        with driver.session() as session:
            with transaction.atomic():
                events_qs = Event.objects.all()

                count = 0
                for event in events_qs:
                    if not event.eventId or not event.title:
                        continue

                    event_id = str(event.eventId)
                    event_title = event.title
                    event_type = event.event_type or "General"
                    event_description = event.description or ""

                    try:
                        sync_event_preferences(
                            event_id=event_id,
                            event_title=event_title,
                            event_type=event_type,
                            event_description=event_description,
                        )
                        count += 1

                        if count % 10 == 0:
                            self.stdout.write(f"✅ Processed {count} events...")

                    except Exception as e:
                        logger.error(
                            "Error syncing event %s: %s",
                            event_id,
                            str(e),
                        )
                        continue

        self.stdout.write(
            self.style.SUCCESS(f"✅ Migrated preferences for {count} events.")
        )

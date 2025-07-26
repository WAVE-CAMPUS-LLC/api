from django.core.management.base import BaseCommand
from django.conf import settings
from eventManagementApp.models import Event
from socialGraphManagement.event.event_host import sync_event_host
from neo4j import GraphDatabase
from django.db import transaction
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Migrate existing event-host relationships to the graph database"

    def handle(self, *args, **kwargs):
        self.stdout.write(
            "📦 Starting migration of event-host relationships to graph database..."
        )

        driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
        )

        with driver.session() as session:
            with transaction.atomic():
                events_qs = Event.objects.select_related("host")

                count = 0
                for event in events_qs:
                    if not event.eventId or not event.host:
                        continue

                    event_id = str(event.eventId)
                    host_id = str(event.host.user_id)
                    event_title = event.title

                    try:
                        sync_event_host(
                            event_id=event_id,
                            event_title=event_title,
                            host_id=host_id,
                        )
                        count += 1

                        if count % 10 == 0:
                            self.stdout.write(f"✅ Processed {count} events...")

                    except Exception as e:
                        logger.error(
                            "Error syncing event-host relationship for event %s: %s",
                            event_id,
                            str(e),
                        )
                        continue

        self.stdout.write(
            self.style.SUCCESS(f"✅ Migrated host relationships for {count} events.")
        )

from django.db.models.signals import post_save
from django.dispatch import receiver
from eventTicketsApp.models import Ticket


from socialGraphManagement.event.event_attended import sync_event_attended
from socialGraphManagement.event.event_going import sync_event_going
from socialGraphManagement.event.event_rsvp import sync_event_rsvp

import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Ticket)
def handle_ticket_creation(sender, instance, created, **kwargs):
    if created:
        logger.info(
            "Syncing event attended for user %s and event %s",
            instance.user.user_id,
            instance.event.eventId,
        )
        sync_event_attended(instance.user.user_id, instance.event.eventId)
        logger.info(
            "Syncing event going for user %s and event %s",
            instance.user.user_id,
            instance.event.eventId,
        )
        sync_event_going(instance.user.user_id, instance.event.eventId)
        logger.info(
            "Syncing event rsvp for user %s and event %s",
            instance.user.user_id,
            instance.event.eventId,
        )
        sync_event_rsvp(instance.user.user_id, instance.event.eventId)
    else:
        logger.info(
            "Event attended for user %s and event %s already exists",
            instance.user.user_id,
            instance.event.eventId,
        )
        logger.info(
            "Event going for user %s and event %s already exists",
            instance.user.user_id,
            instance.event.eventId,
        )
        logger.info(
            "Event rsvp for user %s and event %s already exists",
            instance.user.user_id,
            instance.event.eventId,
        )

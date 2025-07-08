from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from eventTicketsApp.models import Ticket
from eventManagementApp.models import Event
from accountManagementApp.models import UserProfile

from socialGraphManagement.event.event_attended import sync_event_attended
from socialGraphManagement.event.event_going import sync_event_going
from socialGraphManagement.event.event_rsvp import sync_event_rsvp
from socialGraphManagement.event.event_favorited import (
    sync_event_favorited,
    remove_event_favorited,
)
from socialGraphManagement.event.event_based_preferences import sync_event_preferences

import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Event)
def handle_event_preferences_sync(sender, instance, created, **kwargs):
    """
    Sync event preferences to the graph when an event is created or updated.
    """
    logger.info(
        "Syncing event preferences for event %s: %s",
        instance.eventId,
        instance.title,
    )

    # Get event type from the event model
    event_type = getattr(instance, "event_type", "General")

    # Get event description
    event_description = getattr(instance, "description", "") or getattr(
        instance, "event_description", ""
    )

    sync_event_preferences(
        event_id=str(instance.eventId),
        event_title=instance.title,
        event_type=event_type,
        event_description=event_description,
    )

    logger.info(
        "Successfully synced event preferences for event %s",
        instance.eventId,
    )


@receiver(post_save, sender=Ticket)
def handle_ticket_creation(sender, instance, created, **kwargs):
    if created:
        logger.info(
            "Syncing event attended for user %s and event %s",
            instance.user.user_id,
            instance.event.eventId,
        )
        sync_event_attended(
            user_id=instance.user.user_id,
            event_id=instance.event.eventId,
            event_title=instance.event.title,
        )
        logger.info(
            "Syncing event going for user %s and event %s",
            instance.user.user_id,
            instance.event.eventId,
        )
        sync_event_going(
            user_id=instance.user.user_id,
            event_id=instance.event.eventId,
            event_title=instance.event.title,
        )
        logger.info(
            "Syncing event rsvp for user %s and event %s",
            instance.user.user_id,
            instance.event.eventId,
        )
        sync_event_rsvp(
            user_id=instance.user.user_id,
            event_id=instance.event.eventId,
            event_title=instance.event.title,
        )
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


@receiver(m2m_changed, sender=UserProfile.favorite_events.through)
def handle_event_favorited(sender, instance, action, pk_set, **kwargs):
    if action == "post_add":
        # Event was favorited
        for event_id in pk_set:
            try:
                # The pk_set contains the actual eventId values (UUIDs)
                event = Event.objects.get(eventId=event_id)
                logger.info(
                    "Syncing event favorited for user %s and event %s",
                    instance.user.user_id,
                    event.eventId,
                )
                sync_event_favorited(
                    user_id=instance.user.user_id,
                    event_id=str(event.eventId),
                    event_title=event.title,
                )
            except Event.DoesNotExist:
                logger.warning(
                    "Event with eventId %s not found during favorite sync",
                    event_id,
                )
                continue
    elif action == "post_remove":
        # Event was unfavorited
        for event_id in pk_set:
            try:
                # The pk_set contains the actual eventId values (UUIDs)
                event = Event.objects.get(eventId=event_id)
                logger.info(
                    "Removing event favorited for user %s and event %s",
                    instance.user.user_id,
                    event.eventId,
                )
                remove_event_favorited(
                    user_id=instance.user.user_id,
                    event_id=str(event.eventId),
                )
            except Event.DoesNotExist:
                logger.warning(
                    "Event with eventId %s not found during favorite removal",
                    event_id,
                )
                continue

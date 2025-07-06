from django.db.models.signals import post_save
from django.dispatch import receiver
from collegeManagementApp.models import Membership

from socialGraphManagement.campus.membership import sync_membership

import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Membership)
def handle_membership_creation(sender, instance, created, **kwargs):
    if created:
        logger.info(
            "Syncing membership for user %s and college %s",
            instance.user.user_id,
            instance.college.collegeId,
        )
        sync_membership(instance.user.user_id, instance.college.collegeId)
    else:
        logger.info(
            "Membership for user %s and college %s already exists",
            instance.user.user_id,
            instance.college.collegeId,
        )

from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from socialApp.models import Crew, CrewMember, FriendRequest
from accountManagementApp.models import UserProfile

from socialGraphManagement.social.crew import sync_crew_membership
from socialGraphManagement.social.friendship import sync_friendship, remove_friendship

from apiManager.utilities.notifications.send_notification import send_notification


import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=CrewMember)
def handle_crew_member_creation(sender, instance, created, **kwargs):
    if created:
        logger.info(
            "Syncing crew membership for user %s and crew %s",
            instance.user.user_id,
            instance.crew.crewId,
        )
        sync_crew_membership(instance.user.user_id, instance.crew.crewId)


@receiver(post_save, sender=Crew)
def handle_crew_creation(sender, instance, created, **kwargs):
    if created:
        logger.info(
            "Syncing crew membership for user %s and crew %s",
            instance.created_by.user_id,
            instance.crewId,
        )
        sync_crew_membership(instance.created_by.user_id, instance.crewId)


@receiver(post_save, sender=FriendRequest)
def handle_friend_request_creation(sender, instance, created, **kwargs):
    if created:
        logger.info(
            "Syncing friendship for user %s and user %s",
            instance.sender.user_id,
            instance.receiver.user_id,
        )
        sync_friendship(instance.sender.user_id, instance.receiver.user_id)
        send_notification(
            instance.receiver.user_id,
            instance.sender.user_id,
            "FRIEND_REQUEST",
            f"You have a new friend request from {instance.sender.username}",
        )


@receiver(m2m_changed, sender=UserProfile.friends.through)
def handle_friends_changed(sender, instance, action, pk_set, **kwargs):
    """
    Signal handler for when friends are added/removed from UserProfile.friends field.
    Syncs the friendship relationships in the graph database.
    """
    if action == "post_add":
        # Friends were added
        for new_friend_id in pk_set:
            try:
                new_friend_profile = UserProfile.objects.get(user_id=new_friend_id)
                user_profile = instance

                sync_friendship(
                    user_profile.user.user_id, new_friend_profile.user.user_id
                )
                mutuals = user_profile.friends.exclude(user_id=new_friend_id)

                for mutual in mutuals:
                    send_notification(
                        recipient_id=mutual.user.user_id,
                        actor_id=user_profile.user.user_id,
                        notification_type="friend_connected",
                        content=f"{user_profile.user.username} became friends with {new_friend_profile.user.username}",
                        metadata={
                            "friend_1_id": user_profile.user.user_id,
                            "friend_2_id": new_friend_profile.user.user_id,
                        },
                    )
            except UserProfile.DoesNotExist:
                continue
    elif action == "post_remove":
        # Friends were removed
        for friend_id in pk_set:
            try:
                friend = UserProfile.objects.get(user_id=friend_id)
                if instance.user and friend.user:
                    logger.info(
                        "Removing friendship for user %s and user %s",
                        instance.user.user_id,
                        friend.user.user_id,
                    )
                    remove_friendship(instance.user.user_id, friend.user.user_id)
            except UserProfile.DoesNotExist:
                continue

from django.db.models.signals import post_save, m2m_changed, post_delete
from django.dispatch import receiver
from socialApp.models import Crew, CrewMember, FriendRequest
from accountManagementApp.models import UserProfile
from authenticationApp.models import CustomUser

from socialGraphManagement.social.crew import sync_crew_membership
from socialGraphManagement.social.friendship import (
    sync_friendship,
    remove_friendship,
    create_friend_request,
    remove_friend_request,
    remove_user_from_graph,
)

from apiManager.utilities.notifications.send_notification import send_notification


import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=FriendRequest)
def handle_friend_request_creation(sender, instance, created, **kwargs):
    if created:
        logger.info(
            "Creating friend request for user %s and user %s",
            instance.sender.user_id,
            instance.receiver.user_id,
        )
        create_friend_request(instance.sender.user_id, instance.receiver.user_id)
        send_notification(
            str(instance.receiver.user_id),
            str(instance.sender.user_id),
            "FRIEND_REQUEST",
            f"You have a new friend request from {instance.sender.username}",
        )


@receiver(post_save, sender=FriendRequest)
def handle_friend_request_status(sender, instance, **kwargs):
    if instance.status == "accepted":
        sync_friendship(instance.sender.user_id, instance.receiver.user_id)
        logger.info(
            "Creating REQUESTED from %s to %s",
            instance.sender.user_id,
            instance.receiver.user_id,
        )
        send_notification(
            str(instance.receiver.user_id),
            str(instance.sender.user_id),
            "FRIEND_REQUEST_ACCEPTED",
            f"You are now friends with {instance.sender.username}",
        )
    elif instance.status in ["declined", "canceled"]:
        remove_friend_request(instance.sender.user_id, instance.receiver.user_id)
        remove_friendship(instance.sender.user_id, instance.receiver.user_id)
        logger.info(
            "Removing REQUESTED and FRIEND relationships from %s to %s",
            instance.sender.user_id,
            instance.receiver.user_id,
        )


@receiver(m2m_changed, sender=UserProfile.friends.through)
def handle_friends_changed(sender, instance, action, pk_set, **kwargs):
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
                            "friend_1_id": str(user_profile.user.user_id),
                            "friend_2_id": str(new_friend_profile.user.user_id),
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


@receiver(post_delete, sender=CustomUser)
def remove_user_from_graph_signal(sender, instance, **kwargs):
    remove_user_from_graph(str(instance.user_id))

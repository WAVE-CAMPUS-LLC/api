import json
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import FriendRequest, CrewRequest, GoWithRequest

@receiver(post_save, sender=FriendRequest)
def friend_request_post_save(sender, instance, created, **kwargs):
    """Send real-time notifications when a friend request is created or updated."""
    channel_layer = get_channel_layer()
    
    # Determine the action and prepare data
    if created:
        action = "send"
        message = f"{instance.sender.username} sent you a friend request!"
    elif instance.status == "accepted":
        action = "accept"
        message = f"{instance.receiver.username} accepted your friend request!"
    elif instance.status == "declined":
        action = "decline"
        message = f"{instance.receiver.username} declined your friend request."
    elif instance.status == "canceled":
        action = "cancel"
        message = "Friend request has been canceled."
    else:
        # No notification for other status changes
        return
    
    # Send to the receiver for new requests
    if created or instance.status == "canceled":
        # For new requests, notify the receiver
        user_channel = f"user_{instance.receiver.id}"
        async_to_sync(channel_layer.group_send)(
            user_channel,
            {
                "type": "social_update",
                "data": {
                    "message": message,
                    "action": action,
                    "friend_request": {
                        "requestId": str(instance.requestId),
                        "sender_first_name": instance.sender.first_name,
                        "sender_last_name": instance.sender.last_name,
                        "created_at": instance.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                        "profile_picture": instance.sender.user_profile.profile_photo.url if hasattr(instance.sender, 'user_profile') else "",
                    },
                },
            }
        )
    
    # For status updates, notify the sender
    if not created:
        user_channel = f"user_{instance.sender.id}"
        async_to_sync(channel_layer.group_send)(
            user_channel,
            {
                "type": "friend_request_action",
                "data": {
                    "message": message,
                    "action": action,
                    "friend_request": {
                        "requestId": str(instance.requestId),
                        "receiver_first_name": instance.receiver.first_name,
                        "receiver_last_name": instance.receiver.last_name,
                        "status": instance.status,
                    },
                },
            }
        )

@receiver(post_save, sender=CrewRequest)
def crew_request_post_save(sender, instance, created, **kwargs):
    """Send real-time notifications when a crew request is created or updated."""
    channel_layer = get_channel_layer()
    
    # Determine the action and prepare data
    if created:
        action = "sendCrew"
        message = f"{instance.sender.username} invited you to join {instance.crew.name}!"
    elif instance.status == "accepted":
        action = "acceptCrewRequest"
        message = f"{instance.receiver.username} accepted your crew invitation!"
    elif instance.status == "declined":
        action = "declineCrewRequest"
        message = f"{instance.receiver.username} declined your crew invitation."
    else:
        # No notification for other status changes
        return
    
    # Send to the receiver for new requests
    if created:
        # For new requests, notify the receiver
        user_channel = f"user_{instance.receiver.id}"
        async_to_sync(channel_layer.group_send)(
            user_channel,
            {
                "type": "social_update",
                "data": {
                    "message": message,
                    "action": action,
                    "crew_request": {
                        "requestId": str(instance.requestId),
                        "crew": str(instance.crew.name),
                        "crewId": str(instance.crew.crewId),
                        "sender": {
                            "username": instance.sender.username,
                        },
                    },
                },
            }
        )
    
    # For status updates, notify the sender
    if not created:
        user_channel = f"user_{instance.sender.id}"
        async_to_sync(channel_layer.group_send)(
            user_channel,
            {
                "type": "crew_request_update",
                "data": {
                    "message": message,
                    "action": action,
                    "crew_request": {
                        "requestId": str(instance.requestId),
                        "crew": str(instance.crew.name),
                        "crewId": str(instance.crew.crewId),
                        "receiver": {
                            "username": instance.receiver.username,
                        },
                        "status": instance.status,
                    },
                },
            }
        )

@receiver(post_save, sender=GoWithRequest)
def go_with_request_post_save(sender, instance, created, **kwargs):
    """Send real-time notifications when a go-with request is created or updated."""
    channel_layer = get_channel_layer()
    
    # Determine the action and prepare data
    if created:
        action = "sendGoWith"
        message = f"{instance.sender.user.username} wants to go with you to {instance.event.title}!"
    elif instance.status == "accepted" or instance.status == "Accepted":
        action = "acceptGoWithRequest"
        message = f"{instance.receiver.user.username} accepted your go-with request!"
    elif instance.status == "declined" or instance.status == "Declined":
        action = "declineGoWithRequest"
        message = f"{instance.receiver.user.username} declined your go-with request."
    elif instance.status == "cancelled" or instance.status == "Cancelled":
        action = "cancelGoWithRequest"
        message = f"{instance.sender.user.username} cancelled the go-with request."
    else:
        # No notification for other status changes
        return
    
    # Send to the receiver for new requests
    if created or instance.status == "cancelled" or instance.status == "Cancelled":
        # For new or cancelled requests, notify the receiver
        try:
            user_channel = f"user_{instance.receiver.user.id}"
            async_to_sync(channel_layer.group_send)(
                user_channel,
                {
                    "type": "social_update",
                    "data": {
                        "message": message,
                        "action": action,
                        "go_with_request": {
                            "requestId": str(instance.requestId),
                            "event": {
                                "title": instance.event.title,
                                "eventId": str(instance.event.eventId),
                            },
                            "sender": {
                                "username": instance.sender.user.username,
                                "first_name": instance.sender.user.first_name,
                                "last_name": instance.sender.user.last_name,
                                "profile_photo": instance.sender.profile_photo.url,
                            },
                        },
                    },
                }
            )
        except Exception as e:
            print(f"Error sending go-with notification to receiver: {e}")
    
    # For status updates, notify the sender
    if not created:
        try:
            user_channel = f"user_{instance.sender.user.id}"
            async_to_sync(channel_layer.group_send)(
                user_channel,
                {
                    "type": "social_update",
                    "data": {
                        "message": message,
                        "action": action,
                        "go_with_request": {
                            "requestId": str(instance.requestId),
                            "event": {
                                "title": instance.event.title,
                                "eventId": str(instance.event.eventId),
                            },
                            "receiver": {
                                "username": instance.receiver.user.username,
                                "first_name": instance.receiver.user.first_name,
                                "last_name": instance.receiver.user.last_name,
                                "profile_photo": instance.receiver.profile_photo.url,
                            },
                            "status": instance.status,
                        },
                    },
                }
            )
        except Exception as e:
            print(f"Error sending go-with notification to sender: {e}")
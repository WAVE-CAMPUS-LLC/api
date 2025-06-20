import json
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import (
    FriendRequest,
    CrewRequest,
    GoWithRequest,
    SocialActivity,
    CrewMember,
)
from eventTicketsApp.models import Ticket


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
                        "profile_picture": (
                            instance.sender.user_profile.profile_photo.url
                            if hasattr(instance.sender, "user_profile")
                            else ""
                        ),
                    },
                },
            },
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
            },
        )


@receiver(post_save, sender=CrewRequest)
def crew_request_post_save(sender, instance, created, **kwargs):
    """Send real-time notifications when a crew request is created or updated."""
    channel_layer = get_channel_layer()

    # Determine the action and prepare data
    if created:
        action = "sendCrew"
        message = (
            f"{instance.sender.username} invited you to join {instance.crew.name}!"
        )
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
            },
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
            },
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
                },
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
                },
            )
        except Exception as e:
            print(f"Error sending go-with notification to sender: {e}")


@receiver(post_save, sender=FriendRequest)
def record_friend_activity(sender, instance, created, **kwargs):
    if instance.status == "accepted":
        # Record activity for the sender
        SocialActivity.objects.create(
            user=instance.sender,
            activity_type="friend_accepted",
            content={
                "friend_request": str(instance.requestId),
                "friend_username": instance.receiver.username,
                "friend_name": f"{instance.receiver.first_name} {instance.receiver.last_name}",
                "friend_photo": (
                    instance.receiver.user_profile.profile_photo.url
                    if hasattr(instance.receiver, "user_profile")
                    else None
                ),
            },
        )

        # Record activity for the receiver
        SocialActivity.objects.create(
            user=instance.receiver,
            activity_type="friend_accepted",
            content={
                "friend_request": str(instance.requestId),
                "friend_username": instance.sender.username,
                "friend_name": f"{instance.sender.first_name} {instance.sender.last_name}",
                "friend_photo": (
                    instance.sender.user_profile.profile_photo.url
                    if hasattr(instance.sender, "user_profile")
                    else None
                ),
            },
        )


@receiver(post_save, sender=CrewMember)
def record_crew_activity(sender, instance, created, **kwargs):
    if created:
        SocialActivity.objects.create(
            user=instance.user,
            activity_type="crew_joined",
            content={
                "crew": instance.crew.name,
                "crew_id": str(instance.crew.crewId),
                "joined_at": instance.joined_at.isoformat(),
                "crew_photo": (
                    instance.crew.crew_photo.url
                    if hasattr(instance.crew, "crew_photo")
                    else None
                ),
            },
        )


@receiver(post_save, sender=Ticket)
def record_ticket_activity(sender, instance, created, **kwargs):
    try:
        if created and instance.user:  # Only create activity for authenticated users, not guests
            # Try to extract ticket type from QR code data or use default
            ticket_type = "General Admission"  # Default value
            try:
                if instance.qrCodeData:
                    import json
                    qr_data = json.loads(instance.qrCodeData)
                    ticket_type = qr_data.get("ticketType", "General Admission")
            except (json.JSONDecodeError, KeyError, AttributeError):
                print(f"[record_ticket_activity] Could not parse ticket type from QR data, using default")
                pass
            
            # Safely get event details
            event_id = None
            event_title = "Unknown Event"
            event_date = None
            event_photo = None
            venue = None
            event_time = None
            
            try:
                if hasattr(instance, 'event') and instance.event:
                    event_id = str(instance.event.eventId) if hasattr(instance.event, 'eventId') else None
                    event_title = instance.event.title if hasattr(instance.event, 'title') else "Unknown Event"
                    event_date = instance.event.date.isoformat() if hasattr(instance.event, 'date') and instance.event.date else None
                    event_photo = instance.event.header_photo.url if hasattr(instance.event, 'header_photo') and instance.event.header_photo else None
                    venue = instance.event.venue.name if hasattr(instance.event, 'venue') and instance.event.venue else None
                    event_time = (
                        instance.event.time.strftime("%I:%M %p")
                        if hasattr(instance.event, 'time') and instance.event.time
                        else None
                    )
            except Exception as e:
                print(f"[record_ticket_activity] Error extracting event details: {e}")
            
            # Create the social activity record
            SocialActivity.objects.create(
                user=instance.user,
                activity_type="ticket_purchased",
                content={
                    "event_id": event_id,
                    "event_title": event_title,
                    "event_date": event_date,
                    "event_photo": event_photo,
                    "ticket_type": ticket_type,
                    "quantity": 1,  # Each ticket instance represents 1 ticket
                    "venue": venue,
                    "event_time": event_time,
                    "price": None,  # Ticket model doesn't store price, would need to lookup from PaidFreeTicket
                },
            )
            print(f"[record_ticket_activity] Successfully recorded ticket activity for user {instance.user.id}")
    except Exception as e:
        print(f"[record_ticket_activity] Error recording ticket activity: {e}")
        # Don't re-raise the exception to prevent blocking ticket creation
        import traceback
        print(f"[record_ticket_activity] Full traceback: {traceback.format_exc()}")


@receiver(post_save, sender=GoWithRequest)
def record_go_with_activity(sender, instance, created, **kwargs):
    if instance.status in ["accepted", "Accepted"]:
        # Record activity for both users
        for user in [instance.sender.user, instance.receiver.user]:
            SocialActivity.objects.create(
                user=user,
                activity_type="go_with_accepted",
                content={
                    "event_id": str(instance.event.eventId),
                    "event_title": instance.event.title,
                    "event_date": instance.event.date.isoformat(),
                    "event_photo": (
                        instance.event.header_photo.url
                        if instance.event.header_photo
                        else None
                    ),
                    "other_user": {
                        "username": (
                            instance.receiver.user.username
                            if user == instance.sender.user
                            else instance.sender.user.username
                        ),
                        "name": (
                            f"{instance.receiver.user.first_name} {instance.receiver.user.last_name}"
                            if user == instance.sender.user
                            else f"{instance.sender.user.first_name} {instance.sender.user.last_name}"
                        ),
                        "photo": (
                            instance.receiver.profile_photo.url
                            if user == instance.sender.user
                            else instance.sender.profile_photo.url
                        ),
                    },
                },
            )


@receiver(post_save, sender=CrewRequest)
def record_crew_invite_activity(sender, instance, created, **kwargs):
    if instance.status == "accepted":
        SocialActivity.objects.create(
            user=instance.receiver,
            activity_type="crew_invite_accepted",
            content={
                "crew": instance.crew.name,
                "crew_id": str(instance.crew.crewId),
                "invited_by": {
                    "username": instance.sender.username,
                    "name": f"{instance.sender.first_name} {instance.sender.last_name}",
                    "photo": (
                        instance.sender.user_profile.profile_photo.url
                        if hasattr(instance.sender, "user_profile")
                        else None
                    ),
                },
                "crew_photo": (
                    instance.crew.crew_photo.url
                    if hasattr(instance.crew, "crew_photo")
                    else None
                ),
            },
        )

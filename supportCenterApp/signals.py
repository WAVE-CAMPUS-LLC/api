from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import SupportTicketMessage
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

@receiver(post_save, sender=SupportTicketMessage)
def new_message_notification(sender, instance, created, **kwargs):
    if created:
        channel_layer = get_channel_layer()
        room_group_name = f"chat_{instance.ticket.ticket_id}"
        async_to_sync(channel_layer.group_send)(
            room_group_name,
            {
                "type": "new_message",
                "message": instance.message,
                "sender": instance.sender.username,
                "sent_at": instance.sent_at.strftime("%Y-%m-%d %H:%M:%S"),
            },
        )

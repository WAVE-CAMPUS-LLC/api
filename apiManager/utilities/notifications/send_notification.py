from notificationManagement.models import Notification
from django.contrib.auth import get_user_model

User = get_user_model()


def send_notification(recipient_id, actor_id, type, content, metadata=None):
    if not recipient_id or not type or not content:
        return

    try:
        recipient = User.objects.get(user_id=recipient_id)
        actor = User.objects.get(user_id=actor_id) if actor_id else None

        notification = Notification.objects.create(
            recipient=recipient,
            actor=actor,
            type=type,
            content=content,
            metadata=metadata or {},
        )
        return notification

    except User.DoesNotExist:
        pass

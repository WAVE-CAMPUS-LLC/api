from django.utils.timezone import now
from datetime import timedelta
from socialApp.models import EventMessage


def can_send_message(sender):
    last_message = (
        EventMessage.objects.filter(sender=sender).order_by("-created_at").first()
    )
    if last_message and now() - last_message.created_at < timedelta(seconds=30):
        return False
    return True

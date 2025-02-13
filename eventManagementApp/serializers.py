from rest_framework import serializers
from .models import Event, EventPrivacy

class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = [
            "eventId",
            "title",
            "event_type",
            "description",
            "privacy",
            "country",
            "city",
            "state",
            "zip_code",
            # "contact_email",
            # "contact_phone",
            "date",
            "start_time",
            "end_time",
            "status",
        ]

class EventPrivacySerializer(serializers.ModelSerializer):
    class Meta:
        model = EventPrivacy
        fields = [
            "event",
            "display_on_explore",
            "require_invitation",
        ]
from rest_framework import serializers
from .models import Event, SharedEvent
from accountManagementApp.serializers import UserProfileSerializer
from socialApp.serializers import CrewSerializer

class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = "__all__"

# class EventPrivacySerializer(serializers.ModelSerializer):
#     class Meta:
#         model = EventPrivacy
#         fields = [
#             "event",
#             "display_on_explore",
#             "require_invitation",
#         ]
        
class SharedEventSerializer(serializers.ModelSerializer):
    sender = UserProfileSerializer()
    receiver = UserProfileSerializer()
    crew = CrewSerializer()
    event = EventSerializer()

    class Meta:
        model = SharedEvent
        fields = ["id", "sender", "receiver", "crew", "event", "shared_at"]
        
        
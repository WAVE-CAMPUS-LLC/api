from rest_framework import serializers
from .models import Event, SharedEvent
from accountManagementApp.serializers import UserProfileSerializer

class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = "__all__"

class SharedEventWithoutCrewSerializer(serializers.ModelSerializer):
    sender = UserProfileSerializer()
    receiver = UserProfileSerializer()
    event = EventSerializer()

    class Meta:
        model = SharedEvent 
        exclude = ('crew',)

class SharedEventSerializer(SharedEventWithoutCrewSerializer):
    from socialApp.serializers import CrewSerializer
    crew = CrewSerializer()

    class Meta:
        model = SharedEvent
        fields = "__all__"


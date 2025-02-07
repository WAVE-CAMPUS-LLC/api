from rest_framework import serializers
from eventManagementApp.models import Event

class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ['eventId', 'title', 'date', 'description', 'host', 'header_photo']

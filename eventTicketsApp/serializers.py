from rest_framework import serializers
from .models import RSVPTicket, Ticket
from eventManagementApp.models import Event
from eventManagementApp.serializers import EventSerializer
from django.core.exceptions import ValidationError

class RSVPTicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = RSVPTicket
        fields = "__all__" 

    def validate_email(self, value):
        """
        Validate that the email is not already used for RSVP in this event.
        """
        event = self.initial_data.get('event')
        if RSVPTicket.objects.filter(event=event, email=value).exists():
            raise serializers.ValidationError("This email has already been submitted for this event.")
        return value

    def create(self, validated_data):
        """
        Create an RSVP ticket for the event.
        """
        # Ensure ticket_id is automatically generated
        validated_data['ticket_id'] = uuid.uuid4()  # Ensure a unique ticket_id is generated
        return RSVPTicket.objects.create(**validated_data)

    def update(self, instance, validated_data):
        """
        Update an existing RSVP ticket.
        """
        instance.first_name = validated_data.get('first_name', instance.first_name)
        instance.last_name = validated_data.get('last_name', instance.last_name)
        instance.display_on_guestlist = validated_data.get('display_on_guestlist', instance.display_on_guestlist)
        instance.save()
        return instance
    
    
class TicketSerializer(serializers.ModelSerializer):
    event = EventSerializer()
    
    class Meta:
        model = Ticket
        fields = "__all__"
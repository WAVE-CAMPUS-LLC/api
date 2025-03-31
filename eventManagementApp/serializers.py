from rest_framework import serializers
from .models import Event, SharedEvent, CouponCode
from accountManagementApp.serializers import UserProfileSerializer

class EventBasicSerializer(serializers.ModelSerializer):
    """A lightweight serializer for events with minimal fields."""
    class Meta:
        model = Event
        fields = ('eventId', 'title', 'date', 'header_photo', 'status')

class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = "__all__"

class SharedEventWithoutCrewSerializer(serializers.ModelSerializer):
    """Optimized serializer with limited fields and reduced nesting."""
    event = EventBasicSerializer()
    
    # Use custom field representations instead of nested serializers
    sender_id = serializers.SerializerMethodField()
    sender_username = serializers.SerializerMethodField()
    sender_profile_photo = serializers.SerializerMethodField()
    
    receiver_id = serializers.SerializerMethodField()
    receiver_username = serializers.SerializerMethodField()
    
    class Meta:
        model = SharedEvent 
        fields = ('id', 'event', 'shared_at', 
                  'sender_id', 'sender_username', 'sender_profile_photo',
                  'receiver_id', 'receiver_username')

    def get_sender_id(self, obj):
        if obj.sender and obj.sender.user:
            return obj.sender.user.id
        return None
        
    def get_sender_username(self, obj):
        if obj.sender and obj.sender.user:
            return obj.sender.user.username
        return None
        
    def get_sender_profile_photo(self, obj):
        if obj.sender and obj.sender.profile_photo:
            return obj.sender.profile_photo.url
        return None
        
    def get_receiver_id(self, obj):
        if obj.receiver and obj.receiver.user:
            return obj.receiver.user.id
        return None
        
    def get_receiver_username(self, obj):
        if obj.receiver and obj.receiver.user:
            return obj.receiver.user.username
        return None

class SharedEventSerializer(serializers.ModelSerializer):
    """Full shared event serializer with all fields."""
    event = EventBasicSerializer()
    sender = UserProfileSerializer(read_only=True)
    receiver = UserProfileSerializer(read_only=True)
    
    class Meta:
        model = SharedEvent
        fields = '__all__'
        
    def to_representation(self, instance):
        # Limit the depth of serialization
        data = super().to_representation(instance)
        # Add crew ID if it exists
        if instance.crew:
            data['crew_id'] = str(instance.crew.crewId)
            data['crew_name'] = instance.crew.name
        return data

class CouponSerializer(serializers.ModelSerializer):
    event = EventBasicSerializer()
    class Meta:
        model = CouponCode
        fields = "__all__"
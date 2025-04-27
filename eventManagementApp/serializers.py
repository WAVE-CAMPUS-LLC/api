from rest_framework import serializers
from .models import Event, SharedEvent, CouponCode
from accountManagementApp.serializers import UserProfileSerializer
from django.core.files.uploadedfile import UploadedFile

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

class EditEventModelSerializer(serializers.ModelSerializer):
    """ModelSerializer for handling event updates with proper partial update support."""
    header_photo = serializers.ImageField(required=False, allow_null=True)
    body_photo_one = serializers.ImageField(required=False, allow_null=True)
    body_photo_two = serializers.ImageField(required=False, allow_null=True)
    body_photo_three = serializers.ImageField(required=False, allow_null=True)
    body_photo_four = serializers.ImageField(required=False, allow_null=True)
    body_photo_five = serializers.ImageField(required=False, allow_null=True)
    
    class Meta:
        model = Event
        fields = [
            "title",
            "event_type",
            "date",
            "start_time",
            "end_time",
            "description",
            "building_name",
            "street",
            "apt_suite_unit",
            "city",
            "state",
            "zip_code",
            "country",
            "hide_address",
            "header_photo",
            "body_photo_one",
            "body_photo_two",
            "body_photo_three",
            "body_photo_four",
            "body_photo_five",
            "age_restriction",
            "couponsActivated",
            "crew_discount",
            "minimum_crew_size",
            "crew_discount_percentage",
            "show_guest_list",
            "forAllDisplay",
            "forCollegesDisplay",
        ]
    
    def __init__(self, *args, **kwargs):
        # Make all fields optional when partial=True is passed
        super().__init__(*args, **kwargs)
        if kwargs.get('partial', False):
            for field in self.fields.values():
                field.required = False
                
    def to_internal_value(self, data):
        # Handle file fields specially to work with FastAPI UploadFile objects
        # that have been converted to Django's SimpleUploadedFile
        return super().to_internal_value(data)
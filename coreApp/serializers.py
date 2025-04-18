from rest_framework import serializers
from eventManagementApp.models import Event
from authenticationApp.serializers import CustomUserSerializer
from accountManagementApp.serializers import UserProfileSerializer


class ExplorePageEventSerializer(serializers.ModelSerializer):
    """Serializer for events displayed on the explore page."""
    header_photo = serializers.SerializerMethodField()
    
    class Meta:
        model = Event
        fields = ('eventId', 'title', 'date', 'header_photo', "state", "city", "ticketing", "forAllDisplay", "forCollegesDisplay")
        
    def get_header_photo(self, obj):
        if obj.header_photo:
            return obj.header_photo.url
        return None


class EventDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed event view."""
    header_photo = serializers.SerializerMethodField()
    
    class Meta:
        model = Event
        fields = ("eventId", "title", "description", "date", "header_photo", "country", "street", "apt_suite_unit", "city", "state", "zip_code", "hide_address", "ticketing", "start_time", "end_time")
        
    def get_header_photo(self, obj):
        if obj.header_photo:
            return obj.header_photo.url
        return None
    
class EventExtraPhotosSerializer(serializers.ModelSerializer):
    header_photo = serializers.SerializerMethodField()
    body_photo_one = serializers.SerializerMethodField()
    body_photo_two = serializers.SerializerMethodField()
    body_photo_three = serializers.SerializerMethodField()
    body_photo_four = serializers.SerializerMethodField()
    body_photo_five = serializers.SerializerMethodField()


    class Meta:
        model = Event
        fields = ("header_photo", "body_photo_one", "body_photo_two", "body_photo_three", "body_photo_four", "body_photo_five")
        
    def get_header_photo(self, obj):
        if obj.header_photo:
            return obj.header_photo.url
        return None
    
    def get_body_photo_one(self, obj):
        if obj.body_photo_one:
            return obj.body_photo_one.url
        return None

    def get_body_photo_two(self, obj):
        if obj.body_photo_two:
            return obj.body_photo_two.url
        return None
    
    def get_body_photo_three(self, obj):
        if obj.body_photo_three:
            return obj.body_photo_three.url
        return None
    
    def get_body_photo_four(self, obj):
        if obj.body_photo_four:
            return obj.body_photo_four.url
        return None
    
    def get_body_photo_five(self, obj):
        if obj.body_photo_five:
            return obj.body_photo_five.url
        return None



class EventSerializer(serializers.ModelSerializer):
    host = CustomUserSerializer(read_only=True)  # Changed to CustomUserSerializer since host is a CustomUser
    host_profile = serializers.SerializerMethodField()  # Add method to get host's profile
    
    class Meta:
        model = Event
        fields = "__all__"
        
    def get_host_profile(self, obj):
        if hasattr(obj.host, 'user_profile'):
            return UserProfileSerializer(obj.host.user_profile).data
        return None



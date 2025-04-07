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



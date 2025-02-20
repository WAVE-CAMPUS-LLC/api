from rest_framework import serializers
from eventManagementApp.models import Event
from authenticationApp.serializers import CustomUserSerializer
from accountManagementApp.serializers import UserProfileSerializer


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

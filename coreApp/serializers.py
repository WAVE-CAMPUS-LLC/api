from rest_framework import serializers
from eventManagementApp.models import Event
from authenticationApp.serializers import CustomUserSerializer
from accountManagementApp.serializers import UserProfileSerializer


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        host = UserProfileSerializer()
        model = Event
        fields = "__all__"

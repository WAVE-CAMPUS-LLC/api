from rest_framework import serializers
from .models import Crew, CrewMember, CrewRequest, FriendRequest
from accountManagementApp.models import UserProfile
from authenticationApp.serializers import CustomUserSerializer


class CrewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Crew
        fields = "__all__"
        
        
class FriendRequestSerializer(serializers.ModelSerializer):
    sender = CustomUserSerializer()
    receiver = CustomUserSerializer()
    
    class Meta:
        model = FriendRequest
        fields = "__all__"
        
        
class CrewRequestSerializer(serializers.ModelSerializer):
    sender = CustomUserSerializer()
    receiver = CustomUserSerializer()
    crew = CrewSerializer()
    
    class Meta:
        model = CrewRequest
        fields = "__all__"
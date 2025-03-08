from rest_framework import serializers
from .models import Crew, CrewMember, CrewRequest, FriendRequest
from accountManagementApp.models import UserProfile
from authenticationApp.serializers import CustomUserSerializer
from accountManagementApp.serializers import UserProfileSerializer


class CrewSerializer(serializers.ModelSerializer):
    members=CustomUserSerializer(many=True)
    created_by=CustomUserSerializer()
    class Meta:
        model = Crew
        fields = "__all__"
        

class CrewMemberSerializer(serializers.ModelSerializer):
    user = CustomUserSerializer()
    crew = CrewSerializer()
    
    class Meta:
        model = CrewMember
        fields = "__all__"
        
        
class FriendRequestSerializer(serializers.ModelSerializer):
    sender = CustomUserSerializer()
    receiver = CustomUserSerializer()
    sender_profile = serializers.SerializerMethodField()
    receiver_profile = serializers.SerializerMethodField()
    
    class Meta:
        model = FriendRequest
        fields = "__all__"
    
    def get_sender_profile(self, obj):
        try:
            return UserProfileSerializer(obj.sender.user_profile).data
        except UserProfile.DoesNotExist:
            return None
            
    def get_receiver_profile(self, obj):
        try:
            return UserProfileSerializer(obj.receiver.user_profile).data
        except UserProfile.DoesNotExist:
            return None
        
        
class CrewRequestSerializer(serializers.ModelSerializer):
    sender = CustomUserSerializer()
    receiver = CustomUserSerializer()
    crew = CrewSerializer()
    
    class Meta:
        model = CrewRequest
        fields = "__all__"
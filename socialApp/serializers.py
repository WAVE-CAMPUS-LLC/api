from rest_framework import serializers
from django.core.exceptions import ObjectDoesNotExist
from .models import Crew, CrewMember, CrewRequest, FriendRequest
from accountManagementApp.models import UserProfile
from authenticationApp.serializers import CustomUserSerializer
from accountManagementApp.serializers import UserProfileSerializer


class CrewMemberSerializer(serializers.ModelSerializer):
    user = CustomUserSerializer()
    user_profile = serializers.SerializerMethodField()
    
    class Meta:
        model = CrewMember
        fields = "__all__"
        
    def get_user_profile(self, obj):
        try:
            return UserProfileSerializer(obj.user.user_profile).data
        except ObjectDoesNotExist:
            return None


class CrewSerializer(serializers.ModelSerializer):
    created_by = CustomUserSerializer()
    created_by_profile = serializers.SerializerMethodField()
    crew_members = CrewMemberSerializer(many=True, source='crew_members.all')
    
    class Meta:
        model = Crew
        fields = "__all__"
        
    def get_created_by_profile(self, obj):
        try:
            return UserProfileSerializer(obj.created_by.user_profile).data
        except ObjectDoesNotExist:
            return None
        

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
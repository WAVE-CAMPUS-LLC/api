from rest_framework import serializers
from django.core.exceptions import ObjectDoesNotExist
from typing import Optional
from .models import Crew, CrewMember, CrewRequest, FriendRequest
from .forms import createCrewForm
from authenticationApp.serializers import CustomUserSerializer
from accountManagementApp.serializers import UserProfileSerializer
from eventManagementApp.serializers import SharedEventWithoutCrewSerializer


class CrewMemberSerializer(serializers.ModelSerializer):
    user = CustomUserSerializer(read_only=True)
    user_profile = serializers.SerializerMethodField()

    class Meta:
        model = CrewMember
        fields = "__all__"

    def get_user_profile(self, obj) -> Optional[dict]:
        # Only fetch profile if it's part of the prefetch_related
        if hasattr(obj.user, 'user_profile'):
            return UserProfileSerializer(obj.user.user_profile).data
        return None


class CrewSerializer(serializers.ModelSerializer):
    created_by = CustomUserSerializer(read_only=True)
    created_by_profile = serializers.SerializerMethodField()
    crew_members = serializers.SerializerMethodField()
    shared_events = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Crew
        fields = "__all__"

    def get_created_by_profile(self, obj) -> Optional[dict]:
        try:
            return UserProfileSerializer(obj.created_by.user_profile).data
        except (ObjectDoesNotExist, AttributeError):
            return None

    def get_crew_members(self, obj) -> list:
        # Only include if requested and avoid recursive serialization
        if not self.context.get('include_members', True):
            return []
            
        # Use prefetched data if available
        if hasattr(obj, 'prefetched_crew_members'):
            return CrewMemberSerializer(obj.prefetched_crew_members, many=True).data
        
        # Limit to recent members for performance
        members = obj.crew_members.all()[:5]
        return CrewMemberSerializer(members, many=True).data
    
    def get_shared_events(self, obj) -> list:
        # Skip shared events if in non-recursive mode to avoid deep nesting
        if self.context.get('non_recursive', False):
            return []
            
        # Limit shared events for performance
        if hasattr(obj, 'shared_events'):
            shared_events = obj.shared_events.all()[:3]
            return SharedEventWithoutCrewSerializer(shared_events, many=True).data
        return []

    def get_member_count(self, obj) -> int:
        # Use annotated count if available, otherwise count from relationship
        if hasattr(obj, 'member_count'):
            return obj.member_count
        return obj.crew_members.count()


class FriendRequestSerializer(serializers.ModelSerializer):
    sender = CustomUserSerializer(read_only=True)
    receiver = CustomUserSerializer(read_only=True)
    sender_profile = serializers.SerializerMethodField()
    receiver_profile = serializers.SerializerMethodField()

    class Meta:
        model = FriendRequest
        fields = "__all__"

    def get_sender_profile(self, obj) -> Optional[dict]:
        try:
            return UserProfileSerializer(obj.sender.user_profile).data
        except (ObjectDoesNotExist, AttributeError):
            return None

    def get_receiver_profile(self, obj) -> Optional[dict]:
        try:
            return UserProfileSerializer(obj.receiver.user_profile).data
        except (ObjectDoesNotExist, AttributeError):
            return None


class CreateCrewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Crew
        fields = ["name", "bio"]

    def get_fields_metadata(self):
        """Return field metadata for frontend usage"""
        return {
            "name": {
                "max_length": 100,
                "help_text": self.fields['name'].help_text,
                "required": True,
            },
            "bio": {
                "max_length": 150,
                "help_text": self.fields['bio'].help_text,
                "required": False,
            },
        }


class CrewRequestSerializer(serializers.ModelSerializer):
    sender_details = serializers.SerializerMethodField()
    receiver_details = serializers.SerializerMethodField()
    crew_details = serializers.SerializerMethodField()

    class Meta:
        model = CrewRequest
        fields = [
            "requestId", "status", "created_at", "updated_at", 
            "sender_details", "receiver_details", "crew_details"
        ]

    def get_sender_details(self, obj) -> dict:
        # Only include full user details when specifically requested
        if self.context.get('include_user_details', False):
            try:
                return {
                    "user": CustomUserSerializer(obj.sender).data,
                    "profile": UserProfileSerializer(obj.sender.user_profile).data if hasattr(obj.sender, 'user_profile') else None
                }
            except (ObjectDoesNotExist, AttributeError):
                pass
                
        # Otherwise return minimal data
        return {
            "id": obj.sender.id,
            "username": obj.sender.username,
            "first_name": obj.sender.first_name,
            "last_name": obj.sender.last_name,
        }

    def get_receiver_details(self, obj) -> dict:
        # Only include full user details when specifically requested
        if self.context.get('include_user_details', False):
            try:
                return {
                    "user": CustomUserSerializer(obj.receiver).data,
                    "profile": UserProfileSerializer(obj.receiver.user_profile).data if hasattr(obj.receiver, 'user_profile') else None
                }
            except (ObjectDoesNotExist, AttributeError):
                pass
                
        # Otherwise return minimal data
        return {
            "id": obj.receiver.id,
            "username": obj.receiver.username,
            "first_name": obj.receiver.first_name,
            "last_name": obj.receiver.last_name,
        }

    def get_crew_details(self, obj) -> dict:
        # Return minimal crew data to avoid deep serialization
        return {
            "crewId": str(obj.crew.crewId),
            "name": obj.crew.name,
            "created_by_username": obj.crew.created_by.username if obj.crew.created_by else None,
        }

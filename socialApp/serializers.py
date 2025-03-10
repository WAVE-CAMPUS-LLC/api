from rest_framework import serializers
from django.core.exceptions import ObjectDoesNotExist
from typing import Optional
from .models import Crew, CrewMember, CrewRequest, FriendRequest
from .forms import createCrewForm
from authenticationApp.serializers import CustomUserSerializer
from accountManagementApp.serializers import UserProfileSerializer
from eventManagementApp.serializers import SharedEventWithoutCrewSerializer


class CrewMemberSerializer(serializers.ModelSerializer):
    user = CustomUserSerializer()
    user_profile = serializers.SerializerMethodField()

    class Meta:
        model = CrewMember
        fields = "__all__"

    def get_user_profile(self, obj) -> Optional[dict]:
        try:
            return UserProfileSerializer(obj.user.user_profile).data
        except (ObjectDoesNotExist, AttributeError):
            return None


class CrewSerializer(serializers.ModelSerializer):
    created_by = CustomUserSerializer()
    created_by_profile = serializers.SerializerMethodField()
    crew_members = CrewMemberSerializer(many=True, source="crew_members.all")
    shared_events = serializers.SerializerMethodField()

    class Meta:
        model = Crew
        fields = "__all__"

    def get_created_by_profile(self, obj) -> Optional[dict]:
        try:
            return UserProfileSerializer(obj.created_by.user_profile).data
        except (ObjectDoesNotExist, AttributeError):
            return None

    def get_shared_events(self, obj) -> list:
        from eventManagementApp.models import SharedEvent
        from eventManagementApp.serializers import SharedEventWithoutCrewSerializer

        try:
            # Get only the 5 most recent shared events and use prefetch_related to reduce queries
            shared_events = SharedEvent.objects.filter(crew=obj).order_by('-shared_at')[:5]
            
            # Eagerly evaluate the queryset into a list to ensure the database cursor is properly closed
            events_list = list(shared_events)
            
            # Use non_atomic serializer context to prevent cascading serialization
            context = {'non_atomic': True}
            return SharedEventWithoutCrewSerializer(events_list, many=True, context=context).data
        except Exception as e:
            # Log error but don't break the entire API response
            print(f"Error serializing shared events for crew {obj.crewId}: {e}")
            return []


class FriendRequestSerializer(serializers.ModelSerializer):
    sender = CustomUserSerializer()
    receiver = CustomUserSerializer()
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
        fields = createCrewForm.Meta.fields

    def get_fields_metadata(self):
        return {
            field: {
                "type": str(field_instance.__class__.__name__),
                "required": field_instance.required,
            }
            for field, field_instance in createCrewForm().fields.items()
        }


class CrewRequestSerializer(serializers.ModelSerializer):
    sender = CustomUserSerializer()
    receiver = CustomUserSerializer()
    crew = CrewSerializer()

    class Meta:
        model = CrewRequest
        fields = "__all__"

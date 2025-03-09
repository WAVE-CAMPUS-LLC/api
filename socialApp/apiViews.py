from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.urls import reverse
from datetime import datetime
from django.utils.timezone import now
from rest_framework import status
from .models import FriendRequest, Crew, CrewMember, CrewRequest
from accountManagementApp.models import UserProfile
from authenticationApp.models import CustomUser
from eventManagementApp.models import SharedEvent
from accountManagementApp.serializers import UserProfileSerializer
from eventManagementApp.serializers import SharedEventSerializer
from .serializers import (
    CrewSerializer,
    FriendRequestSerializer,
    CrewRequestSerializer,
    CrewMemberSerializer
)
from authenticationApp.serializers import CustomUserSerializer
from django.contrib.auth import get_user_model
from django.db.models import Q
from .views import send_crew_request, leave_crew, delete_crew, kick_member
from django.views.decorators.csrf import csrf_exempt
from wave_v1.decorators import check_suspension, member, verified


class SocialHomeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_profile = get_object_or_404(UserProfile, user=request.user)
        site_url = settings.SITE_URL
        profile_link = f"{site_url}{reverse('social:publicProfile', kwargs={'username': user_profile.user.username})}"

        my_crews = Crew.objects.filter(created_by=request.user)
        crews_im_in = Crew.objects.filter(crew_members__user=request.user).exclude(
            created_by=request.user
        )
        friends = user_profile.friends.all()
        my_shared_events = SharedEvent.objects.filter(
            sender=user_profile
        ).select_related("event", "receiver", "crew")
        shared_with_me = SharedEvent.objects.filter(
            receiver=user_profile
        ).select_related("event", "sender", "crew")
        pending_friend_requests = FriendRequest.objects.filter(
            receiver=request.user, status="pending"
        )
        sent_friend_requests = FriendRequest.objects.filter(
            sender=request.user, status="pending"
        )
        pending_crew_requests = CrewRequest.objects.filter(
            receiver=request.user, status="pending"
        )
        sent_crew_requests = CrewRequest.objects.filter(
            sender=request.user, status="pending"
        )

        is_host = user_profile.user.groups.filter(name="Host").exists()
        is_active_user = (
            user_profile.user.groups.filter(name="Onboarded").exists()
            and user_profile.user.groups.filter(name="Verified").exists()
        )

        response_data = {
            "user_profile": UserProfileSerializer(user_profile).data,
            "profile_link": profile_link,
            "friends": UserProfileSerializer(friends, many=True).data,
            "my_crews": CrewSerializer(my_crews, many=True).data,
            "crews_im_in": CrewSerializer(crews_im_in, many=True).data,
            "my_shared_events": SharedEventSerializer(my_shared_events, many=True).data,
            "shared_with_me": SharedEventSerializer(shared_with_me, many=True).data,
            "pending_friend_requests": FriendRequestSerializer(
                pending_friend_requests, many=True
            ).data,
            "sent_friend_requests": FriendRequestSerializer(
                sent_friend_requests, many=True
            ).data,
            "pending_crew_requests": CrewRequestSerializer(
                pending_crew_requests, many=True
            ).data,
            "sent_crew_requests": CrewRequestSerializer(
                sent_crew_requests, many=True
            ).data,
            "is_host": is_host,
            "is_active_user": is_active_user,
            "timestamp": now().timestamp(),
        }

        return Response(response_data, status=status.HTTP_200_OK)


class NonFriendsListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        User = get_user_model()

        # Get all accepted friend requests where the current user is either sender or receiver
        accepted_friends = FriendRequest.objects.filter(
            (Q(sender=request.user) | Q(receiver=request.user)), status="accepted"
        )

        # Get the list of friend user IDs
        friend_ids = []
        for friendship in accepted_friends:
            if friendship.sender == request.user:
                friend_ids.append(friendship.receiver.id)
            else:
                friend_ids.append(friendship.sender.id)

        # Get all users who are not friends (excluding the request user), and who have profiles
        non_friends = (
            User.objects.filter(
                user_profile__isnull=False  # Only include users who have profiles
            )
            .exclude(id__in=friend_ids)
            .exclude(id=request.user.id)
            .select_related("user_profile")
        )

        # Create a list to store combined data
        combined_data = []
        for user in non_friends:
            try:
                user_data = CustomUserSerializer(user).data
                profile_data = UserProfileSerializer(user.user_profile).data
                combined_data.append({"user": user_data, "profile": profile_data})
            except User.user_profile.RelatedObjectDoesNotExist:
                # Skip users without profiles (this shouldn't happen due to our filter, but just in case)
                continue

        return Response(combined_data, status=status.HTTP_200_OK)


class PublicProfileAPIView(APIView):
    permission_classes = []  # Remove default permission requirements

    def get(self, request, username):
        """
        Get a user's public profile - accessible to anyone
        """
        try:
            # Get the requested user and their profile
            other_user = get_object_or_404(CustomUser, username=username)
            other_user_profile, created = UserProfile.objects.get_or_create(
                user=other_user
            )

            # Initialize friend-related data
            friend_request_status = None
            friend_request_id = None
            is_profile = False

            # Only check friendship status if the user is authenticated
            if request.user.is_authenticated:
                # Check if the users are friends or have pending requests
                friend_request = FriendRequest.objects.filter(
                    (Q(sender=request.user) & Q(receiver=other_user))
                    | (Q(sender=other_user) & Q(receiver=request.user))
                ).first()

                if friend_request:
                    friend_request_status = friend_request.status
                    friend_request_id = str(friend_request.requestId)

                is_profile = request.user.id == other_user.id

            # Prepare response data
            response_data = {
                "user": CustomUserSerializer(other_user).data,
                "user_profile": UserProfileSerializer(other_user_profile).data,
                "is_profile": is_profile,
            }

            # Only include friendship data for authenticated users
            if request.user.is_authenticated:
                response_data.update(
                    {
                        "friend_request_status": friend_request_status,
                        "friend_request_id": friend_request_id,
                        "can_send_request": request.user.is_authenticated,
                    }
                )

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)


# Crew API Setup
@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def crew_api_view(request, crewId):
    user_profile = get_object_or_404(UserProfile, user=request.user)
    crew = get_object_or_404(Crew, crewId=crewId)

    crew_members = CrewMember.objects.filter(crew=crew)
    is_in_crew = CrewMember.objects.filter(crew=crew, user=request.user).exists()

    friends = user_profile.friends.all()
    friends_not_in_crew = friends.exclude(
        user__in=crew_members.values_list("user", flat=True)
    )
    
    try:
        shared_events = SharedEvent.objects.filter(crew=crew).select_related('event', 'sender', 'receiver', 'crew')
        shared_events_serialized = SharedEventSerializer(shared_events, many=True)
    except Exception as e:
        shared_events_serialized = []

    pending_friends = [
        friend
        for friend in friends_not_in_crew
        if friend.has_pending_crew_request(request.user)
    ]
    declined_friends = [
        friend
        for friend in friends_not_in_crew
        if friend.has_declined_crew_request(request.user)
    ]
    not_invited_friends = friends_not_in_crew.exclude(
        user__username__in=[f.user.username for f in pending_friends]
    ).exclude(user__username__in=[f.user.username for f in declined_friends])

    if request.method == "POST":
        action = request.data.get("action")

        if action == "crew_invite":
            invitee_username = request.data.get("invitee_username")
            success, message, _ = send_crew_request(
                user_profile, invitee_username, crewId
            )
            return Response({"success": success, "message": message})

        elif action == "leave_crew":
            leave_crew(request, crewId)
            return Response({"message": "You have left the crew."})

        elif action == "delete_crew":
            delete_crew(request, crewId)
            return Response({"message": "Crew deleted successfully."})

        elif action == "kick_member":
            member_username = request.data.get("member")
            kick_member(request, crewId, member_username)
            return Response(
                {"message": f"{member_username} has been removed from the crew."}
            )

    return Response(
        {
            "crew": CrewSerializer(crew).data,
            "self": UserProfileSerializer(user_profile).data,
            "crewMembers": CrewMemberSerializer(crew_members, many=True).data,
            "pendingFriends": UserProfileSerializer(pending_friends, many=True).data,
            "declinedFriends": UserProfileSerializer(declined_friends, many=True).data,
            "notInvitedFriends": UserProfileSerializer(not_invited_friends, many=True).data,
            "time": datetime.now().timestamp(),
            "sharedEvents": shared_events_serialized.data if hasattr(shared_events_serialized, 'data') else [],
            "isCrewOwner": crew.created_by == request.user,
            "isInCrew": is_in_crew,
        }
    )

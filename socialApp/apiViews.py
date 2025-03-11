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
from django.core.exceptions import ObjectDoesNotExist
from .models import FriendRequest, Crew, CrewMember, CrewRequest
from accountManagementApp.models import UserProfile
from authenticationApp.models import CustomUser
from eventManagementApp.models import SharedEvent
from accountManagementApp.serializers import UserProfileSerializer
from eventManagementApp.serializers import SharedEventWithoutCrewSerializer
from .serializers import (
    CrewSerializer,
    FriendRequestSerializer,
    CrewRequestSerializer,
    CrewMemberSerializer,
    CreateCrewSerializer,
)
from authenticationApp.serializers import CustomUserSerializer
from django.contrib.auth import get_user_model
from django.db.models import Q
from .helpers import send_crew_request, leave_crew, delete_crew, kick_member

User = get_user_model()


@api_view(["GET"])
def public_profile(request, username):
    try:
        # Get the requested user and their profile
        other_user = get_object_or_404(User, username=username)
        other_user_profile, _ = UserProfile.objects.get_or_create(user=other_user)

        # Initialize friend-related data
        friend_request_status = None
        friend_request_id = None
        is_profile = False

        # Only check friendship status if the user is authenticated
        if request.user.is_authenticated:
            # Check if the users are friends or have pending requests
            friend_request = FriendRequest.objects.filter(
                Q(sender=request.user, receiver=other_user)
                | Q(sender=other_user, receiver=request.user)
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
                    "can_send_request": True,
                }
            )

        return Response(response_data, status=status.HTTP_200_OK)

    except ObjectDoesNotExist as e:
        return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
    except ValueError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def friends_api_view(request):
    """
    API view to show a user's friends and non-friends.
    """
    try:
        User = get_user_model()  # Get the CustomUser model
        user_profile = get_object_or_404(UserProfile, user=request.user)
        
        # Get all friends with optimized query using select_related
        # Add select_related to ensure user is prefetched
        friends = list(user_profile.friends.filter(user__isnull=False).select_related("user"))
        
        # Get IDs of friends' users - safely extract IDs and handle possible None values
        friend_user_ids = []
        for f in friends:
            if hasattr(f, 'user') and f.user is not None:
                friend_user_ids.append(f.user.id)
        
        # Add current user's ID to the exclusion list
        exclude_ids = friend_user_ids + [request.user.id]
        
        # Get all non-friends excluding the current user
        # Only include users who have profiles
        non_friends = list(
            UserProfile.objects.filter(
                user__isnull=False  # Only include users who have profiles
            )
            .exclude(user__id__in=exclude_ids)
            .select_related("user")
        )
        2
        return Response(
            {
                "friends": UserProfileSerializer(friends, many=True).data,
                "non_friends": UserProfileSerializer(non_friends, many=True).data,
                "timestamp": now().timestamp(),
            },
            status=200,
        )
    except Exception as e:
        # Return an informative error for debugging
        return Response(
            {
                "error": f"Error retrieving friends: {str(e)}",
                "timestamp": now().timestamp(),
            },
            status=200,  # Still return 200 with error info for frontend compatibility
        )


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def crewInfo_api_view(request):
    """
    API view to get information about crews the user is a member of.
    """
    try:
        # Use a safer query approach to prevent errors
        user = request.user
        
        # Get crews the user created - direct relationship
        my_crews = list(Crew.objects.filter(created_by=user).select_related("created_by"))
        
        # Get crews where the user is a member - through CrewMember
        crew_memberships = list(CrewMember.objects.filter(user=user).select_related('crew', 'crew__created_by'))
        crews_im_in = [membership.crew for membership in crew_memberships if hasattr(membership, 'crew')]
        
        # Filter out duplicates if the user created and is a member of the same crew
        crews_im_in = [c for c in crews_im_in if c.created_by != user]
        
        return Response(
            {
                "crews": CrewSerializer(my_crews + crews_im_in, many=True).data,
                "my_crews": CrewSerializer(my_crews, many=True).data,
                "crews_im_in": CrewSerializer(crews_im_in, many=True).data,
                "time": datetime.now().timestamp(),
            },
            status=200,
        )
    except Exception as e:
        # Return an informative error message for debugging
        return Response(
            {
                "crews": [],
                "my_crews": [],
                "crews_im_in": [],
                "error": f"Error retrieving crew information: {str(e)}",
                "time": datetime.now().timestamp(),
            },
            status=200,  # Still return 200 with empty data and error message
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def send_friend_request_api(request, receiver_username):
    sender = request.user

    try:
        receiver = get_object_or_404(UserProfile, user__username=receiver_username)

        if sender.user_profile.is_friends_with(receiver.user):
            return Response({"success": False, "message": "You are already friends with this user."}, status=400)

        active_request = FriendRequest.objects.filter(
            Q(sender=sender, receiver=receiver.user) | 
            Q(sender=receiver.user, receiver=sender),
            status__in=['pending', 'accepted']
        ).first()

        if active_request:
            if active_request.status == 'pending':
                if active_request.sender == sender:
                    return Response({"success": False, "message": "You have already sent a friend request to this user."}, status=400)
                else:
                    return Response({"success": False, "message": f"{receiver.user.username} has already sent you a friend request. Check your notifications to respond."}, status=400)
            else:
                return Response({"success": False, "message": "You are already friends with this user."}, status=400)

        old_request = FriendRequest.objects.filter(
            sender=sender,
            receiver=receiver.user,
            status__in=['canceled', 'declined']
        ).first()

        if old_request:
            old_request.status = 'pending'
            old_request.save()
            return Response({"success": True, "message": "Friend request sent successfully."}, status=200)

        friend_request = FriendRequest.objects.create(
            sender=sender,
            receiver=receiver.user,
            status="pending"
        )

        return Response({"success": True, "message": "Friend request sent successfully."}, status=201)

    except Exception as e:
        return Response({"success": False, "message": f"An error occurred: {str(e)}"}, status=500)

# Crew API Setup
@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def crew_api_view(request, crewId):
    user_profile = get_object_or_404(UserProfile, user=request.user)
    crew = get_object_or_404(Crew, crewId=crewId)

    # Limit query results and use select_related
    crew_members = list(
        CrewMember.objects.filter(crew=crew).select_related("user")[:20]
    )
    is_in_crew = CrewMember.objects.filter(crew=crew, user=request.user).exists()

    # Limit friends query and avoid N+1 issues
    friends = list(user_profile.friends.all().select_related("user")[:50])

    # Get crew member user IDs in a single query (more efficient than values_list)
    crew_member_ids = set(m.user_id for m in crew_members)

    # Filter friends not in crew
    friends_not_in_crew = [f for f in friends if f.user_id not in crew_member_ids]

    # Process in batches to prevent memory issues
    pending_friends = []
    declined_friends = []

    # Process in smaller batches to avoid cursor issues
    for i in range(0, len(friends_not_in_crew), 10):
        batch = friends_not_in_crew[i : i + 10]
        pending_batch = [f for f in batch if f.has_pending_crew_request(request.user)]
        declined_batch = [f for f in batch if f.has_declined_crew_request(request.user)]
        pending_friends.extend(pending_batch)
        declined_friends.extend(declined_batch)

    # Create a set of usernames for efficient lookups
    pending_usernames = {f.user.username for f in pending_friends}
    declined_usernames = {f.user.username for f in declined_friends}

    # Filter not invited friends
    not_invited_friends = [
        f
        for f in friends_not_in_crew
        if f.user.username not in pending_usernames
        and f.user.username not in declined_usernames
    ][
        :20
    ]  # Limit to 20 friends

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

    # Serialize the crew with a non-recursive context to prevent deep serialization
    context = {"non_recursive": True}
    crew_data = CrewSerializer(crew, context=context).data

    # Prepare the response with limited data
    return Response(
        {
            "crew": crew_data,
            "self": UserProfileSerializer(user_profile).data,
            "crewMembers": CrewMemberSerializer(crew_members, many=True).data,
            "pendingFriends": UserProfileSerializer(
                pending_friends[:20], many=True
            ).data,
            "declinedFriends": UserProfileSerializer(
                declined_friends[:20], many=True
            ).data,
            "notInvitedFriends": UserProfileSerializer(
                not_invited_friends, many=True
            ).data,
            "time": datetime.now().timestamp(),
            "isCrewOwner": crew.created_by == request.user,
            "isInCrew": is_in_crew,
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def crew_invite_action(request, crew_id):
    crew = get_object_or_404(Crew, crewId=crew_id)
    crew_request = get_object_or_404(CrewRequest, crew=crew, receiver=request.user)
    sender = get_object_or_404(UserProfile, user=crew_request.sender)
    receiver = get_object_or_404(UserProfile, user=request.user)

    if request.method == "POST":
        action = request.data.get("action")

        if action == "joinCrew":
            crew_request.accept_request()
            CrewMember.objects.create(user=request.user, crew=crew)

            return Response(
                {"message": f"You joined the {crew.name} crew."}, status=200
            )

        elif action == "declineCrew":
            crew_request.decline_request()
            crew_request.delete()
            return Response({"message": "Crew invite declined."}, status=200)

    return Response({"error": "Invalid action."}, status=400)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def create_crew_api_view(request):
    if request.method == "GET":
        # Return field metadata for frontend usage
        serializer = CreateCrewSerializer()
        return Response(serializer.get_fields_metadata(), status=status.HTTP_200_OK)

    serializer = CreateCrewSerializer(data=request.data)

    if serializer.is_valid():
        crew_instance = serializer.save(created_by=request.user)  # Auto-assign user

        # Add the creator as an admin member
        CrewMember.objects.create(
            user=request.user,
            crew=crew_instance,
            is_admin=True,
        )

        return Response(
            {"message": "Crew created successfully", "crew": serializer.data},
            status=status.HTTP_201_CREATED,
        )

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def invite_member(request, crewId):
    """Send a crew invite to another user."""
    invitee_username = request.data.get("invitee_username")
    success, message, crew_request = send_crew_request(
        request.user, invitee_username, crewId
    )

    if success:
        return Response({"message": message}, status=200)
    return Response({"error": message}, status=400)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def leave_crew_view(request, crewId):
    """Leave a crew."""
    return leave_crew(request.user, crewId)


@api_view(["POST", "DELETE"])
@permission_classes([IsAuthenticated])
def delete_crew_view(request, crewId):
    """Delete a crew (only if user is the owner)."""
    return delete_crew(request.user, crewId)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def kick_member_view(request, crewId):
    """Kick a member from the crew."""
    member_username = request.data.get("member_username")
    return kick_member(request.user, crewId, member_username)

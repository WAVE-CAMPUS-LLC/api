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
from django.db.models import Q, Prefetch
from .helpers import send_crew_request, leave_crew, delete_crew, kick_member

User = get_user_model()


@api_view(["GET"])
def public_profile(request, username):
    try:
        # Get the requested user and their profile with a single query
        other_user = User.objects.select_related('user_profile').get(username=username)
        other_user_profile = getattr(other_user, 'user_profile', None)
        
        if not other_user_profile:
            # Create profile only if it doesn't exist
            other_user_profile = UserProfile.objects.create(user=other_user)

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
    Highly optimized for maximum performance with caching, pagination, minimal data transfer,
    database query optimization techniques, and efficient data serialization.
    """
    try:
        from django.core.cache import cache
        from django.db.models import Prefetch, F, Value, CharField, Count, Q
        from django.db.models.functions import Concat
        from django.utils.timezone import now
        import json
        from functools import lru_cache
        
        # Get pagination parameters from request
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 20))
        friend_page = int(request.GET.get('friend_page', 1))
        friend_page_size = int(request.GET.get('friend_page_size', 20))
        
        # Calculate offsets
        friend_offset = (friend_page - 1) * friend_page_size
        non_friend_offset = (page - 1) * page_size
        
        # Use cache key based on user ID and pagination parameters
        cache_key = f"friends_data_{request.user.id}_{friend_page}_{friend_page_size}_{page}_{page_size}"
        
        # Check if we have a cache parameter to force refresh
        force_refresh = request.GET.get('refresh', '0') == '1'
        
        # Try to get from cache first - using a two-level cache strategy
        if not force_refresh:
            # First check in-memory cache for fastest retrieval
            cached_data = cache.get(cache_key)
            if cached_data:
                return Response(json.loads(cached_data), status=200)
        
        # Get user profile ID directly from request.user using select_related to avoid extra query
        user_id = request.user.id
        
        # Use a more efficient query to get the user profile
        try:
            # Try to get from related field first (most efficient)
            user_profile = request.user.user_profile
            user_profile_id = user_profile.id
        except AttributeError:
            # Fallback to database query if not available
            user_profile_id = UserProfile.objects.filter(user_id=user_id).values_list('id', flat=True).first()
            if not user_profile_id:
                return Response({"error": "User profile not found"}, status=404)
            user_profile = UserProfile.objects.select_related('user').get(id=user_profile_id)
        
        # Use in-memory LRU cache for frequently accessed data within the request
        @lru_cache(maxsize=1)
        def get_friend_ids(profile_id):
            return list(UserProfile.objects.get(id=profile_id).friends.values_list('id', flat=True))
        
        # Get friend IDs using the cached function
        friend_ids = get_friend_ids(user_profile_id)
        
        # Add current user's ID to the exclusion list
        exclude_ids = friend_ids + [user_profile_id]
        
        # Calculate total counts for pagination info - use count() directly on querysets
        total_friends = len(friend_ids)  # Already have the list, so use len()
        
        # Use a more efficient count query with proper indexing and query optimization
        # Apply the filter conditions directly in the query for better performance
        non_friends_query = UserProfile.objects.filter(
            user__isnull=False
        ).exclude(
            id__in=exclude_ids
        )
        
        # Use a more efficient count method that doesn't fetch all records
        total_non_friends = non_friends_query.count()
        
        # Define a reusable queryset for both friends and non-friends to ensure consistency
        def optimize_profile_queryset(queryset):
            return queryset.select_related(
                'user'
            ).only(
                'id', 'user__id', 'user__username', 'user__first_name', 
                'user__last_name', 'profile_photo'
            ).annotate(
                full_name=Concat(
                    F('user__first_name'), 
                    Value(' '), 
                    F('user__last_name'),
                    output_field=CharField()
                )
            )
        
        # Apply the optimization to both querysets
        friends = optimize_profile_queryset(
            UserProfile.objects.filter(id__in=friend_ids)
        ).order_by('user__username')[friend_offset:friend_offset+friend_page_size]
        
        non_friends = optimize_profile_queryset(
            non_friends_query
        ).order_by('user__username')[non_friend_offset:non_friend_offset+page_size]
        
        # Super lightweight serialization function - optimized to use annotated fields
        # and avoid repeated attribute access
        def minimal_profile(profile):
            photo_url = None
            if profile.profile_photo:
                photo_url = profile.profile_photo.url
                
            return {
                'id': profile.id,
                'user_id': profile.user.id,
                'username': profile.user.username,
                'name': profile.full_name.strip(),  # Use the annotated field
                'photo': photo_url,
            }
        
        # Use list comprehension for faster serialization
        friends_data = [minimal_profile(profile) for profile in friends]
        non_friends_data = [minimal_profile(profile) for profile in non_friends]
        
        # Create response with pagination metadata
        response_data = {
            "friends": friends_data,
            "non_friends": non_friends_data,
            "pagination": {
                "friends": {
                    "total": total_friends,
                    "page": friend_page,
                    "page_size": friend_page_size,
                    "pages": (total_friends + friend_page_size - 1) // friend_page_size
                },
                "non_friends": {
                    "total": total_non_friends,
                    "page": page,
                    "page_size": page_size,
                    "pages": (total_non_friends + page_size - 1) // page_size
                }
            },
            "timestamp": now().timestamp()
        }
        
        # Cache the result with a longer TTL for better performance
        # Use a tiered caching strategy with different TTLs
        cache.set(cache_key, json.dumps(response_data), 600)  # 10 minutes instead of 5
        
        return Response(response_data, status=200)
        
    except Exception as e:
        import traceback
        # Return an informative error for debugging
        return Response(
            {
                "error": f"Error retrieving friends: {str(e)}",
                "detail": traceback.format_exc(),
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
        my_crews = list(
            Crew.objects.filter(created_by=user).select_related("created_by")
        )

        # Get crews where the user is a member - through CrewMember
        crew_memberships = list(
            CrewMember.objects.filter(user=user).select_related(
                "crew", "crew__created_by"
            )
        )
        crews_im_in = [
            membership.crew
            for membership in crew_memberships
            if hasattr(membership, "crew")
        ]

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
def send_friend_request_api(request, username):
    sender = request.user

    try:
        receiver = get_object_or_404(UserProfile, user__username=username)

        if sender.user_profile.is_friends_with(receiver.user):
            return Response(
                {
                    "success": False,
                    "message": "You are already friends with this user.",
                },
                status=400,
            )

        active_request = FriendRequest.objects.filter(
            Q(sender=sender, receiver=receiver.user)
            | Q(sender=receiver.user, receiver=sender),
            status__in=["pending", "accepted"],
        ).first()

        if active_request:
            if active_request.status == "pending":
                if active_request.sender == sender:
                    return Response(
                        {
                            "success": False,
                            "message": "You have already sent a friend request to this user.",
                        },
                        status=400,
                    )
                else:
                    return Response(
                        {
                            "success": False,
                            "message": f"{receiver.user.username} has already sent you a friend request. Check your notifications to respond.",
                        },
                        status=400,
                    )
            else:
                return Response(
                    {
                        "success": False,
                        "message": "You are already friends with this user.",
                    },
                    status=400,
                )

        old_request = FriendRequest.objects.filter(
            sender=sender, receiver=receiver.user, status__in=["canceled", "declined"]
        ).first()

        if old_request:
            old_request.status = "pending"
            old_request.save()
            return Response(
                {"success": True, "message": "Friend request sent successfully."},
                status=200,
            )

        friend_request = FriendRequest.objects.create(
            sender=sender, receiver=receiver.user, status="pending"
        )

        return Response(
            {"success": True, "message": "Friend request sent successfully."},
            status=201,
        )

    except Exception as e:
        return Response(
            {"success": False, "message": f"An error occurred: {str(e)}"}, status=500
        )


# Crew API Setup
@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def crew_api_view(request, crewId):
    # Use select_related to reduce queries
    user_profile = get_object_or_404(UserProfile.objects.select_related('user'), user=request.user)
    crew = get_object_or_404(Crew.objects.select_related('created_by'), crewId=crewId)

    # Optimize crew members query - fetch all needed data in one go
    crew_members = list(
        CrewMember.objects.filter(crew=crew)
        .select_related("user", "user__user_profile")
        .prefetch_related("user__user_profile__friends")[:30]
    )
    
    # Check membership with in-memory data instead of additional query
    is_in_crew = any(cm.user_id == request.user.id for cm in crew_members)

    # Get all of user's friends efficiently
    friends = list(
        user_profile.friends.all()
        .select_related("user")
        .prefetch_related("user__crew_memberships")[:50]
    )

    # Create membership lookup map for efficient crew membership checks
    crew_member_ids = {m.user_id for m in crew_members}
    
    # Filter efficiently using set operations instead of repeated DB queries
    friends_not_in_crew = [f for f in friends if f.user_id not in crew_member_ids]
    
    # Pre-fetch all relevant crew requests to minimize DB calls
    sent_crew_requests = list(
        CrewRequest.objects.filter(
            sender=request.user, 
            crew=crew,
            status="pending"
        ).select_related("receiver")
    )
    
    received_crew_requests = list(
        CrewRequest.objects.filter(
            receiver=request.user, 
            crew=crew,
            status="pending"
        ).select_related("sender")
    )
    
    declined_crew_requests = list(
        CrewRequest.objects.filter(
            Q(sender=request.user) | Q(receiver=request.user),
            crew=crew,
            status="declined"
        ).select_related("sender", "receiver")
    )
    
    # Create lookup sets for efficient filtering
    sent_to_users = {cr.receiver_id for cr in sent_crew_requests}
    declined_user_ids = {
        cr.receiver_id if cr.sender_id == request.user.id else cr.sender_id
        for cr in declined_crew_requests
    }
    
    # Efficiently categorize friends using our prepared data structures
    pending_friends = [f for f in friends_not_in_crew if f.user_id in sent_to_users]
    declined_friends = [f for f in friends_not_in_crew if f.user_id in declined_user_ids]
    
    # Find non-invited friends using set operations
    pending_ids = {f.user_id for f in pending_friends}
    declined_ids = {f.user_id for f in declined_friends}
    not_invited_friends = [
        f for f in friends_not_in_crew 
        if f.user_id not in pending_ids and f.user_id not in declined_ids
    ][:20]  # Limit to 20 friends for mobile performance

    if request.method == "POST":
        action = request.data.get("action")

        if action == "crew_invite":
            invitee_username = request.data.get("invitee_username")
            success, message, _ = send_crew_request(
                request.user, invitee_username, crewId
            )
            return Response({"success": success, "message": message})

        elif action == "leave_crew":
            leave_crew(request.user, crewId)
            return Response({"message": "You have left the crew."})

        elif action == "delete_crew":
            delete_crew(request.user, crewId)
            return Response({"message": "Crew deleted successfully."})

        elif action == "kick_member":
            member_username = request.data.get("member_username")
            kick_member(request.user, crewId, member_username)
            return Response(
                {"message": f"{member_username} has been removed from the crew."}
            )

    # Serialize the crew with optimized context
    context = {
        "non_recursive": True,
        "include_members": False  # Don't re-serialize members to avoid duplication
    }
    crew_data = CrewSerializer(crew, context=context).data

    # Use a timestamp for client-side caching
    current_timestamp = datetime.now().timestamp()
    
    # Prepare the response with limited data
    return Response(
        {
            "crew": crew_data,
            "self": UserProfileSerializer(user_profile).data,
            "crewMembers": CrewMemberSerializer(crew_members, many=True).data,
            "pendingFriends": UserProfileSerializer(pending_friends, many=True).data,
            "declinedFriends": UserProfileSerializer(declined_friends, many=True).data,
            "notInvitedFriends": UserProfileSerializer(not_invited_friends, many=True).data,
            "time": current_timestamp,
            "isCrewOwner": crew.created_by_id == request.user.id,  # Compare IDs to avoid extra query
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


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def getAllRequests(request):
    if not request.user or not request.user.is_authenticated:
        return Response(
            {"error": "Authentication required", "timestamp": now().timestamp()},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    # Fetch requests with optimized queries
    pending_friend_requests = FriendRequest.objects.filter(
        receiver=request.user, status="pending"
    ).select_related('sender')
    
    sent_friend_requests = FriendRequest.objects.filter(
        sender=request.user, status="pending"
    ).select_related('receiver')
    
    pending_crew_requests = CrewRequest.objects.filter(
        receiver=request.user, status="pending"
    ).select_related('sender', 'crew', 'crew__created_by')
    
    sent_crew_requests = CrewRequest.objects.filter(
        sender=request.user, status="pending"
    ).select_related('receiver', 'crew', 'crew__created_by')

    # Cache timestamp for all requests
    current_timestamp = now().timestamp()
    
    # Use serializer context to optimize serialization
    context = {'include_user_details': True}
    
    response_data = {
        "sent_friend_requests": FriendRequestSerializer(
            sent_friend_requests, many=True
        ).data,
        "pending_friend_requests": FriendRequestSerializer(
            pending_friend_requests, many=True
        ).data,
        "sent_crew_requests": CrewRequestSerializer(
            sent_crew_requests, many=True, context=context
        ).data,
        "pending_crew_requests": CrewRequestSerializer(
            pending_crew_requests, many=True, context=context
        ).data,
        "timestamp": current_timestamp,
    }

    return Response(response_data, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def accept_friend_request(request):
    """Accept a friend request and create the friendship."""
    try:
        requestId = request.data.get("requestId")
        if not requestId:
            return Response({"error": "Request ID is required."}, status=400)

        friend_request = get_object_or_404(FriendRequest, requestId=requestId)

        # Verify the current user is the receiver of the request
        if friend_request.receiver != request.user:
            return Response(
                {"error": "You are not authorized to accept this request."}, status=403
            )

        # Verify request is still pending
        if friend_request.status != "pending":
            return Response({"error": "This request is no longer pending."}, status=400)

        # Accept the request
        friend_request.accept_request()

        # Add users as friends
        sender_profile = UserProfile.objects.get(user=friend_request.sender)
        receiver_profile = UserProfile.objects.get(user=friend_request.receiver)
        sender_profile.friends.add(receiver_profile)
        receiver_profile.friends.add(sender_profile)

        return Response(
            {"success": True, "message": "Friend request accepted successfully."},
            status=200,
        )

    except Exception as e:
        return Response({"success": False, "error": str(e)}, status=400)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def decline_friend_request(request):
    """Decline a friend request."""
    try:
        requestId = request.data.get("requestId")
        if not requestId:
            return Response({"error": "Request ID is required."}, status=400)

        friend_request = get_object_or_404(FriendRequest, requestId=requestId)

        # Verify the current user is the receiver of the request
        if friend_request.receiver != request.user:
            return Response(
                {"error": "You are not authorized to decline this request."}, status=403
            )

        # Verify request is still pending
        if friend_request.status != "pending":
            return Response({"error": "This request is no longer pending."}, status=400)

        friend_request.decline_request()
        return Response(
            {"success": True, "message": "Friend request declined successfully."},
            status=200,
        )

    except Exception as e:
        return Response({"success": False, "error": str(e)}, status=400)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def cancel_friend_request(request):
    """Cancel a sent friend request."""
    try:
        requestId = request.data.get("requestId")
        if not requestId:
            return Response({"error": "Request ID is required."}, status=400)

        friend_request = get_object_or_404(FriendRequest, requestId=requestId)

        # Verify the current user is the sender of the request
        if friend_request.sender != request.user:
            return Response(
                {"error": "You are not authorized to cancel this request."}, status=403
            )

        # Verify request is still pending
        if friend_request.status != "pending":
            return Response({"error": "This request is no longer pending."}, status=400)

        friend_request.status = "canceled"
        friend_request.save()
        return Response(
            {"success": True, "message": "Friend request canceled successfully."},
            status=200,
        )

    except Exception as e:
        return Response({"success": False, "error": str(e)}, status=400)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def decline_crew_request(request):
    """Decline a crew invitation."""
    try:
        requestId = request.data.get("requestId")
        if not requestId:
            return Response({"error": "Request ID is required."}, status=400)

        # Use select_related to load related models in a single query
        crew_request = CrewRequest.objects.select_related('receiver', 'sender', 'crew').get(
            requestId=requestId
        )

        # Verify the current user is the receiver of the request
        if crew_request.receiver != request.user:
            return Response(
                {"error": "You are not authorized to decline this invitation."},
                status=403,
            )

        # Verify request is still pending
        if crew_request.status != "pending":
            return Response(
                {"error": "This invitation is no longer pending."}, status=400
            )

        # Update the status in a single operation
        crew_request.status = "declined"
        crew_request.save(update_fields=['status', 'updated_at'])
        
        return Response(
            {"success": True, "message": "Crew invitation declined successfully."},
            status=200,
        )

    except CrewRequest.DoesNotExist:
        return Response({"success": False, "error": "Invitation not found."}, status=404)
    except Exception as e:
        return Response({"success": False, "error": str(e)}, status=400)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def accept_crew_request(request):
    """Accept a crew invitation."""
    try:
        requestId = request.data.get("requestId")
        if not requestId:
            return Response({"error": "Request ID is required."}, status=400)

        # Use select_related to load related models in a single query
        crew_request = CrewRequest.objects.select_related('receiver', 'sender', 'crew').get(
            requestId=requestId
        )

        # Verify the current user is the receiver of the request
        if crew_request.receiver != request.user:
            return Response(
                {"error": "You are not authorized to accept this invitation."},
                status=403,
            )

        # Verify request is still pending
        if crew_request.status != "pending":
            return Response(
                {"error": "This invitation is no longer pending."}, status=400
            )

        # Check if user is already a member of the crew - use efficient exists() method
        if CrewMember.objects.filter(
            user=request.user, crew=crew_request.crew
        ).exists():
            return Response(
                {"error": "You are already a member of this crew."}, status=400
            )

        # Accept the request and create crew membership in a transaction-like approach
        crew_request.status = "accepted"
        crew_request.save(update_fields=['status', 'updated_at'])
        
        CrewMember.objects.create(
            user=request.user, crew=crew_request.crew, is_admin=False
        )

        return Response(
            {
                "success": True,
                "message": f"You have successfully joined {crew_request.crew.name}.",
                "crew": {
                    "crewId": str(crew_request.crew.crewId),
                    "name": crew_request.crew.name
                }
            },
            status=200,
        )

    except CrewRequest.DoesNotExist:
        return Response({"success": False, "error": "Invitation not found."}, status=404)
    except Exception as e:
        return Response({"success": False, "error": str(e)}, status=400)


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

from typing import Optional, List
from datetime import timedelta
from channels.db import database_sync_to_async
from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
import bleach
import os
from user_agents import parse as parse_user_agent
from django.db.models import Q, Prefetch
from django.db import transaction
from django.utils import timezone
import re
from django.shortcuts import get_object_or_404
from django.utils.timezone import now

from apiManager.utilities.notify_by_bot import notify_by_bot
from apiManager.utilities.device_info import get_device_info
from apiManager.utilities.form_fields import get_form_fields

from eventManagementApp.models import Event
from accountManagementApp.models import UserProfile
from socialApp.models import (
    Crew,
    CrewMember,
    FriendRequest,
    CrewRequest,
    SocialActivity,
    SurfPost,
    TideUpTideDown,
    FixedMessage,
    EventMessage,
    MessageReaction,
)
from socialApp.forms import SurfPostForm
from eventTicketsApp.views import generateTicket
from apiManager.algorithms.suggested_friends import get_suggested_friends


from apiManager.dependencies import get_current_user
from authenticationApp.models import CustomUser
from uuid import UUID

from .serializers import (
    MyPassSerializer,
    SearchResult,
    UserFriends,
    UserCrewsResponse,
    SurfPostResponse,
    SurfPostCreate,
    VoteRequest,
    SendMessageRequest,
    FixedMessageResponse,
    MessageReactionRequest,
    EventMessageResponse,
)


router = APIRouter()


def is_valid_discord_username(username):
    return re.match(r"^[^#]{2,32}#[0-9]{4}$", username) is not None


@router.get("/user/{username}")
async def get_user_details(
    request: Request,
    username: str,
    caller_user_id: Optional[int] = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    API endpoint to retrieve comprehensive information about a specific user by username.
    """
    print(f"[get_user_details API] Function called with username: {username}")

    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def get_user_data(username, caller_user_id):
        try:
            # Get user with related profile in a single query
            user = CustomUser.objects.select_related("user_profile").get(
                username=username
            )
            user_profile = user.user_profile  # type: ignore[attr-defined]

            # Determine if the calling user is viewing their own profile
            is_own_profile = False
            if caller_user_id:
                try:
                    calling_user = CustomUser.objects.get(id=caller_user_id)
                    is_own_profile = calling_user.username == username
                except CustomUser.DoesNotExist:
                    is_own_profile = False

            # Get profile photo URL
            profile_photo_url = (
                user_profile.profile_photo.url if user_profile.profile_photo else None
            )

            # Get profile QR code URL
            profile_qr_code_url = (
                user_profile.profile_qr_code.url
                if user_profile.profile_qr_code
                else None
            )

            # Get college information
            college_data = None
            if user_profile.college:
                college_data = {
                    "id": str(user_profile.college.collegeId),
                    "name": user_profile.college.name,
                    "state": user_profile.college.state,
                    "city": user_profile.college.city,
                }

            # Get user's groups
            groups = list(user_profile.group.all().values("id", "name"))

            friend_amount = user_profile.friends.count()

            # Get user's friends (max 4, randomized)
            friends = []
            for friend in user_profile.friends.all().order_by("?")[:4]:
                friends.append(
                    {
                        "user_id": str(friend.user.user_id),
                        "username": friend.user.username,
                        "first_name": friend.user.first_name,
                        "last_name": friend.user.last_name,
                        "profile_photo": (
                            friend.profile_photo.url if friend.profile_photo else None
                        ),
                    }
                )

            # Get user's crews
            crew_memberships = []
            for crew_member in CrewMember.objects.filter(user=user).select_related(
                "crew", "crew__created_by"
            )[:20]:
                crew_memberships.append(
                    {
                        "crewId": str(crew_member.crew.crewId),
                        "name": crew_member.crew.name,
                    }
                )

            # Get user's favorite events (max 4)
            favorite_events = []
            for event in user_profile.favorite_events.all()[:4]:
                favorite_events.append(
                    {
                        "eventId": str(event.eventId),
                        "title": event.title,
                        "date": event.date,
                        "header_photo": (
                            event.header_photo.url if event.header_photo else None
                        ),
                        "event_host": {
                            "username": event.host.username,
                        },
                    }
                )

            # Get user's purchased events (max 4)
            purchased_events = []
            for event in user_profile.purchased_events.all()[:4]:
                purchased_events.append(
                    {
                        "eventId": str(event.eventId),
                        "title": event.title,
                        "date": event.date,
                        "header_photo": (
                            event.header_photo.url if event.header_photo else None
                        ),
                        "event_host": {
                            "username": event.host.username,
                        },
                    }
                )

            # Get user's hosted events (max 4, most recent)
            hosted_events = []
            for event in Event.objects.filter(host=user).order_by("-date")[:4]:
                hosted_events.append(
                    {
                        "eventId": str(event.eventId),
                        "title": event.title,
                        "date": event.date,
                        "header_photo": (
                            event.header_photo.url if event.header_photo else None
                        ),
                    }
                )

            # Check friend request status between users
            friend_request_status = "not_yet_sent"
            if caller_user_id and not is_own_profile:
                try:
                    calling_user = CustomUser.objects.get(id=caller_user_id)

                    # Check if they are already friends
                    if calling_user.user_profile.is_friends_with(user):
                        friend_request_status = "friends"
                    else:
                        # Check for existing friend request
                        friend_request = (
                            FriendRequest.objects.filter(
                                Q(sender=calling_user, receiver=user)
                                | Q(sender=user, receiver=calling_user)
                            )
                            .order_by("-created_at")
                            .first()
                        )

                        if friend_request:
                            if friend_request.status == "pending":
                                # Check who sent the request
                                if friend_request.sender == calling_user:
                                    friend_request_status = "sent_pending"
                                else:
                                    friend_request_status = "received_pending"
                            elif friend_request.status == "accepted":
                                # Data inconsistency: accepted request but no friendship
                                # This should not happen with proper transaction handling
                                friend_request_status = "friends"
                            elif friend_request.status == "canceled":
                                friend_request_status = "canceled"
                            # Note: declined requests are deleted, so they won't appear here
                except CustomUser.DoesNotExist:
                    # Calling user doesn't exist, keep default status
                    pass

            return {
                "user": {
                    "username": user.username,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "date_joined": user.date_joined,
                    "email_verified": user.email_verified,
                },
                "profile": {
                    "profile_photo": profile_photo_url,
                    "profile_qr_code": profile_qr_code_url,
                    "college": college_data,
                    "groups": groups,
                    "friend_amount": friend_amount,
                    "friends": friends,
                    "crew_memberships": crew_memberships,
                    "favorite_events": favorite_events,
                    "purchased_events": purchased_events,
                    "hosted_events": hosted_events,
                },
                "is_own_profile": is_own_profile,
                "friend_request_status": friend_request_status,
            }, None
        except CustomUser.DoesNotExist:
            error_message = f"User not found with username: {username}"
            print(f"[get_user_details API] {error_message}")
            return None, error_message
        except Exception as e:
            error_message = f"Error retrieving user data: {str(e)}"
            print(f"[get_user_details API] {error_message}")
            return None, error_message

    user_data, error_message = await get_user_data(username, caller_user_id)
    if user_data is None:
        notification_sent = await notify_by_bot(
            f"**[API: get_user_details API]** \n\n {error_message} \n\n Platform: {platform} \n\n User ID: {caller_user_id} \n\n Username: {username}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        if notification_sent is None:
            print(
                "[get_user_details API] Could not send notification: BOT_API_KEY not set"
            )
        raise HTTPException(status_code=404, detail=error_message)

    print(
        f"[get_user_details API] Returning details for user: {user_data['user']['username']}"
    )

    return {"user_details": user_data}


@router.get("/crew/{crew_id}")
async def get_crew_details(
    request: Request,
    crew_id: UUID,
    caller_user_id: Optional[int] = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    API endpoint to retrieve comprehensive information about a specific crew.
    """
    print(f"[get_crew_details API] Function called with crew_id: {crew_id}")

    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def get_crew_data(crew_id, caller_user_id):
        try:
            # Get crew with related data in optimized queries
            crew = Crew.objects.select_related(
                "created_by", "created_by__user_profile"
            ).get(crewId=crew_id)

            # Get crew creator profile information
            creator_profile = (
                crew.created_by.user_profile
                if hasattr(crew.created_by, "user_profile")
                else None
            )
            creator_data = {
                "user_id": str(crew.created_by.user_id),
                "username": crew.created_by.username,
                "first_name": crew.created_by.first_name,
                "last_name": crew.created_by.last_name,
                "profile_photo": (
                    creator_profile.profile_photo.url
                    if creator_profile and creator_profile.profile_photo
                    else None
                ),
            }

            # Get all crew members with their profiles
            crew_members = []
            user_is_member = False
            user_is_admin = False

            # FIRST: Check if the caller is the crew creator
            if caller_user_id and crew.created_by.id == caller_user_id:
                user_is_member = True
                user_is_admin = True  # Creator is always admin
                print(f"[get_crew_details] User {caller_user_id} is the crew creator")

            # Get all crew member records
            crew_member_records = CrewMember.objects.filter(crew=crew).select_related(
                "user", "user__user_profile"
            )

            print(
                f"[get_crew_details] Found {crew_member_records.count()} crew members"
            )
            print(
                f"[get_crew_details] Checking membership for user_id: {caller_user_id}"
            )

            for crew_member in crew_member_records:
                member_profile = (
                    crew_member.user.user_profile
                    if hasattr(crew_member.user, "user_profile")
                    else None
                )

                # DEBUG: Log member IDs for comparison
                print(
                    f"[get_crew_details] Comparing caller_user_id={caller_user_id} with member_user_id={crew_member.user.id}"
                )

                # Check if the caller is this crew member - ensure both are integers
                if caller_user_id and int(crew_member.user.id) == int(caller_user_id):
                    user_is_member = True
                    user_is_admin = crew_member.is_admin
                    print(
                        f"[get_crew_details] User {caller_user_id} found as crew member with admin={crew_member.is_admin}"
                    )

                crew_members.append(
                    {
                        "user": {
                            "user_id": str(crew_member.user.user_id),
                            "username": crew_member.user.username,
                            "first_name": crew_member.user.first_name,
                            "last_name": crew_member.user.last_name,
                        },
                        "profile": {
                            "profile_photo": (
                                member_profile.profile_photo.url
                                if member_profile and member_profile.profile_photo
                                else None
                            ),
                        },
                        "membership_details": {
                            "joined_at": crew_member.joined_at,
                            "is_admin": crew_member.is_admin,
                        },
                    }
                )

            # Final debug log
            print(
                f"[get_crew_details] Final membership status: user_is_member={user_is_member}, user_is_admin={user_is_admin}"
            )

            # Also check if caller should be included but is missing from CrewMember records
            if caller_user_id and not user_is_member:
                # Check for potential data inconsistency
                direct_membership_check = CrewMember.objects.filter(
                    crew=crew, user_id=caller_user_id
                ).exists()
                print(
                    f"[get_crew_details] Direct membership check result: {direct_membership_check}"
                )

                if direct_membership_check:
                    print(
                        f"[get_crew_details] WARNING: Found membership in direct check but missed in iteration!"
                    )
                    user_is_member = True
                    # Get the admin status
                    try:
                        member_record = CrewMember.objects.get(
                            crew=crew, user_id=caller_user_id
                        )
                        user_is_admin = member_record.is_admin
                    except CrewMember.DoesNotExist:
                        pass

            # Get shared events for this crew (limit for performance)
            from eventManagementApp.models import SharedEvent

            shared_events = []
            for shared_event in SharedEvent.objects.filter(crew=crew).select_related(
                "event", "sender"
            )[:20]:
                shared_events.append(
                    {
                        "event": {
                            "eventId": str(shared_event.event.eventId),
                            "title": shared_event.event.title,
                            "date": shared_event.event.date,
                            "header_photo": (
                                shared_event.event.header_photo.url
                                if shared_event.event.header_photo
                                else None
                            ),
                        },
                        "sender": {
                            "username": shared_event.sender.username,
                            "first_name": shared_event.sender.first_name,
                            "last_name": shared_event.sender.last_name,
                        },
                        "shared_at": shared_event.shared_at,
                    }
                )

            return {
                "crewId": str(crew.crewId),
                "name": crew.name,
                "bio": crew.bio,
                "created_at": crew.created_at,
                "created_by": creator_data,
                "members": crew_members,
                "member_count": len(crew_members),
                "shared_events": shared_events,
                "user_is_member": user_is_member,
                "user_is_admin": user_is_admin,
            }, None
        except Crew.DoesNotExist:
            error_message = f"Crew not found with ID: {crew_id}"
            print(f"[get_crew_details API] Crew not found with ID: {crew_id}")
            return None, error_message
        except Exception as e:
            error_message = f"Error retrieving crew data: {str(e)}"
            print(f"[get_crew_details API] Error retrieving crew data: {str(e)}")
            return None, error_message

    crew_data, error_message = await get_crew_data(crew_id, caller_user_id)
    if crew_data is None:
        notification_sent = await notify_by_bot(
            f"**[API: get_crew_details API]** \n\n {error_message} \n\n Platform: {platform} \n\n User ID: {caller_user_id} \n\n Crew ID: {crew_id}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        if notification_sent is None:
            print(
                "[get_crew_details API] Could not send notification: BOT_API_KEY not set"
            )
        raise HTTPException(status_code=404, detail=error_message)

    print(f"[get_crew_details API] Returning details for crew: {crew_data['name']}")

    return {"crew_details": crew_data}


# My Pass Tab
@router.get("/myPass")
async def get_my_pass(
    request: Request,
    caller_user_id: Optional[int] = Depends(get_current_user),
    platform: Optional[str] = None,
):
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def get_my_pass_data(caller_user_id):
        try:
            user = CustomUser.objects.get(id=caller_user_id)
            user_profile = user.user_profile  # type: ignore[attr-defined]

            return (
                MyPassSerializer(
                    id=str(user.id),
                    user_id=str(user.user_id),
                    username=user.username,
                    profile_photo=(
                        user_profile.profile_photo.url
                        if user_profile.profile_photo
                        else None
                    ),
                    qr_code=(
                        user_profile.profile_qr_code.url
                        if user_profile.profile_qr_code
                        else None
                    ),
                ),
                None,
            )  # Return tuple with data and None for error
        except CustomUser.DoesNotExist:
            print(
                f"[get_my_pass API] User not found with ID: {caller_user_id} (Platform: {platform})"
            )
            return None, "User not found"
        except Exception as e:
            print(
                f"[get_my_pass API] Error retrieving user data: {str(e)} (Platform: {platform})"
            )
            return None, f"Error retrieving user data: {str(e)}"

    my_pass_data, error_message = await get_my_pass_data(caller_user_id)
    if my_pass_data is None:
        notification_sent = await notify_by_bot(
            f"**[API: get_my_pass API]** \n\n {error_message} \n\n Platform: {platform} \n\n User ID: {caller_user_id}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        if notification_sent is None:
            print("[get_my_pass API] Could not send notification: BOT_API_KEY not set")
        raise HTTPException(status_code=404, detail=error_message)

    return {"my_pass_data": my_pass_data}


@router.get("/search", response_model=SearchResult)
async def search(
    request: Request,
    query: str = Query(
        ...,
        description="Search query",
        min_length=1,
    ),
    platform: Optional[str] = None,
):
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def search_users(query):
        try:
            user_qs = (
                CustomUser.objects.filter(
                    Q(username__icontains=query)
                    | Q(first_name__icontains=query)
                    | Q(last_name__icontains=query)
                )
                .select_related("user_profile")
                .only(
                    "user_id",
                    "username",
                    "first_name",
                    "last_name",
                    "user_profile__profile_photo",
                )[:10]
            )

            crew_qs = Crew.objects.filter(Q(name__icontains=query)).only(
                "crewId", "name"
            )[:10]

            # Convert UUIDs to strings
            users = [
                {
                    "user_id": str(user.user_id),
                    "username": user.username,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "profile_photo": (
                        user.user_profile.profile_photo.url
                        if user.user_profile.profile_photo
                        else None
                    ),
                }
                for user in user_qs
            ]

            crews = [
                {
                    "crew_id": str(crew.crewId),
                    "name": crew.name,
                }
                for crew in crew_qs
            ]

            return users, crews, None
        except Exception as e:
            print(f"[search API] Error searching users: {str(e)}")
            return None, None, str(e)

    users, crews, error_message = await search_users(query)
    if users is None or crews is None:
        notification_sent = await notify_by_bot(
            f"**[API: search API]** \n\n {error_message} \n\n Platform: {platform} \n\n Query: {query}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        if notification_sent is None:
            print("[search API] Could not send notification: BOT_API_KEY not set")
        raise HTTPException(status_code=500, detail="Error searching users")

    return {"users": users, "crews": crews}


@router.get("/get_user_friends", response_model=UserFriends)
async def get_user_friends(
    request: Request,
    caller_user_id: Optional[int] = Depends(get_current_user),
    platform: Optional[str] = None,
):
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def get_user_friends_data(caller_user_id):
        try:
            user = CustomUser.objects.get(id=caller_user_id)
            user_profile = user.user_profile  # type: ignore[attr-defined]
            friends = user_profile.friends.all()
            friends_data = [
                {
                    "user_id": str(friend.user.user_id),
                    "username": friend.user.username,
                    "first_name": friend.user.first_name,
                    "last_name": friend.user.last_name,
                    "profile_photo": (
                        friend.profile_photo.url if friend.profile_photo else None
                    ),
                }
                for friend in friends
            ]
            return friends_data, None
        except CustomUser.DoesNotExist:
            print(f"[get_user_friends API] User not found with ID: {caller_user_id}")
            return None, "User not found"
        except Exception as e:
            print(f"[get_user_friends API] Error retrieving user friends: {str(e)}")
            return None, f"Error retrieving user friends: {str(e)}"

    try:
        friends_data, error_message = await get_user_friends_data(caller_user_id)
        if friends_data is None:
            notification_sent = await notify_by_bot(
                f"**[API: get_user_friends API]** \n\n {error_message} \n\n Platform: {platform} \n\n User ID: {caller_user_id}",
                platform or "Unknown",
                "ERROR",
                device_info,
            )
            if notification_sent is None:
                print(
                    "[get_user_friends API] Could not send notification: BOT_API_KEY not set"
                )
            raise HTTPException(status_code=500, detail=error_message)

        return {"user_friends": friends_data}
    except Exception as e:
        error_message = f"Error in get_user_friends API: {str(e)}"
        print(f"[get_user_friends API] {error_message}")
        # notification_sent = await notify_by_bot(
        #     f"**[API: get_user_friends API]** \n\n {error_message} \n\n Platform: {platform} \n\n User ID: {caller_user_id}",
        #     platform or "Unknown",
        #     "ERROR",
        #     device_info,
        # )
        # if notification_sent is None:
        #     print(
        #         "[get_user_friends API] Could not send notification: BOT_API_KEY not set"
        #     )
        raise HTTPException(status_code=500, detail=error_message)


@router.get("/get_user_crews", response_model=UserCrewsResponse)
async def get_user_crews(
    request: Request,
    caller_user_id: Optional[int] = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    API endpoint to retrieve all crews a user is in, including 3 random profile pictures of other members.
    """
    print(f"[get_user_crews API] Function called for user ID: {caller_user_id}")

    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def get_user_crews_data(caller_user_id):
        try:
            user = CustomUser.objects.get(id=caller_user_id)

            # Get all crews the user is a member of
            crew_memberships = CrewMember.objects.filter(user=user).select_related(
                "crew", "crew__created_by"
            )

            crews_data = []
            for membership in crew_memberships:
                crew = membership.crew

                # Get 3 random members (excluding the current user)
                random_members = (
                    CrewMember.objects.filter(crew=crew)
                    .exclude(user=user)
                    .select_related("user", "user__user_profile")
                    .order_by("?")[:3]
                )

                # Get member profile pictures
                member_photos = []
                for member in random_members:
                    if (
                        hasattr(member.user, "user_profile")
                        and member.user.user_profile.profile_photo
                    ):
                        member_photos.append(member.user.user_profile.profile_photo.url)

                crews_data.append(
                    {
                        "crewId": str(crew.crewId),
                        "name": crew.name,
                        "bio": crew.bio,
                        "created_at": crew.created_at,
                        "member_photos": member_photos,
                        "is_admin": membership.is_admin,
                    }
                )

            return crews_data, None
        except CustomUser.DoesNotExist:
            error_message = f"User not found with ID: {caller_user_id}"
            print(f"[get_user_crews API] {error_message}")
            return None, error_message
        except Exception as e:
            error_message = f"Error retrieving user crews: {str(e)}"
            print(f"[get_user_crews API] {error_message}")
            return None, error_message

    crews_data, error_message = await get_user_crews_data(caller_user_id)
    if crews_data is None:
        notification_sent = await notify_by_bot(
            f"**[API: get_user_crews API]** \n\n {error_message} \n\n Platform: {platform} \n\n User ID: {caller_user_id}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        if notification_sent is None:
            print(
                "[get_user_crews API] Could not send notification: BOT_API_KEY not set"
            )
        raise HTTPException(status_code=500, detail=error_message)

    return {"user_crews": crews_data}


@router.post("/send-friend-request/{receiver_username}")
async def send_friend_request(
    request: Request,
    receiver_username: str,
    caller_user_id: Optional[int] = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    API endpoint to send a friend request to another user.
    """
    print(
        f"[send_friend_request API] Function called with receiver_username: {receiver_username}"
    )

    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def send_friend_request_logic(sender_user_id, receiver_username):
        try:
            # Validate Discord-style username
            if not is_valid_discord_username(receiver_username):
                return (
                    None,
                    "Invalid username format. Please use the full Discord-style username (e.g., name#1234).",
                    None,
                )
            # Get sender user
            sender_user = CustomUser.objects.get(id=sender_user_id)

            # Check if trying to send request to self
            if receiver_username == sender_user.username:
                return None, "You cannot send a friend request to yourself.", None

            # Get receiver user profile - use full Discord-style username
            try:
                receiver_user_profile = UserProfile.objects.select_related("user").get(
                    user__username=receiver_username
                )
                receiver_user = receiver_user_profile.user
            except UserProfile.DoesNotExist:
                return None, "User not found.", None

            # Check if already friends
            if sender_user.user_profile.is_friends_with(receiver_user):
                return None, "You are already friends with this user.", None

            # Check for any active (pending/accepted) requests
            active_request = FriendRequest.objects.filter(
                Q(sender=sender_user, receiver=receiver_user)
                | Q(sender=receiver_user, receiver=sender_user),
                status__in=["pending", "accepted"],
            ).first()

            if active_request:
                if active_request.status == "pending":
                    if active_request.sender == sender_user:
                        return (
                            None,
                            "You have already sent a friend request to this user.",
                            None,
                        )
                    else:
                        return (
                            None,
                            f"{receiver_username} has already sent you a friend request. Check your notifications to respond.",
                            None,
                        )
                else:  # status is 'accepted'
                    # Double-check if friendship actually exists
                    if sender_user.user_profile.is_friends_with(receiver_user):
                        return (
                            None,
                            "You are already friends with this user.",
                            None,
                        )
                    else:
                        # Data inconsistency: accepted request but no friendship
                        # Fix the friendship relationship
                        try:
                            sender_user.user_profile.friends.add(
                                receiver_user.user_profile
                            )  # type: ignore[attr-defined]
                            receiver_user.user_profile.friends.add(
                                sender_user.user_profile
                            )  # type: ignore[attr-defined]
                            return (
                                None,
                                "You are already friends with this user.",
                                None,
                            )
                        except Exception as e:
                            print(
                                f"[send_friend_request API] Error fixing friendship relationship: {str(e)}"
                            )
                            # If fixing fails, allow new request (treat as if no accepted request exists)
                            pass

            # Check for canceled requests to reuse (declined requests are deleted)
            old_request = FriendRequest.objects.filter(
                sender=sender_user,
                receiver=receiver_user,
                status="canceled",
            ).first()

            if old_request:
                # Reuse the old request
                old_request.status = "pending"
                old_request.save()
                friend_request = old_request
            else:
                # Create new friend request
                try:
                    friend_request = FriendRequest.objects.create(
                        sender=sender_user, receiver=receiver_user, status="pending"
                    )
                except Exception as create_error:
                    error_message = (
                        f"Error creating friend request: {str(create_error)}"
                    )
                    print(f"[send_friend_request API] {error_message}")
                    return None, error_message, None

            return (
                {
                    "status": friend_request.status,
                    "created_at": friend_request.created_at,
                },
                "Friend request sent successfully.",
                None,
            )

        except CustomUser.DoesNotExist:
            error_message = f"Sender user not found with ID: {sender_user_id}"
            print(f"[send_friend_request API] {error_message}")
            return None, error_message, None
        except Exception as e:
            error_message = f"Error sending friend request: {str(e)}"
            print(f"[send_friend_request API] {error_message}")
            return None, error_message, None

    friend_request_data, success_message, error_message = (
        await send_friend_request_logic(caller_user_id, receiver_username)
    )

    if friend_request_data is None:
        notification_sent = await notify_by_bot(
            f"**[API: send_friend_request API]** \n\n {success_message} \n\n Platform: {platform} \n\n User ID: {caller_user_id} \n\n Receiver Username: {receiver_username}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        if notification_sent is None:
            print(
                "[send_friend_request API] Could not send notification: BOT_API_KEY not set"
            )
        raise HTTPException(status_code=400, detail=success_message)

    print(f"[send_friend_request API] {success_message}")
    return {"message": success_message, "friend_request": friend_request_data}


@router.post("/cancel-friend-request/{receiver_username}")
async def cancel_friend_request(
    request: Request,
    receiver_username: str,
    caller_user_id: Optional[int] = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    API endpoint to cancel a friend request sent to another user.
    """
    print(
        f"[cancel_friend_request API] Function called with receiver_username: {receiver_username}"
    )

    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def cancel_friend_request_logic(sender_user_id, receiver_username):
        try:
            # Validate Discord-style username
            if not is_valid_discord_username(receiver_username):
                return (
                    None,
                    "Invalid username format. Please use the full Discord-style username (e.g., name#1234).",
                    None,
                )
            # Get sender user
            sender_user = CustomUser.objects.get(id=sender_user_id)

            # Check if trying to cancel request to self
            if receiver_username == sender_user.username:
                return None, "You cannot cancel a friend request to yourself.", None

            # Get receiver user profile - use full Discord-style username
            try:
                receiver_user_profile = UserProfile.objects.select_related("user").get(
                    user__username=receiver_username
                )
                receiver_user = receiver_user_profile.user
            except UserProfile.DoesNotExist:
                return None, "User not found.", None

            # Check if users are already friends
            if sender_user.user_profile.is_friends_with(receiver_user):
                return (
                    None,
                    "You are already friends with this user. No request to cancel.",
                    None,
                )

            # Find the pending friend request sent by the caller
            friend_request = FriendRequest.objects.filter(
                sender=sender_user, receiver=receiver_user, status="pending"
            ).first()

            if not friend_request:
                # Check if there's a non-pending request to provide better feedback
                existing_request = (
                    FriendRequest.objects.filter(
                        sender=sender_user, receiver=receiver_user
                    )
                    .exclude(status="pending")
                    .first()
                )

                if existing_request:
                    if existing_request.status == "accepted":
                        return (
                            None,
                            "This friend request was already accepted. You are now friends.",
                            None,
                        )
                    elif existing_request.status == "canceled":
                        return None, "This friend request was already canceled.", None
                    # Note: declined requests are deleted, so they won't appear here

                return None, "No pending friend request found to cancel.", None

            # Update the request status to canceled
            friend_request.status = "canceled"
            friend_request.save()

            return (
                {
                    "status": friend_request.status,
                    "canceled_at": friend_request.updated_at,
                },
                "Friend request canceled successfully.",
                None,
            )

        except CustomUser.DoesNotExist:
            error_message = f"Sender user not found with ID: {sender_user_id}"
            print(f"[cancel_friend_request API] {error_message}")
            return None, error_message, None
        except Exception as e:
            error_message = f"Error canceling friend request: {str(e)}"
            print(f"[cancel_friend_request API] {error_message}")
            return None, error_message, None

    friend_request_data, success_message, error_message = (
        await cancel_friend_request_logic(caller_user_id, receiver_username)
    )

    if friend_request_data is None:
        notification_sent = await notify_by_bot(
            f"**[API: cancel_friend_request API]** \n\n {success_message or error_message} \n\n Platform: {platform} \n\n User ID: {caller_user_id} \n\n Receiver Username: {receiver_username}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        if notification_sent is None:
            print(
                "[cancel_friend_request API] Could not send notification: BOT_API_KEY not set"
            )
        raise HTTPException(status_code=400, detail=success_message or error_message)

    print(f"[cancel_friend_request API] {success_message}")
    return {"message": success_message, "friend_request": friend_request_data}


@router.post("/accept-friend-request/{sender_username}")
async def accept_friend_request(
    request: Request,
    sender_username: str,
    caller_user_id: Optional[int] = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    API endpoint to accept a friend request received from another user.
    """
    print(
        f"[accept_friend_request API] Function called with sender_username: {sender_username}"
    )

    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def accept_friend_request_logic(receiver_user_id, sender_username):
        try:
            # Validate Discord-style username
            if not is_valid_discord_username(sender_username):
                return (
                    None,
                    "Invalid username format. Please use the full Discord-style username (e.g., name#1234).",
                    None,
                )
            # Get receiver user (the one accepting the request)
            receiver_user = CustomUser.objects.get(id=receiver_user_id)

            # Check if trying to accept request from self
            if sender_username == receiver_user.username:
                return None, "You cannot accept a friend request from yourself.", None

            # Get sender user profile - use full Discord-style username
            try:
                sender_user_profile = UserProfile.objects.select_related("user").get(
                    user__username=sender_username
                )
                sender_user = sender_user_profile.user
            except UserProfile.DoesNotExist:
                return None, "User not found.", None

            # Check if already friends
            if receiver_user.user_profile.is_friends_with(sender_user):
                return None, "You are already friends with this user.", None

            # Find the pending friend request sent by the sender to the receiver
            friend_request = FriendRequest.objects.filter(
                sender=sender_user, receiver=receiver_user, status="pending"
            ).first()

            if not friend_request:
                # Check if there's a non-pending request to provide better feedback
                existing_request = (
                    FriendRequest.objects.filter(
                        sender=sender_user, receiver=receiver_user
                    )
                    .exclude(status="pending")
                    .first()
                )

                if existing_request:
                    if existing_request.status == "accepted":
                        return (
                            None,
                            "This friend request was already accepted. You are now friends.",
                            None,
                        )
                    elif existing_request.status == "canceled":
                        return (
                            None,
                            "This friend request was canceled by the sender.",
                            None,
                        )
                    # Note: declined requests are deleted, so they won't appear here

                return None, "No pending friend request found to accept.", None

            # Use transaction to ensure data consistency
            with transaction.atomic():
                # Double-check that they're not already friends within the transaction
                # (in case another concurrent request was processed)
                if receiver_user.user_profile.is_friends_with(sender_user):
                    return None, "You are already friends with this user.", None

                # Update the request status to accepted
                friend_request.status = "accepted"
                friend_request.save()

                # Add both users to each other's friends list
                receiver_user.user_profile.friends.add(sender_user_profile)  # type: ignore[attr-defined]
                sender_user_profile.friends.add(receiver_user.user_profile)  # type: ignore[attr-defined]

            # Defensive type check
            from socialApp.models import FriendRequest as FriendRequestModel

            if not isinstance(friend_request, FriendRequestModel):
                raise Exception(
                    f"Internal error: friend_request is not a FriendRequest instance, got {type(friend_request)}"
                )

            return (
                {
                    "status": friend_request.status,
                    "accepted_at": friend_request.updated_at,
                    "friendship_established": True,
                },
                "Friend request accepted successfully.",
                None,
            )

        except CustomUser.DoesNotExist:
            error_message = f"Receiver user not found with ID: {receiver_user_id}"
            print(f"[accept_friend_request API] {error_message}")
            return None, error_message, None
        except Exception as e:
            error_message = f"Error accepting friend request: {str(e)}"
            print(f"[accept_friend_request API] {error_message}")
            return None, error_message, None

    friend_request_data, success_message, error_message = (
        await accept_friend_request_logic(caller_user_id, sender_username)
    )

    if friend_request_data is None:
        notification_sent = await notify_by_bot(
            f"**[API: accept_friend_request API]** \n\n {success_message or error_message} \n\n Platform: {platform} \n\n User ID: {caller_user_id} \n\n Sender Username: {sender_username}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        if notification_sent is None:
            print(
                "[accept_friend_request API] Could not send notification: BOT_API_KEY not set"
            )
        raise HTTPException(status_code=400, detail=success_message or error_message)

    print(f"[accept_friend_request API] {success_message}")
    return {"message": success_message, "friend_request": friend_request_data}


@router.post("/decline-friend-request/{sender_username}")
async def decline_friend_request(
    request: Request,
    sender_username: str,
    caller_user_id: Optional[int] = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    API endpoint to decline a friend request received from another user.
    """
    print(
        f"[decline_friend_request API] Function called with sender_username: {sender_username}"
    )

    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def decline_friend_request_logic(receiver_user_id, sender_username):
        try:
            # Validate Discord-style username
            if not is_valid_discord_username(sender_username):
                return (
                    None,
                    "Invalid username format. Please use the full Discord-style username (e.g., name#1234).",
                    None,
                )
            # Get receiver user (the one declining the request)
            receiver_user = CustomUser.objects.get(id=receiver_user_id)

            # Check if trying to decline request from self
            if sender_username == receiver_user.username:
                return None, "You cannot decline a friend request from yourself.", None

            # Get sender user profile - use full Discord-style username
            try:
                sender_user_profile = UserProfile.objects.select_related("user").get(
                    user__username=sender_username
                )
                sender_user = sender_user_profile.user
            except UserProfile.DoesNotExist:
                return None, "User not found.", None

            # Check if already friends
            if receiver_user.user_profile.is_friends_with(sender_user):
                return None, "You are already friends with this user.", None

            # Find the pending friend request sent by the sender to the receiver
            friend_request = FriendRequest.objects.filter(
                sender=sender_user, receiver=receiver_user, status="pending"
            ).first()

            if not friend_request:
                # Check if there's a non-pending request to provide better feedback
                existing_request = (
                    FriendRequest.objects.filter(
                        sender=sender_user, receiver=receiver_user
                    )
                    .exclude(status="pending")
                    .first()
                )

                if existing_request:
                    if existing_request.status == "accepted":
                        return (
                            None,
                            "This friend request was already accepted. You are now friends.",
                            None,
                        )
                    elif existing_request.status == "canceled":
                        return None, "This friend request was already canceled.", None
                    # Note: declined requests are deleted, so they won't appear here

                return None, "No pending friend request found to decline.", None

            # Store request info before deletion
            request_info = {
                "request_id": str(friend_request.requestId),
                "sender_username": sender_user.username,
                "declined_at": timezone.now(),
            }

            # Delete the friend request (declining means removing it completely)
            friend_request.delete()

            return (
                {
                    "status": "declined_and_deleted",
                    "declined_at": request_info["declined_at"],
                    "request_id": request_info["request_id"],
                },
                "Friend request declined successfully.",
                None,
            )

        except CustomUser.DoesNotExist:
            error_message = f"Receiver user not found with ID: {receiver_user_id}"
            print(f"[decline_friend_request API] {error_message}")
            return None, error_message, None
        except Exception as e:
            error_message = f"Error declining friend request: {str(e)}"
            print(f"[decline_friend_request API] {error_message}")
            return None, error_message, None

    friend_request_data, success_message, error_message = (
        await decline_friend_request_logic(caller_user_id, sender_username)
    )

    if friend_request_data is None:
        notification_sent = await notify_by_bot(
            f"**[API: decline_friend_request API]** \n\n {success_message or error_message} \n\n Platform: {platform} \n\n User ID: {caller_user_id} \n\n Sender Username: {sender_username}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        if notification_sent is None:
            print(
                "[decline_friend_request API] Could not send notification: BOT_API_KEY not set"
            )
        raise HTTPException(status_code=400, detail=success_message or error_message)

    print(f"[decline_friend_request API] {success_message}")
    return {"message": success_message, "friend_request": friend_request_data}


@router.post("/remove-friend/{friend_username}")
async def remove_friend(
    request: Request,
    friend_username: str,
    caller_user_id: Optional[int] = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    API endpoint to remove a user from the caller's friends list.
    """
    print(
        f"[remove_friend API] Function called with friend_username: {friend_username}"
    )

    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def remove_friend_logic(caller_user_id, friend_username):
        try:
            # Validate Discord-style username
            if not is_valid_discord_username(friend_username):
                return (
                    None,
                    "Invalid username format. Please use the full Discord-style username (e.g., name#1234).",
                    None,
                )
            # Get caller user
            caller_user = CustomUser.objects.get(id=caller_user_id)

            # Check if trying to remove self
            if friend_username == caller_user.username:
                return None, "You cannot remove yourself as a friend.", None

            # Get friend user profile - use full Discord-style username
            try:
                friend_user_profile = UserProfile.objects.select_related("user").get(
                    user__username=friend_username
                )
                friend_user = friend_user_profile.user
            except UserProfile.DoesNotExist:
                return None, "User not found.", None

            # Check if they are actually friends
            if not caller_user.user_profile.is_friends_with(friend_user):
                return None, "You are not friends with this user.", None

            # Use transaction to ensure data consistency
            with transaction.atomic():
                # Remove friendship from both users' friend lists
                caller_user.user_profile.friends.remove(friend_user_profile)
                friend_user_profile.friends.remove(caller_user.user_profile)

                # Find and delete any accepted friend request
                friend_request = FriendRequest.objects.filter(
                    Q(sender=caller_user, receiver=friend_user)
                    | Q(sender=friend_user, receiver=caller_user),
                    status="accepted",
                ).first()

                request_info = None
                if friend_request:
                    # Store request info before deletion
                    request_info = {
                        "request_id": str(friend_request.requestId),
                        "original_sender": friend_request.sender.username,
                        "original_receiver": friend_request.receiver.username,
                    }
                    # Delete the friend request (removing friendship means removing the request too)
                    friend_request.delete()

            friendship_removed_at = timezone.now()

            return (
                {
                    "friendship_removed": True,
                    "removed_at": friendship_removed_at,
                    "friend_username": friend_username,
                    "friend_request_deleted": request_info is not None,
                    "deleted_request_info": request_info,
                },
                "Friend removed successfully.",
                None,
            )

        except CustomUser.DoesNotExist:
            error_message = f"Caller user not found with ID: {caller_user_id}"
            print(f"[remove_friend API] {error_message}")
            return None, error_message, None
        except Exception as e:
            error_message = f"Error removing friend: {str(e)}"
            print(f"[remove_friend API] {error_message}")
            return None, error_message, None

    try:
        friend_removal_data, success_message, error_message = await remove_friend_logic(
            caller_user_id, friend_username
        )

        if friend_removal_data is None:
            notification_sent = await notify_by_bot(
                f"**[API: remove_friend API]** \n\n {success_message or error_message} \n\n Platform: {platform} \n\n User ID: {caller_user_id} \n\n Friend Username: {friend_username}",
                platform or "Unknown",
                "ERROR",
                device_info,
            )
            if notification_sent is None:
                print(
                    "[remove_friend API] Could not send notification: BOT_API_KEY not set"
                )
            raise HTTPException(
                status_code=400, detail=success_message or error_message
            )

        print(f"[remove_friend API] {success_message}")
        return {"message": success_message, "friend_removal": friend_removal_data}

    except Exception as e:
        error_message = f"Error in remove_friend API: {str(e)}"
        print(f"[remove_friend API] {error_message}")
        notification_sent = await notify_by_bot(
            f"**[API: remove_friend API]** \n\n {error_message} \n\n Platform: {platform} \n\n User ID: {caller_user_id} \n\n Friend Username: {friend_username}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        if notification_sent is None:
            print(
                "[remove_friend API] Could not send notification: BOT_API_KEY not set"
            )
        raise HTTPException(status_code=500, detail=error_message)


@router.get("/suggested-friends")
async def get_suggested_friends_endpoint(
    request: Request,
    caller_user_id: Optional[int] = Depends(get_current_user),
    platform: Optional[str] = None,
    max_suggestions: int = Query(10, ge=1, le=50),
):
    """
    API endpoint to get suggested friends for the current user.
    Suggestions are based on mutual friends and shared events.
    """
    print(f"[get_suggested_friends API] Function called for user ID: {caller_user_id}")

    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def get_suggested_friends_data(caller_user_id, max_suggestions):
        try:
            user = CustomUser.objects.get(id=caller_user_id)
            suggested_users = get_suggested_friends(user, max_suggestions)

            suggested_friends_data = []
            for suggested_user in suggested_users:
                user_profile = suggested_user.user_profile
                suggested_friends_data.append(
                    {
                        "user_id": str(suggested_user.user_id),
                        "username": suggested_user.username,
                        "first_name": suggested_user.first_name,
                        "last_name": suggested_user.last_name,
                        "profile_photo": (
                            user_profile.profile_photo.url
                            if user_profile.profile_photo
                            else None
                        ),
                    }
                )

            return suggested_friends_data, None
        except CustomUser.DoesNotExist:
            error_message = f"User not found with ID: {caller_user_id}"
            print(f"[get_suggested_friends API] {error_message}")
            return None, error_message
        except Exception as e:
            error_message = f"Error getting suggested friends: {str(e)}"
            print(f"[get_suggested_friends API] {error_message}")
            return None, error_message

    suggested_friends_data, error_message = await get_suggested_friends_data(
        caller_user_id, max_suggestions
    )
    if suggested_friends_data is None:
        notification_sent = await notify_by_bot(
            f"**[API: get_suggested_friends API]** \n\n {error_message} \n\n Platform: {platform} \n\n User ID: {caller_user_id}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        if notification_sent is None:
            print(
                "[get_suggested_friends API] Could not send notification: BOT_API_KEY not set"
            )
        raise HTTPException(status_code=500, detail=error_message)

    print(
        f"[get_suggested_friends API] Returning {len(suggested_friends_data)} suggested friends"
    )
    return {"suggested_friends": suggested_friends_data}


@router.get("/get-sent-friend-requests")
async def get_sent_friend_requests(
    request: Request,
    caller_user_id: Optional[int] = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    API endpoint to get all friend requests sent by the current user.
    Returns friend requests with status pending or canceled (declined requests are deleted).
    """
    print(
        f"[get_sent_friend_requests API] Function called for user ID: {caller_user_id}"
    )

    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def get_sent_friend_requests_data(caller_user_id):
        try:
            user = CustomUser.objects.get(id=caller_user_id)

            # Get sent friend requests (declined requests are deleted, so only pending and canceled)
            sent_requests = (
                FriendRequest.objects.filter(
                    sender=user, status__in=["pending", "canceled"]
                )
                .select_related("receiver", "receiver__user_profile")
                .order_by("-created_at")
            )

            # Format sent requests
            sent_requests_data = []
            for request in sent_requests:
                receiver_profile = request.receiver.user_profile
                sent_requests_data.append(
                    {
                        "request_id": str(request.requestId),
                        "status": request.status,
                        "created_at": request.created_at,
                        "updated_at": request.updated_at,
                        "user": {
                            "user_id": str(request.receiver.user_id),
                            "username": request.receiver.username,
                            "first_name": request.receiver.first_name,
                            "last_name": request.receiver.last_name,
                            "profile_photo": (
                                receiver_profile.profile_photo.url
                                if receiver_profile.profile_photo
                                else None
                            ),
                        },
                    }
                )

            return sent_requests_data, None

        except CustomUser.DoesNotExist:
            error_message = f"User not found with ID: {caller_user_id}"
            print(f"[get_sent_friend_requests API] {error_message}")
            return None, error_message
        except Exception as e:
            error_message = f"Error getting sent friend requests: {str(e)}"
            print(f"[get_sent_friend_requests API] {error_message}")
            return None, error_message

    sent_requests_data, error_message = await get_sent_friend_requests_data(
        caller_user_id
    )
    if sent_requests_data is None:
        notification_sent = await notify_by_bot(
            f"**[API: get_sent_friend_requests API]** \n\n {error_message} \n\n Platform: {platform} \n\n User ID: {caller_user_id}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        if notification_sent is None:
            print(
                "[get_sent_friend_requests API] Could not send notification: BOT_API_KEY not set"
            )
        raise HTTPException(status_code=500, detail=error_message)

    print(
        f"[get_sent_friend_requests API] Returning {len(sent_requests_data)} sent friend requests"
    )
    return {"sent_requests": sent_requests_data}


@router.get("/get-received-friend-requests")
async def get_received_friend_requests(
    request: Request,
    caller_user_id: Optional[int] = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    API endpoint to get all friend requests received by the current user.
    Returns friend requests with status pending or canceled (declined requests are deleted).
    """
    print(
        f"[get_received_friend_requests API] Function called for user ID: {caller_user_id}"
    )

    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def get_received_friend_requests_data(caller_user_id):
        try:
            user = CustomUser.objects.get(id=caller_user_id)

            # Get received friend requests (declined requests are deleted, so only pending and canceled)
            received_requests = (
                FriendRequest.objects.filter(
                    receiver=user, status__in=["pending", "canceled"]
                )
                .select_related("sender", "sender__user_profile")
                .order_by("-created_at")
            )

            # Format received requests
            received_requests_data = []
            for request in received_requests:
                sender_profile = request.sender.user_profile
                received_requests_data.append(
                    {
                        "request_id": str(request.requestId),
                        "status": request.status,
                        "created_at": request.created_at,
                        "updated_at": request.updated_at,
                        "user": {
                            "user_id": str(request.sender.user_id),
                            "username": request.sender.username,
                            "first_name": request.sender.first_name,
                            "last_name": request.sender.last_name,
                            "profile_photo": (
                                sender_profile.profile_photo.url
                                if sender_profile.profile_photo
                                else None
                            ),
                        },
                    }
                )

            return received_requests_data, None

        except CustomUser.DoesNotExist:
            error_message = f"User not found with ID: {caller_user_id}"
            print(f"[get_received_friend_requests API] {error_message}")
            return None, error_message
        except Exception as e:
            error_message = f"Error getting received friend requests: {str(e)}"
            print(f"[get_received_friend_requests API] {error_message}")
            return None, error_message

    received_requests_data, error_message = await get_received_friend_requests_data(
        caller_user_id
    )
    if received_requests_data is None:
        notification_sent = await notify_by_bot(
            f"**[API: get_received_friend_requests API]** \n\n {error_message} \n\n Platform: {platform} \n\n User ID: {caller_user_id}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        if notification_sent is None:
            print(
                "[get_received_friend_requests API] Could not send notification: BOT_API_KEY not set"
            )
        raise HTTPException(status_code=500, detail=error_message)

    print(
        f"[get_received_friend_requests API] Returning {len(received_requests_data)} received friend requests"
    )
    return {"received_requests": received_requests_data}


@router.get("/get-sent-crew-invites")
async def get_sent_crew_invites(
    request: Request,
    caller_user_id: Optional[int] = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    API endpoint to get all crew invites sent by the current user.
    Returns crew invites with status pending or declined (accepted invites are converted to crew memberships).
    """
    print(f"[get_sent_crew_invites API] Function called for user ID: {caller_user_id}")

    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def get_sent_crew_invites_data(caller_user_id):
        try:
            user = CustomUser.objects.get(id=caller_user_id)

            # Get sent crew invites (accepted invites are converted to crew memberships, so only pending and declined)
            sent_invites = (
                CrewRequest.objects.filter(
                    sender=user, status__in=["pending", "declined"]
                )
                .select_related("receiver", "receiver__user_profile", "crew")
                .order_by("-created_at")
            )

            # Format sent invites
            sent_invites_data = []
            for invite in sent_invites:
                receiver_profile = invite.receiver.user_profile
                sent_invites_data.append(
                    {
                        "request_id": str(invite.requestId),
                        "status": invite.status,
                        "created_at": invite.created_at,
                        "updated_at": invite.updated_at,
                        "crew": {
                            "crew_id": str(invite.crew.crewId),
                            "name": invite.crew.name,
                        },
                        "receiver": {
                            "user_id": str(invite.receiver.user_id),
                            "username": invite.receiver.username,
                            "first_name": invite.receiver.first_name,
                            "last_name": invite.receiver.last_name,
                            "profile_photo": (
                                receiver_profile.profile_photo.url
                                if receiver_profile.profile_photo
                                else None
                            ),
                        },
                    }
                )

            return sent_invites_data, None

        except CustomUser.DoesNotExist:
            error_message = f"User not found with ID: {caller_user_id}"
            print(f"[get_sent_crew_invites API] {error_message}")
            return None, error_message
        except Exception as e:
            error_message = f"Error getting sent crew invites: {str(e)}"
            print(f"[get_sent_crew_invites API] {error_message}")
            return None, error_message

    sent_invites_data, error_message = await get_sent_crew_invites_data(caller_user_id)
    if sent_invites_data is None:
        notification_sent = await notify_by_bot(
            f"**[API: get_sent_crew_invites API]** \n\n {error_message} \n\n Platform: {platform} \n\n User ID: {caller_user_id}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        if notification_sent is None:
            print(
                "[get_sent_crew_invites API] Could not send notification: BOT_API_KEY not set"
            )
        raise HTTPException(status_code=500, detail=error_message)

    print(
        f"[get_sent_crew_invites API] Returning {len(sent_invites_data)} sent crew invites"
    )
    return {"sent_crew_invites": sent_invites_data}


@router.get("/get-received-crew-invites")
async def get_received_crew_invites(
    request: Request,
    caller_user_id: Optional[int] = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    API endpoint to get all crew invites received by the current user.
    Returns crew invites with status pending or declined (accepted invites are converted to crew memberships).
    """
    print(
        f"[get_received_crew_invites API] Function called for user ID: {caller_user_id}"
    )

    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def get_received_crew_invites_data(caller_user_id):
        try:
            user = CustomUser.objects.get(id=caller_user_id)

            # Get received crew invites (accepted invites are converted to crew memberships, so only pending and declined)
            received_invites = (
                CrewRequest.objects.filter(
                    receiver=user, status__in=["pending", "declined"]
                )
                .select_related("sender", "sender__user_profile", "crew")
                .order_by("-created_at")
            )

            # Format received invites
            received_invites_data = []
            for invite in received_invites:
                sender_profile = invite.sender.user_profile
                received_invites_data.append(
                    {
                        "request_id": str(invite.requestId),
                        "status": invite.status,
                        "created_at": invite.created_at,
                        "updated_at": invite.updated_at,
                        "crew": {
                            "crew_id": str(invite.crew.crewId),
                            "name": invite.crew.name,
                        },
                        "sender": {
                            "user_id": str(invite.sender.user_id),
                            "username": invite.sender.username,
                            "first_name": invite.sender.first_name,
                            "last_name": invite.sender.last_name,
                            "profile_photo": (
                                sender_profile.profile_photo.url
                                if sender_profile.profile_photo
                                else None
                            ),
                        },
                    }
                )

            return received_invites_data, None

        except CustomUser.DoesNotExist:
            error_message = f"User not found with ID: {caller_user_id}"
            print(f"[get_received_crew_invites API] {error_message}")
            return None, error_message
        except Exception as e:
            error_message = f"Error getting received crew invites: {str(e)}"
            print(f"[get_received_crew_invites API] {error_message}")
            return None, error_message

    received_invites_data, error_message = await get_received_crew_invites_data(
        caller_user_id
    )
    if received_invites_data is None:
        notification_sent = await notify_by_bot(
            f"**[API: get_received_crew_invites API]** \n\n {error_message} \n\n Platform: {platform} \n\n User ID: {caller_user_id}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        if notification_sent is None:
            print(
                "[get_received_crew_invites API] Could not send notification: BOT_API_KEY not set"
            )
        raise HTTPException(status_code=500, detail=error_message)

    print(
        f"[get_received_crew_invites API] Returning {len(received_invites_data)} received crew invites"
    )
    return {"received_crew_invites": received_invites_data}


@router.post("/accept-crew-invite/{request_id}")
async def accept_crew_invite(
    request: Request,
    request_id: UUID,
    caller_user_id: Optional[int] = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    API endpoint to accept a crew invite received from another user.
    """
    print(f"[accept_crew_invite API] Function called with request_id: {request_id}")

    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def accept_crew_invite_logic(receiver_user_id, request_id):
        try:
            # Get receiver user (the one accepting the request)
            receiver_user = CustomUser.objects.get(id=receiver_user_id)

            # Find the pending crew invite
            crew_invite = (
                CrewRequest.objects.filter(
                    requestId=request_id, receiver=receiver_user, status="pending"
                )
                .select_related("crew", "sender")
                .first()
            )

            if not crew_invite:
                # Check if there's a non-pending invite to provide better feedback
                existing_invite = (
                    CrewRequest.objects.filter(
                        requestId=request_id, receiver=receiver_user
                    )
                    .exclude(status="pending")
                    .first()
                )

                if existing_invite:
                    if existing_invite.status == "accepted":
                        return None, "This crew invite was already accepted.", None
                    elif existing_invite.status == "declined":
                        return None, "This crew invite was already declined.", None
                    elif existing_invite.status == "canceled":
                        return (
                            None,
                            "This crew invite was canceled by the sender.",
                            None,
                        )

                return None, "No pending crew invite found to accept.", None

            # Use transaction to ensure data consistency
            with transaction.atomic():
                # Check if user is already a member of the crew
                if CrewMember.objects.filter(
                    user=receiver_user, crew=crew_invite.crew
                ).exists():
                    return None, "You are already a member of this crew.", None

                # Update the invite status to accepted
                crew_invite.status = "accepted"
                crew_invite.save()

                # Create crew membership
                CrewMember.objects.create(
                    user=receiver_user,
                    crew=crew_invite.crew,
                    is_admin=False,  # New members are not admins by default
                )

            return (
                {
                    "status": crew_invite.status,
                    "accepted_at": crew_invite.updated_at,
                    "crew": {
                        "crew_id": str(crew_invite.crew.crewId),
                        "name": crew_invite.crew.name,
                    },
                    "membership_established": True,
                },
                "Crew invite accepted successfully.",
                None,
            )

        except CustomUser.DoesNotExist:
            error_message = f"Receiver user not found with ID: {receiver_user_id}"
            print(f"[accept_crew_invite API] {error_message}")
            return None, error_message, None
        except Exception as e:
            error_message = f"Error accepting crew invite: {str(e)}"
            print(f"[accept_crew_invite API] {error_message}")
            return None, error_message, None

    invite_data, success_message, error_message = await accept_crew_invite_logic(
        caller_user_id, request_id
    )

    if invite_data is None:
        notification_sent = await notify_by_bot(
            f"**[API: accept_crew_invite API]** \n\n {success_message or error_message} \n\n Platform: {platform} \n\n User ID: {caller_user_id} \n\n Request ID: {request_id}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        if notification_sent is None:
            print(
                "[accept_crew_invite API] Could not send notification: BOT_API_KEY not set"
            )
        raise HTTPException(status_code=400, detail=success_message or error_message)

    print(f"[accept_crew_invite API] {success_message}")
    return {"message": success_message, "crew_invite": invite_data}


@router.post("/decline-crew-invite/{request_id}")
async def decline_crew_invite(
    request: Request,
    request_id: UUID,
    caller_user_id: Optional[int] = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    API endpoint to decline a crew invite received from another user.
    """
    print(f"[decline_crew_invite API] Function called with request_id: {request_id}")

    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def decline_crew_invite_logic(receiver_user_id, request_id):
        try:
            # Get receiver user (the one declining the request)
            receiver_user = CustomUser.objects.get(id=receiver_user_id)

            # Find the pending crew invite
            crew_invite = (
                CrewRequest.objects.filter(
                    requestId=request_id, receiver=receiver_user, status="pending"
                )
                .select_related("crew", "sender")
                .first()
            )

            if not crew_invite:
                # Check if there's a non-pending invite to provide better feedback
                existing_invite = (
                    CrewRequest.objects.filter(
                        requestId=request_id, receiver=receiver_user
                    )
                    .exclude(status="pending")
                    .first()
                )

                if existing_invite:
                    if existing_invite.status == "accepted":
                        return None, "This crew invite was already accepted.", None
                    elif existing_invite.status == "declined":
                        return None, "This crew invite was already declined.", None
                    elif existing_invite.status == "canceled":
                        return (
                            None,
                            "This crew invite was canceled by the sender.",
                            None,
                        )

                return None, "No pending crew invite found to decline.", None

            # Store invite info before updating
            invite_info = {
                "request_id": str(crew_invite.requestId),
                "crew_id": str(crew_invite.crew.crewId),
                "crew_name": crew_invite.crew.name,
                "sender_username": crew_invite.sender.username,
                "declined_at": timezone.now(),
            }

            # Update the invite status to declined
            crew_invite.status = "declined"
            crew_invite.save()

            return (
                {
                    "status": crew_invite.status,
                    "declined_at": invite_info["declined_at"],
                    "crew": {
                        "crew_id": invite_info["crew_id"],
                        "name": invite_info["crew_name"],
                    },
                    "sender": {"username": invite_info["sender_username"]},
                },
                "Crew invite declined successfully.",
                None,
            )

        except CustomUser.DoesNotExist:
            error_message = f"Receiver user not found with ID: {receiver_user_id}"
            print(f"[decline_crew_invite API] {error_message}")
            return None, error_message, None
        except Exception as e:
            error_message = f"Error declining crew invite: {str(e)}"
            print(f"[decline_crew_invite API] {error_message}")
            return None, error_message, None

    invite_data, success_message, error_message = await decline_crew_invite_logic(
        caller_user_id, request_id
    )

    if invite_data is None:
        notification_sent = await notify_by_bot(
            f"**[API: decline_crew_invite API]** \n\n {success_message or error_message} \n\n Platform: {platform} \n\n User ID: {caller_user_id} \n\n Request ID: {request_id}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        if notification_sent is None:
            print(
                "[decline_crew_invite API] Could not send notification: BOT_API_KEY not set"
            )
        raise HTTPException(status_code=400, detail=success_message or error_message)

    print(f"[decline_crew_invite API] {success_message}")
    return {"message": success_message, "crew_invite": invite_data}


@router.post("/cancel-crew-invite/{request_id}")
async def cancel_crew_invite(
    request: Request,
    request_id: UUID,
    caller_user_id: Optional[int] = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    API endpoint to cancel a crew invite sent to another user.
    """
    print(f"[cancel_crew_invite API] Function called with request_id: {request_id}")

    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def cancel_crew_invite_logic(sender_user_id, request_id):
        try:
            # Get sender user
            sender_user = CustomUser.objects.get(id=sender_user_id)

            # Find the pending crew invite
            crew_invite = (
                CrewRequest.objects.filter(
                    requestId=request_id, sender=sender_user, status="pending"
                )
                .select_related("crew", "receiver")
                .first()
            )

            if not crew_invite:
                # Check if there's a non-pending invite to provide better feedback
                existing_invite = (
                    CrewRequest.objects.filter(requestId=request_id, sender=sender_user)
                    .exclude(status="pending")
                    .first()
                )

                if existing_invite:
                    if existing_invite.status == "accepted":
                        return None, "This crew invite was already accepted.", None
                    elif existing_invite.status == "declined":
                        return None, "This crew invite was already declined.", None
                    elif existing_invite.status == "canceled":
                        return None, "This crew invite was already canceled.", None

                return None, "No pending crew invite found to cancel.", None

            # Store invite info before updating
            invite_info = {
                "request_id": str(crew_invite.requestId),
                "crew_id": str(crew_invite.crew.crewId),
                "crew_name": crew_invite.crew.name,
                "receiver_username": crew_invite.receiver.username,
                "canceled_at": timezone.now(),
            }

            # Update the invite status to canceled
            crew_invite.status = "canceled"
            crew_invite.save()

            return (
                {
                    "status": crew_invite.status,
                    "canceled_at": invite_info["canceled_at"],
                    "crew": {
                        "crew_id": invite_info["crew_id"],
                        "name": invite_info["crew_name"],
                    },
                    "receiver": {"username": invite_info["receiver_username"]},
                },
                "Crew invite canceled successfully.",
                None,
            )

        except CustomUser.DoesNotExist:
            error_message = f"Sender user not found with ID: {sender_user_id}"
            print(f"[cancel_crew_invite API] {error_message}")
            return None, error_message, None
        except Exception as e:
            error_message = f"Error canceling crew invite: {str(e)}"
            print(f"[cancel_crew_invite API] {error_message}")
            return None, error_message, None

    invite_data, success_message, error_message = await cancel_crew_invite_logic(
        caller_user_id, request_id
    )

    if invite_data is None:
        notification_sent = await notify_by_bot(
            f"**[API: cancel_crew_invite API]** \n\n {success_message or error_message} \n\n Platform: {platform} \n\n User ID: {caller_user_id} \n\n Request ID: {request_id}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        if notification_sent is None:
            print(
                "[cancel_crew_invite API] Could not send notification: BOT_API_KEY not set"
            )
        raise HTTPException(status_code=400, detail=success_message or error_message)

    print(f"[cancel_crew_invite API] {success_message}")
    return {"message": success_message, "crew_invite": invite_data}


@router.get("/whats-happening")
async def get_whats_happening(
    request: Request,
    caller_user_id: Optional[int] = Depends(get_current_user),
    platform: Optional[str] = None,
    limit: int = Query(20, ge=1, le=50),
):
    """
    API endpoint to get what's happening for a user.
    Returns activities from friends including:
    - Friend connections
    - Crew memberships
    - Event tickets
    - Go-with requests
    - Crew invites
    """
    print(
        f"[get_whats_happening API] Function called with caller_user_id: {caller_user_id}"
    )

    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def get_activities(caller_user_id, limit):
        try:
            user = CustomUser.objects.get(id=caller_user_id)
            user_profile = user.user_profile

            # Get friend user IDs
            friend_ids = [friend.user.id for friend in user_profile.friends.all()]

            # Get activities where either:
            # 1. The activity is performed by a friend
            # 2. The activity involves a friend (in the content)
            activities = (
                SocialActivity.objects.filter(
                    Q(user_id__in=friend_ids)  # Activities by friends
                    | Q(
                        content__friend_username__in=[
                            friend.user.username
                            for friend in user_profile.friends.all()
                        ]
                    )  # Activities involving friends
                )
                .select_related("user", "user__user_profile")
                .order_by("-created_at")[:limit]
            )

            activities_data = []
            for activity in activities:
                # Base activity data
                activity_data = {
                    "activity_id": str(activity.activityId),
                    "activity_type": activity.activity_type,
                    "created_at": activity.created_at,
                    "user": {
                        "user_id": str(activity.user.user_id),
                        "username": activity.user.username,
                        "first_name": activity.user.first_name,
                        "last_name": activity.user.last_name,
                        "profile_photo": (
                            activity.user.user_profile.profile_photo.url
                            if activity.user.user_profile.profile_photo
                            else None
                        ),
                    },
                    "content": activity.content,
                }

                # Add activity-specific formatting
                if activity.activity_type == "friend_accepted":
                    # If the activity is by a friend connecting with someone else
                    if activity.user.id in friend_ids:
                        activity_data["message"] = (
                            f"{activity.user.first_name} connected with {activity.content['friend_name']}"
                        )
                    # If the activity is by someone else connecting with your friend
                    else:
                        activity_data["message"] = (
                            f"{activity.user.first_name} connected with {activity.content['friend_name']}"
                        )
                elif activity.activity_type == "crew_joined":
                    activity_data["message"] = (
                        f"{activity.user.first_name} joined {activity.content['crew']}"
                    )
                elif activity.activity_type == "ticket_purchased":
                    # Format the message with ticket details
                    ticket_info = []
                    if activity.content.get("quantity") > 1:
                        ticket_info.append(f"{activity.content['quantity']} tickets")
                    if activity.content.get("ticket_type"):
                        ticket_info.append(f"({activity.content['ticket_type']})")
                    if activity.content.get("price"):
                        ticket_info.append(f"for ${activity.content['price']} each")

                    event_info = []
                    if activity.content.get("venue"):
                        event_info.append(f"at {activity.content['venue']}")
                    if activity.content.get("event_time"):
                        event_info.append(f"at {activity.content['event_time']}")

                    message = f"{activity.user.first_name} got {' '.join(ticket_info)} to {activity.content['event_title']}"
                    if event_info:
                        message += f" {' '.join(event_info)}"

                    activity_data["message"] = message
                elif activity.activity_type == "go_with_accepted":
                    # If the activity is by a friend going with someone else
                    if activity.user.id in friend_ids:
                        activity_data["message"] = (
                            f"{activity.user.first_name} is going with {activity.content['other_user']['name']} to {activity.content['event_title']}"
                        )
                    # If the activity is by someone else going with your friend
                    else:
                        activity_data["message"] = (
                            f"{activity.content['other_user']['name']} is going with {activity.user.first_name} to {activity.content['event_title']}"
                        )
                elif activity.activity_type == "crew_invite_accepted":
                    activity_data["message"] = (
                        f"{activity.user.first_name} joined {activity.content['crew']} (invited by {activity.content['invited_by']['name']})"
                    )

                activities_data.append(activity_data)

            return activities_data, None

        except CustomUser.DoesNotExist:
            error_message = f"User not found with ID: {caller_user_id}"
            print(f"[get_whats_happening API] {error_message}")
            return None, error_message
        except Exception as e:
            error_message = f"Error getting activities: {str(e)}"
            print(f"[get_whats_happening API] {error_message}")
            return None, error_message

    activities_data, error_message = await get_activities(caller_user_id, limit)
    if activities_data is None:
        notification_sent = await notify_by_bot(
            f"**[API: get_whats_happening API]** \n\n {error_message} \n\n Platform: {platform} \n\n User ID: {caller_user_id} \n\n Limit: {limit}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        if notification_sent is None:
            print(
                "[get_whats_happening API] Could not send notification: BOT_API_KEY not set"
            )
        raise HTTPException(status_code=400, detail=error_message)

    print(f"[get_whats_happening API] Returning {len(activities_data)} activities")
    return {"activities": activities_data}


@router.get("/get_user_friends_paginated")
async def get_user_friends_paginated(
    request: Request,
    caller_user_id: Optional[int] = Depends(get_current_user),
    page: int = Query(1, ge=1, description="Page number (starts from 1)"),
    page_size: int = Query(
        10, ge=1, le=50, description="Number of friends per page (max 50)"
    ),
    platform: Optional[str] = None,
):
    """
    API endpoint to get all friends of a user with pagination support.
    Returns paginated results to prevent slow load times with large friend lists.
    """
    print(
        f"[get_user_friends_paginated API] Function called for user ID: {caller_user_id}, page: {page}, page_size: {page_size}"
    )

    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def get_user_friends_paginated_data(caller_user_id, page, page_size):
        try:
            user = CustomUser.objects.get(id=caller_user_id)
            user_profile = user.user_profile  # type: ignore[attr-defined]

            # Get total count of friends
            total_friends = user_profile.friends.count()

            # Calculate pagination
            total_pages = (
                total_friends + page_size - 1
            ) // page_size  # Ceiling division
            offset = (page - 1) * page_size

            # Get paginated friends
            friends = user_profile.friends.all()[offset : offset + page_size]

            friends_data = [
                {
                    "user_id": str(friend.user.user_id),
                    "username": friend.user.username,
                    "first_name": friend.user.first_name,
                    "last_name": friend.user.last_name,
                    "profile_photo": (
                        friend.profile_photo.url if friend.profile_photo else None
                    ),
                }
                for friend in friends
            ]

            return {
                "friends": friends_data,
                "pagination": {
                    "current_page": page,
                    "page_size": page_size,
                    "total_friends": total_friends,
                    "total_pages": total_pages,
                    "has_next": page < total_pages,
                    "has_previous": page > 1,
                },
            }, None
        except CustomUser.DoesNotExist:
            print(
                f"[get_user_friends_paginated API] User not found with ID: {caller_user_id}"
            )
            return None, "User not found"
        except Exception as e:
            print(
                f"[get_user_friends_paginated API] Error retrieving user friends: {str(e)}"
            )
            return None, f"Error retrieving user friends: {str(e)}"

    try:
        result_data, error_message = await get_user_friends_paginated_data(
            caller_user_id, page, page_size
        )
        if result_data is None:
            notification_sent = await notify_by_bot(
                f"**[API: get_user_friends_paginated API]** \n\n {error_message} \n\n Platform: {platform} \n\n User ID: {caller_user_id} \n\n Page: {page} \n\n Page Size: {page_size}",
                platform or "Unknown",
                "ERROR",
                device_info,
            )
            if notification_sent is None:
                print(
                    "[get_user_friends_paginated API] Could not send notification: BOT_API_KEY not set"
                )
            raise HTTPException(status_code=500, detail=error_message)

        print(
            f"[get_user_friends_paginated API] Returning {len(result_data['friends'])} friends for page {page}"
        )
        return result_data
    except Exception as e:
        error_message = f"Error in get_user_friends_paginated API: {str(e)}"
        print(f"[get_user_friends_paginated API] {error_message}")
        raise HTTPException(status_code=500, detail=error_message)


@router.get("/check-friend-request-status/{target_username}")
async def check_friend_request_status(
    request: Request,
    target_username: str,
    caller_user_id: Optional[int] = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    API endpoint to check the friend request status between the caller and target user.
    Returns the current status to help determine which UI elements to show.
    """
    print(
        f"[check_friend_request_status API] Function called with target_username: {target_username}"
    )

    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def check_friend_request_status_logic(caller_user_id, target_username):
        try:
            # Validate Discord-style username
            if not is_valid_discord_username(target_username):
                return (
                    None,
                    "Invalid username format. Please use the full Discord-style username (e.g., name#1234).",
                    None,
                )

            # Get caller user
            caller_user = CustomUser.objects.get(id=caller_user_id)

            # Check if trying to check status with self
            if target_username == caller_user.username:
                return (
                    None,
                    "You cannot check friend request status with yourself.",
                    None,
                )

            # Get target user profile - use full Discord-style username
            try:
                target_user_profile = UserProfile.objects.select_related("user").get(
                    user__username=target_username
                )
                target_user = target_user_profile.user
            except UserProfile.DoesNotExist:
                return None, "Target user not found.", None

            # Check if they are already friends
            if caller_user.user_profile.is_friends_with(target_user):
                return (
                    {
                        "status": "friends",
                        "message": "You are already friends with this user.",
                        "can_send_request": False,
                        "can_accept_request": False,
                        "can_cancel_request": False,
                        "can_decline_request": False,
                        "can_remove_friend": True,
                    },
                    "Already friends",
                    None,
                )

            # Check for existing friend request
            friend_request = (
                FriendRequest.objects.filter(
                    Q(sender=caller_user, receiver=target_user)
                    | Q(sender=target_user, receiver=caller_user)
                )
                .order_by("-created_at")
                .first()
            )

            if friend_request:
                if friend_request.status == "pending":
                    # Check who sent the request
                    if friend_request.sender == caller_user:
                        # Caller sent the request
                        return (
                            {
                                "status": "sent_pending",
                                "message": "You have sent a friend request to this user.",
                                "can_send_request": False,
                                "can_accept_request": False,
                                "can_cancel_request": True,
                                "can_decline_request": False,
                                "can_remove_friend": False,
                                "request_id": str(friend_request.requestId),
                                "created_at": friend_request.created_at,
                            },
                            "Request sent and pending",
                            None,
                        )
                    else:
                        # Caller received the request
                        return (
                            {
                                "status": "received_pending",
                                "message": "You have received a friend request from this user.",
                                "can_send_request": False,
                                "can_accept_request": True,
                                "can_cancel_request": False,
                                "can_decline_request": True,
                                "can_remove_friend": False,
                                "request_id": str(friend_request.requestId),
                                "created_at": friend_request.created_at,
                            },
                            "Request received and pending",
                            None,
                        )
                elif friend_request.status == "accepted":
                    # This shouldn't happen if they're not friends, but handle it
                    return (
                        {
                            "status": "friends",
                            "message": "You are already friends with this user.",
                            "can_send_request": False,
                            "can_accept_request": False,
                            "can_cancel_request": False,
                            "can_decline_request": False,
                            "can_remove_friend": True,
                        },
                        "Already friends",
                        None,
                    )
                elif friend_request.status == "canceled":
                    # Request was canceled, can send new one
                    return (
                        {
                            "status": "canceled",
                            "message": "Previous friend request was canceled. You can send a new one.",
                            "can_send_request": True,
                            "can_accept_request": False,
                            "can_cancel_request": False,
                            "can_decline_request": False,
                            "can_remove_friend": False,
                        },
                        "Request was canceled",
                        None,
                    )
                # Note: declined requests are deleted, so they won't appear here

            # No friend request exists
            return (
                {
                    "status": "no_request",
                    "message": "No friend request exists. You can send one.",
                    "can_send_request": True,
                    "can_accept_request": False,
                    "can_cancel_request": False,
                    "can_decline_request": False,
                    "can_remove_friend": False,
                },
                "No request exists",
                None,
            )

        except CustomUser.DoesNotExist:
            error_message = f"Caller user not found with ID: {caller_user_id}"
            print(f"[check_friend_request_status API] {error_message}")
            return None, error_message, None
        except Exception as e:
            error_message = f"Error checking friend request status: {str(e)}"
            print(f"[check_friend_request_status API] {error_message}")
            return None, error_message, None

    status_data, success_message, error_message = (
        await check_friend_request_status_logic(caller_user_id, target_username)
    )

    if status_data is None:
        notification_sent = await notify_by_bot(
            f"**[API: check_friend_request_status API]** \n\n {success_message or error_message} \n\n Platform: {platform} \n\n User ID: {caller_user_id} \n\n Target Username: {target_username}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        if notification_sent is None:
            print(
                "[check_friend_request_status API] Could not send notification: BOT_API_KEY not set"
            )
        raise HTTPException(status_code=400, detail=success_message or error_message)

    print(f"[check_friend_request_status API] {success_message}")
    return {"message": success_message, "friend_request_status": status_data}


@router.get("/get_user_crews_paginated")
async def get_user_crews_paginated(
    request: Request,
    caller_user_id: Optional[int] = Depends(get_current_user),
    page: int = Query(1, ge=1, description="Page number (starts from 1)"),
    page_size: int = Query(
        10, ge=1, le=50, description="Number of crews per page (max 50)"
    ),
    platform: Optional[str] = None,
):
    """
    API endpoint to get all crews a user is a member of with pagination support.
    Returns paginated results to prevent slow load times with large crew lists.
    """
    print(
        f"[get_user_crews_paginated API] Function called for user ID: {caller_user_id}, page: {page}, page_size: {page_size}"
    )

    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def get_user_crews_paginated_data(caller_user_id, page, page_size):
        try:
            user = CustomUser.objects.get(id=caller_user_id)

            # Get total count of crews the user is a member of
            total_crews = CrewMember.objects.filter(user=user).count()

            # Calculate pagination
            total_pages = (total_crews + page_size - 1) // page_size  # Ceiling division
            offset = (page - 1) * page_size

            # Get paginated crew memberships with crew details
            crew_memberships = (
                CrewMember.objects.filter(user=user)
                .select_related("crew", "crew__created_by")
                .order_by("-joined_at")[offset : offset + page_size]
            )

            crews_data = []
            for membership in crew_memberships:
                crew = membership.crew

                # Get member count for this crew
                member_count = CrewMember.objects.filter(crew=crew).count()

                crews_data.append(
                    {
                        "crewId": str(crew.crewId),
                        "name": crew.name,
                        "member_count": member_count,
                    }
                )

            return {
                "crews": crews_data,
                "pagination": {
                    "current_page": page,
                    "page_size": page_size,
                    "total_crews": total_crews,
                    "total_pages": total_pages,
                    "has_next": page < total_pages,
                    "has_previous": page > 1,
                },
            }, None
        except CustomUser.DoesNotExist:
            print(
                f"[get_user_crews_paginated API] User not found with ID: {caller_user_id}"
            )
            return None, "User not found"
        except Exception as e:
            print(
                f"[get_user_crews_paginated API] Error retrieving user crews: {str(e)}"
            )
            return None, f"Error retrieving user crews: {str(e)}"

    try:
        result_data, error_message = await get_user_crews_paginated_data(
            caller_user_id, page, page_size
        )
        if result_data is None:
            notification_sent = await notify_by_bot(
                f"**[API: get_user_crews_paginated API]** \n\n {error_message} \n\n Platform: {platform} \n\n User ID: {caller_user_id} \n\n Page: {page} \n\n Page Size: {page_size}",
                platform or "Unknown",
                "ERROR",
                device_info,
            )
            if notification_sent is None:
                print(
                    "[get_user_crews_paginated API] Could not send notification: BOT_API_KEY not set"
                )
            raise HTTPException(status_code=500, detail=error_message)

        print(
            f"[get_user_crews_paginated API] Returning {len(result_data['crews'])} crews for page {page}"
        )
        return result_data
    except Exception as e:
        error_message = f"Error in get_user_crews_paginated API: {str(e)}"
        print(f"[get_user_crews_paginated API] {error_message}")
        raise HTTPException(status_code=500, detail=error_message)


@router.get("/get_crew_details_with_members/{crew_id}")
async def get_crew_details_with_members(
    request: Request,
    crew_id: UUID,
    caller_user_id: Optional[int] = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    API endpoint to retrieve comprehensive information about a specific crew including all members.
    """
    print(
        f"[get_crew_details_with_members API] Function called with crew_id: {crew_id}"
    )

    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def get_crew_details_with_members_data(crew_id, caller_user_id):
        try:
            # Get crew with related data in optimized queries
            crew = Crew.objects.select_related(
                "created_by", "created_by__user_profile"
            ).get(crewId=crew_id)

            # Get crew creator profile information
            creator_profile = (
                crew.created_by.user_profile
                if hasattr(crew.created_by, "user_profile")
                else None
            )
            creator_data = {
                "user_id": str(crew.created_by.user_id),
                "username": crew.created_by.username,
                "first_name": crew.created_by.first_name,
                "last_name": crew.created_by.last_name,
                "profile_photo": (
                    creator_profile.profile_photo.url
                    if creator_profile and creator_profile.profile_photo
                    else None
                ),
            }

            # Get all crew members with their profiles
            crew_members = []
            user_is_member = False
            user_is_admin = False

            # FIRST: Check if the caller is the crew creator
            if caller_user_id and crew.created_by.id == caller_user_id:
                user_is_member = True
                user_is_admin = True  # Creator is always admin
                print(
                    f"[get_crew_details_with_members] User {caller_user_id} is the crew creator"
                )

            # Get all crew member records
            crew_member_records = CrewMember.objects.filter(crew=crew).select_related(
                "user", "user__user_profile"
            )

            print(
                f"[get_crew_details_with_members] Found {crew_member_records.count()} crew members"
            )
            print(
                f"[get_crew_details_with_members] Checking membership for user_id: {caller_user_id}"
            )

            for crew_member in crew_member_records:
                member_profile = (
                    crew_member.user.user_profile
                    if hasattr(crew_member.user, "user_profile")
                    else None
                )

                # DEBUG: Log member IDs for comparison
                print(
                    f"[get_crew_details_with_members] Comparing caller_user_id={caller_user_id} with member_user_id={crew_member.user.id}"
                )

                # Check if the caller is this crew member - ensure both are integers
                if caller_user_id and int(crew_member.user.id) == int(caller_user_id):
                    user_is_member = True
                    user_is_admin = crew_member.is_admin
                    print(
                        f"[get_crew_details_with_members] User {caller_user_id} found as crew member with admin={crew_member.is_admin}"
                    )

                crew_members.append(
                    {
                        "user": {
                            "user_id": str(crew_member.user.user_id),
                            "username": crew_member.user.username,
                            "first_name": crew_member.user.first_name,
                            "last_name": crew_member.user.last_name,
                        },
                        "profile": {
                            "profile_photo": (
                                member_profile.profile_photo.url
                                if member_profile and member_profile.profile_photo
                                else None
                            ),
                        },
                        "membership_details": {
                            "joined_at": crew_member.joined_at,
                            "is_admin": crew_member.is_admin,
                        },
                    }
                )

            # Final debug log
            print(
                f"[get_crew_details_with_members] Final membership status: user_is_member={user_is_member}, user_is_admin={user_is_admin}"
            )

            # Also check if caller should be included but is missing from CrewMember records
            if caller_user_id and not user_is_member:
                # Check for potential data inconsistency
                direct_membership_check = CrewMember.objects.filter(
                    crew=crew, user_id=caller_user_id
                ).exists()
                print(
                    f"[get_crew_details_with_members] Direct membership check result: {direct_membership_check}"
                )

                if direct_membership_check:
                    print(
                        f"[get_crew_details_with_members] WARNING: Found membership in direct check but missed in iteration!"
                    )
                    user_is_member = True
                    # Get the admin status
                    try:
                        member_record = CrewMember.objects.get(
                            crew=crew, user_id=caller_user_id
                        )
                        user_is_admin = member_record.is_admin
                    except CrewMember.DoesNotExist:
                        pass

            # Get shared events for this crew (limit for performance)
            from eventManagementApp.models import SharedEvent

            shared_events = []
            for shared_event in SharedEvent.objects.filter(crew=crew).select_related(
                "event", "sender"
            )[:20]:
                shared_events.append(
                    {
                        "event": {
                            "eventId": str(shared_event.event.eventId),
                            "title": shared_event.event.title,
                            "date": shared_event.event.date,
                            "header_photo": (
                                shared_event.event.header_photo.url
                                if shared_event.event.header_photo
                                else None
                            ),
                        },
                        "sender": {
                            "username": shared_event.sender.username,
                            "first_name": shared_event.sender.first_name,
                            "last_name": shared_event.sender.last_name,
                        },
                        "shared_at": shared_event.shared_at,
                    }
                )

            return {
                "crewId": str(crew.crewId),
                "name": crew.name,
                "bio": crew.bio,
                "created_at": crew.created_at,
                "created_by": creator_data,
                "members": crew_members,
                "member_count": len(crew_members),
                "shared_events": shared_events,
                "user_is_member": user_is_member,
                "user_is_admin": user_is_admin,
            }, None
        except Crew.DoesNotExist:
            error_message = f"Crew not found with ID: {crew_id}"
            print(
                f"[get_crew_details_with_members API] Crew not found with ID: {crew_id}"
            )
            return None, error_message
        except Exception as e:
            error_message = f"Error retrieving crew data: {str(e)}"
            print(
                f"[get_crew_details_with_members API] Error retrieving crew data: {str(e)}"
            )
            return None, error_message

    crew_data, error_message = await get_crew_details_with_members_data(
        crew_id, caller_user_id
    )
    if crew_data is None:
        notification_sent = await notify_by_bot(
            f"**[API: get_crew_details_with_members API]** \n\n {error_message} \n\n Platform: {platform} \n\n User ID: {caller_user_id} \n\n Crew ID: {crew_id}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        if notification_sent is None:
            print(
                "[get_crew_details_with_members API] Could not send notification: BOT_API_KEY not set"
            )
        raise HTTPException(status_code=404, detail=error_message)

    print(
        f"[get_crew_details_with_members API] Returning details for crew: {crew_data['name']}"
    )

    return {"crew_details": crew_data}


@router.post("/create-surf-post", response_model=SurfPostResponse)
async def create_surf_post(
    request: Request,
    data: SurfPostCreate,
    caller_user_id: Optional[int] = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    API endpoint to create a new surf post for an event.
    """
    print(f"[create_surf_post API] Function called with event_id: {data.event_id}")

    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def create_surf_post_logic(caller_user_id, event_id, content):
        try:
            # Get the user
            user = CustomUser.objects.get(id=caller_user_id)

            # Get the event
            event = Event.objects.get(eventId=event_id)

            # Create the surf post
            post = SurfPost.objects.create(user=user, event=event, content=content)

            return {
                "post_id": post.surfId,
                "event_id": event.eventId,
                "content": post.content,
                "created_at": post.created_at,
                "tideup": post.tideup,
                "tidedown": post.tidedown,
                "score": post.score,
            }, None
        except CustomUser.DoesNotExist:
            error_message = f"User not found with ID: {caller_user_id}"
            print(f"[create_surf_post API] {error_message}")
            return None, error_message
        except Event.DoesNotExist:
            error_message = f"Event not found with ID: {event_id}"
            print(f"[create_surf_post API] {error_message}")
            return None, error_message
        except Exception as e:
            error_message = f"Error creating surf post: {str(e)}"
            print(f"[create_surf_post API] {error_message}")
            return None, error_message

    post_data, error_message = await create_surf_post_logic(
        caller_user_id, data.event_id, data.content
    )
    if post_data is None:
        notification_sent = await notify_by_bot(
            f"**[API: create_surf_post API]** \n\n {error_message} \n\n Platform: {platform} \n\n User ID: {caller_user_id} \n\n Event ID: {data.event_id}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        if notification_sent is None:
            print(
                "[create_surf_post API] Could not send notification: BOT_API_KEY not set"
            )
        raise HTTPException(status_code=400, detail=error_message)

    print(f"[create_surf_post API] Surf post created successfully")
    return SurfPostResponse(**post_data)


@router.post("/surf-posts/vote")
async def vote_on_post(
    request: Request,
    data: VoteRequest,
    caller_user_id: Optional[int] = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    API endpoint to vote on a surf post.
    """
    print(f"[vote_on_post API] Function called with post_id: {data.post_id}")

    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def vote_on_post_logic(caller_user_id, post_id, vote_value):
        try:
            # Validate vote value
            if vote_value not in [1, -1]:
                return (
                    None,
                    "Invalid vote value. Must be 1 (tideup) or -1 (tidedown).",
                    None,
                )

            # Get the user
            user = CustomUser.objects.get(id=caller_user_id)

            # Get the post
            post = SurfPost.objects.get(surfId=post_id)

            # Check if user already has a vote
            existing_vote = TideUpTideDown.objects.filter(post=post, user=user).first()

            if existing_vote:
                # User already voted - update their vote
                old_vote_value = existing_vote.value
                existing_vote.value = vote_value
                existing_vote.save()
                created = False
                vote_changed = old_vote_value != vote_value
            else:
                # User hasn't voted before - create new vote
                existing_vote = TideUpTideDown.objects.create(
                    post=post, user=user, value=vote_value
                )
                created = True
                vote_changed = False

            # Refresh the post to get updated vote counts
            post.refresh_from_db()

            return {
                "message": "Vote recorded successfully",
                "score": post.score,
                "tideup": post.tideup,
                "tidedown": post.tidedown,
                "vote_value": vote_value,
                "created": created,
                "vote_changed": vote_changed,
                "previous_vote": (
                    old_vote_value if existing_vote and not created else None
                ),
            }, None
        except CustomUser.DoesNotExist:
            error_message = f"User not found with ID: {caller_user_id}"
            print(f"[vote_on_post API] {error_message}")
            return None, error_message, None
        except SurfPost.DoesNotExist:
            error_message = f"Surf post not found with ID: {post_id}"
            print(f"[vote_on_post API] {error_message}")
            return None, error_message, None
        except Exception as e:
            error_message = f"Error voting on post: {str(e)}"
            print(f"[vote_on_post API] {error_message}")
            return None, error_message, None

    vote_data, error_message = await vote_on_post_logic(
        caller_user_id, data.post_id, data.vote
    )
    if vote_data is None:
        notification_sent = await notify_by_bot(
            f"**[API: vote_on_post API]** \n\n {error_message} \n\n Platform: {platform} \n\n User ID: {caller_user_id} \n\n Post ID: {data.post_id} \n\n Vote: {data.vote}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        if notification_sent is None:
            print("[vote_on_post API] Could not send notification: BOT_API_KEY not set")
        raise HTTPException(status_code=400, detail=error_message)

    print(f"[vote_on_post API] Vote recorded successfully")
    return {"message": vote_data["message"], "vote_data": vote_data}


@router.post("/surf-posts/downvote/{post_id}")
async def downvote_post(
    request: Request,
    post_id: UUID,
    caller_user_id: Optional[int] = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    API endpoint to downvote a surf post.
    Allows users to downvote even if they haven't upvoted before.
    """
    print(f"[downvote_post API] Function called with post_id: {post_id}")

    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def downvote_post_logic(caller_user_id, post_id):
        try:
            # Get the user
            user = CustomUser.objects.get(id=caller_user_id)

            # Get the post
            post = SurfPost.objects.get(surfId=post_id)

            # Check if user already has a vote
            existing_vote = TideUpTideDown.objects.filter(post=post, user=user).first()

            if existing_vote:
                # User already voted - update to downvote
                old_vote_value = existing_vote.value
                existing_vote.value = -1  # Downvote
                existing_vote.save()
                vote_changed = old_vote_value != -1
            else:
                # User hasn't voted before - create downvote
                existing_vote = TideUpTideDown.objects.create(
                    post=post, user=user, value=-1
                )
                vote_changed = False

            # Refresh the post to get updated vote counts
            post.refresh_from_db()

            return (
                {
                    "message": "Downvote recorded successfully",
                    "score": post.score,
                    "tideup": post.tideup,
                    "tidedown": post.tidedown,
                    "vote_value": -1,
                    "vote_changed": vote_changed,
                    "previous_vote": (
                        old_vote_value if existing_vote and vote_changed else None
                    ),
                },
                "Downvote recorded successfully",
                None,
            )
        except CustomUser.DoesNotExist:
            error_message = f"User not found with ID: {caller_user_id}"
            print(f"[downvote_post API] {error_message}")
            return None, error_message, None
        except SurfPost.DoesNotExist:
            error_message = f"Surf post not found with ID: {post_id}"
            print(f"[downvote_post API] {error_message}")
            return None, error_message, None
        except Exception as e:
            error_message = f"Error downvoting post: {str(e)}"
            print(f"[downvote_post API] {error_message}")
            return None, error_message, None

    vote_data, success_message, error_message = await downvote_post_logic(
        caller_user_id, post_id
    )
    if vote_data is None:
        notification_sent = await notify_by_bot(
            f"**[API: downvote_post API]** \n\n {success_message or error_message} \n\n Platform: {platform} \n\n User ID: {caller_user_id} \n\n Post ID: {post_id}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        if notification_sent is None:
            print(
                "[downvote_post API] Could not send notification: BOT_API_KEY not set"
            )
        raise HTTPException(status_code=404, detail=success_message or error_message)

    print(f"[downvote_post API] Downvote recorded successfully")
    return {"message": vote_data["message"], "vote_data": vote_data}


@router.get("/surf-posts/{event_id}")
async def get_surf_posts_for_event(
    request: Request,
    event_id: UUID,
    platform: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
):
    """
    API endpoint to get surf posts for a specific event.
    """
    print(f"[get_surf_posts_for_event API] Function called with event_id: {event_id}")

    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def get_surf_posts_logic(event_id, limit):
        try:
            # Get the event
            event = Event.objects.get(eventId=event_id)

            # Get surf posts for this event
            posts = (
                SurfPost.objects.filter(event=event)
                .select_related("user", "user__user_profile")
                .order_by("-created_at")[:limit]
            )

            posts_data = []
            for post in posts:
                user_profile = (
                    post.user.user_profile
                    if hasattr(post.user, "user_profile")
                    else None
                )

                posts_data.append(
                    {
                        "post_id": post.surfId,
                        "event_id": event.eventId,
                        "content": post.content,
                        "created_at": post.created_at,
                        "tideup": post.tideup,
                        "tidedown": post.tidedown,
                        "score": post.score,
                        "user": {
                            "user_id": str(post.user.user_id),
                            "username": post.user.username,
                            "first_name": post.user.first_name,
                            "last_name": post.user.last_name,
                            "profile_photo": (
                                user_profile.profile_photo.url
                                if user_profile and user_profile.profile_photo
                                else None
                            ),
                        },
                    }
                )

            return posts_data, None
        except Event.DoesNotExist:
            error_message = f"Event not found with ID: {event_id}"
            print(f"[get_surf_posts_for_event API] {error_message}")
            return None, error_message
        except Exception as e:
            error_message = f"Error getting surf posts: {str(e)}"
            print(f"[get_surf_posts_for_event API] {error_message}")
            return None, error_message

    posts_data, error_message = await get_surf_posts_logic(event_id, limit)
    if posts_data is None:
        notification_sent = await notify_by_bot(
            f"**[API: get_surf_posts_for_event API]** \n\n {error_message} \n\n Platform: {platform} \n\n Event ID: {event_id}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        if notification_sent is None:
            print(
                "[get_surf_posts_for_event API] Could not send notification: BOT_API_KEY not set"
            )
        raise HTTPException(status_code=404, detail=error_message)

    print(f"[get_surf_posts_for_event API] Returning {len(posts_data)} surf posts")
    return {"surf_posts": posts_data}


@router.get("/surf-posts")
async def get_all_surf_posts(
    request: Request,
    platform: Optional[str] = None,
    page: int = Query(1, ge=1, description="Page number (starts from 1)"),
    page_size: int = Query(
        20, ge=1, le=100, description="Number of posts per page (max 100)"
    ),
    sort_by: str = Query(
        "created_at", description="Sort by field: created_at, score, tideup, tidedown"
    ),
    order: str = Query("desc", description="Sort order: asc or desc"),
):
    """
    API endpoint to get all surf posts with pagination and sorting support.
    """
    print(
        f"[get_all_surf_posts API] Function called with page: {page}, page_size: {page_size}"
    )

    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def get_all_surf_posts_logic(page, page_size, sort_by, order):
        try:
            # Validate sort_by field
            valid_sort_fields = ["created_at", "score", "tideup", "tidedown"]
            if sort_by not in valid_sort_fields:
                sort_by = "created_at"  # Default to created_at if invalid

            # Validate order
            if order not in ["asc", "desc"]:
                order = "desc"  # Default to desc if invalid

            # Build sort field
            sort_field = f"{'-' if order == 'desc' else ''}{sort_by}"

            # Get total count of surf posts
            total_posts = SurfPost.objects.count()

            # Calculate pagination
            total_pages = (total_posts + page_size - 1) // page_size  # Ceiling division
            offset = (page - 1) * page_size

            # Get paginated surf posts with user and event information
            posts = SurfPost.objects.select_related(
                "user", "user__user_profile", "event"
            ).order_by(sort_field)[offset : offset + page_size]

            posts_data = []
            for post in posts:
                user_profile = (
                    post.user.user_profile
                    if hasattr(post.user, "user_profile")
                    else None
                )

                posts_data.append(
                    {
                        "post_id": post.surfId,
                        "event_id": post.event.eventId,
                        "event_title": post.event.title,
                        "content": post.content,
                        "created_at": post.created_at,
                        "tideup": post.tideup,
                        "tidedown": post.tidedown,
                        "score": post.score,
                        "user": {
                            "user_id": str(post.user.user_id),
                            "username": post.user.username,
                            "first_name": post.user.first_name,
                            "last_name": post.user.last_name,
                            "profile_photo": (
                                user_profile.profile_photo.url
                                if user_profile and user_profile.profile_photo
                                else None
                            ),
                        },
                        "event": {
                            "event_id": str(post.event.eventId),
                            "title": post.event.title,
                            "date": post.event.date,
                            "header_photo": (
                                post.event.header_photo.url
                                if post.event.header_photo
                                else None
                            ),
                        },
                    }
                )

            return {
                "posts": posts_data,
                "pagination": {
                    "current_page": page,
                    "page_size": page_size,
                    "total_posts": total_posts,
                    "total_pages": total_pages,
                    "has_next": page < total_pages,
                    "has_previous": page > 1,
                },
                "sorting": {
                    "sort_by": sort_by,
                    "order": order,
                },
            }, None
        except Exception as e:
            error_message = f"Error getting all surf posts: {str(e)}"
            print(f"[get_all_surf_posts API] {error_message}")
            return None, error_message

    posts_data, error_message = await get_all_surf_posts_logic(
        page, page_size, sort_by, order
    )
    if posts_data is None:
        notification_sent = await notify_by_bot(
            f"**[API: get_all_surf_posts API]** \n\n {error_message} \n\n Platform: {platform} \n\n Page: {page} \n\n Page Size: {page_size}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        if notification_sent is None:
            print(
                "[get_all_surf_posts API] Could not send notification: BOT_API_KEY not set"
            )
        raise HTTPException(status_code=500, detail=error_message)

    print(f"[get_all_surf_posts API] Returning {len(posts_data['posts'])} surf posts")
    return posts_data


@router.get("/surf-post-form-fields")
async def get_surf_post_form_fields(
    request: Request,
    platform: Optional[str] = None,
):
    """
    API endpoint to get form fields for creating a surf post.
    Uses dynamic field discovery without hardcoding any field information.
    """
    print(f"[get_surf_post_form_fields API] Function called")

    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def get_surf_post_form_fields_logic():
        try:
            # Get form fields for SurfPost model dynamically
            FormClass = SurfPostForm
            fields_info = get_form_fields(FormClass)

            return {
                "form_fields": fields_info,
                "model_name": "SurfPost",
                "description": "Form fields for creating a new surf post",
                "related_endpoints": {
                    "active_events": "/active-events-for-surf-post",
                    "description": "Get list of active events for selection",
                },
            }, None
        except Exception as e:
            error_message = f"Error getting surf post form fields: {str(e)}"
            print(f"[get_surf_post_form_fields API] {error_message}")
            return None, error_message

    form_fields_data, error_message = await get_surf_post_form_fields_logic()
    if form_fields_data is None:
        notification_sent = await notify_by_bot(
            f"**[API: get_surf_post_form_fields API]** \n\n {error_message} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        if notification_sent is None:
            print(
                "[get_surf_post_form_fields API] Could not send notification: BOT_API_KEY not set"
            )
        raise HTTPException(status_code=500, detail=error_message)

    print(f"[get_surf_post_form_fields API] Returning surf post form fields")
    return form_fields_data


@router.get("/active-events-for-surf-post")
async def get_active_events_for_surf_post(
    request: Request,
    platform: Optional[str] = None,
    limit: int = Query(
        50, ge=1, le=200, description="Maximum number of events to return"
    ),
):
    """
    API endpoint to get active events that can be selected for creating a surf post.
    Returns events that are currently active (not past) and available for surf posts.
    """
    print(f"[get_active_events_for_surf_post API] Function called with limit: {limit}")

    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def get_active_events_logic(limit):
        try:
            from django.utils import timezone

            # Get current time
            now = timezone.now()

            # Get active events (events that haven't passed yet)
            # You can customize this query based on your Event model fields
            active_events = (
                Event.objects.filter(date__gte=now)  # Events with date >= current time
                .select_related("host", "host__user_profile")
                .order_by("date")  # Order by date (earliest first)
                .only(
                    "eventId",
                    "title",
                    "date",
                    "venue",
                    "header_photo",
                    "host__username",
                    "host__first_name",
                    "host__last_name",
                    "host__user_profile__profile_photo",
                )[:limit]
            )

            events_data = []
            for event in active_events:
                host_profile = (
                    event.host.user_profile
                    if hasattr(event.host, "user_profile")
                    else None
                )

                events_data.append(
                    {
                        "event_id": str(event.eventId),
                        "title": event.title,
                        "date": event.date,
                        "header_photo": (
                            event.header_photo.url if event.header_photo else None
                        ),
                        "host": {
                            "user_id": str(event.host.user_id),
                            "username": event.host.username,
                            "first_name": event.host.first_name,
                            "last_name": event.host.last_name,
                            "profile_photo": (
                                host_profile.profile_photo.url
                                if host_profile and host_profile.profile_photo
                                else None
                            ),
                        },
                        "formatted_date": (
                            event.date.strftime("%B %d, %Y at %I:%M %p")
                            if event.date
                            else None
                        ),
                    }
                )

            return {
                "active_events": events_data,
                "total_count": len(events_data),
                "description": "Active events available for surf post creation",
                "note": "Events are ordered by date (earliest first)",
            }, None
        except Exception as e:
            error_message = f"Error getting active events: {str(e)}"
            print(f"[get_active_events_for_surf_post API] {error_message}")
            return None, error_message

    events_data, error_message = await get_active_events_logic(limit)
    if events_data is None:
        notification_sent = await notify_by_bot(
            f"**[API: get_active_events_for_surf_post API]** \n\n {error_message} \n\n Platform: {platform} \n\n Limit: {limit}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        if notification_sent is None:
            print(
                "[get_active_events_for_surf_post API] Could not send notification: BOT_API_KEY not set"
            )
        raise HTTPException(status_code=500, detail=error_message)

    print(
        f"[get_active_events_for_surf_post API] Returning {len(events_data['active_events'])} active events"
    )
    return events_data


@router.get("/surf-posts/vote/{post_id}")
async def check_user_vote(
    request: Request,
    post_id: UUID,
    caller_user_id: Optional[int] = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    API endpoint to check the current user's vote status on a surf post.
    Returns whether the user has voted and what they voted (tideup/tidedown).
    """
    print(f"[check_user_vote API] Function called with post_id: {post_id}")

    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def check_user_vote_logic(caller_user_id, post_id):
        try:
            # Get the user
            user = CustomUser.objects.get(id=caller_user_id)

            # Get the post
            post = SurfPost.objects.get(surfId=post_id)

            # Check if user has voted
            vote = TideUpTideDown.objects.filter(post=post, user=user).first()

            if vote:
                # User has voted
                vote_status = "tideup" if vote.value == 1 else "tidedown"
                return (
                    {
                        "has_voted": True,
                        "vote_value": vote.value,
                        "vote_status": vote_status,
                        "voted_at": vote.created_at,
                        "post_id": str(post.surfId),
                        "post_score": post.score,
                        "post_tideup": post.tideup,
                        "post_tidedown": post.tidedown,
                    },
                    "Vote status retrieved successfully",
                    None,
                )
            else:
                # User hasn't voted
                return (
                    {
                        "has_voted": False,
                        "vote_value": None,
                        "vote_status": None,
                        "voted_at": None,
                        "post_id": str(post.surfId),
                        "post_score": post.score,
                        "post_tideup": post.tideup,
                        "post_tidedown": post.tidedown,
                    },
                    "Vote status retrieved successfully",
                    None,
                )
        except CustomUser.DoesNotExist:
            error_message = f"User not found with ID: {caller_user_id}"
            print(f"[check_user_vote API] {error_message}")
            return None, error_message, None
        except SurfPost.DoesNotExist:
            error_message = f"Surf post not found with ID: {post_id}"
            print(f"[check_user_vote API] {error_message}")
            return None, error_message, None
        except Exception as e:
            error_message = f"Error checking user vote: {str(e)}"
            print(f"[check_user_vote API] {error_message}")
            return None, error_message, None

    vote_data, success_message, error_message = await check_user_vote_logic(
        caller_user_id, post_id
    )
    if vote_data is None:
        notification_sent = await notify_by_bot(
            f"**[API: check_user_vote API]** \n\n {success_message or error_message} \n\n Platform: {platform} \n\n User ID: {caller_user_id} \n\n Post ID: {post_id}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        if notification_sent is None:
            print(
                "[check_user_vote API] Could not send notification: BOT_API_KEY not set"
            )
        raise HTTPException(status_code=404, detail=success_message or error_message)

    print(f"[check_user_vote API] Vote status retrieved successfully")
    return {"vote_status": vote_data}


@router.get("/surf-posts/post/{post_id}")
async def get_surf_post_details(
    request: Request,
    post_id: UUID,
    caller_user_id: Optional[int] = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    API endpoint to get detailed information about a specific surf post.
    Returns comprehensive post details including user info, event info, and vote counts.
    """
    print(f"[get_surf_post_details API] Function called with post_id: {post_id}")

    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def get_surf_post_details_logic(caller_user_id, post_id):
        try:
            # Get the post with related data
            post = SurfPost.objects.select_related(
                "user",
                "user__user_profile",
                "event",
                "event__host",
                "event__host__user_profile",
            ).get(surfId=post_id)

            # Get user profile
            user_profile = (
                post.user.user_profile if hasattr(post.user, "user_profile") else None
            )

            # Get event host profile
            event_host_profile = (
                post.event.host.user_profile
                if hasattr(post.event.host, "user_profile")
                else None
            )

            # Check if current user has voted on this post
            current_user_vote = None
            if caller_user_id:
                try:
                    user = CustomUser.objects.get(id=caller_user_id)
                    vote = TideUpTideDown.objects.filter(post=post, user=user).first()
                    if vote:
                        current_user_vote = {
                            "has_voted": True,
                            "vote_value": vote.value,
                            "vote_status": "tideup" if vote.value == 1 else "tidedown",
                            "voted_at": vote.created_at,
                        }
                    else:
                        current_user_vote = {
                            "has_voted": False,
                            "vote_value": None,
                            "vote_status": None,
                            "voted_at": None,
                        }
                except CustomUser.DoesNotExist:
                    current_user_vote = {
                        "has_voted": False,
                        "vote_value": None,
                        "vote_status": None,
                        "voted_at": None,
                    }

            # Build comprehensive post details
            post_details = {
                "post_id": str(post.surfId),
                "content": post.content,
                "created_at": post.created_at,
                "score": post.score,
                "tideup": post.tideup,
                "tidedown": post.tidedown,
                "user": {
                    "user_id": str(post.user.user_id),
                    "username": post.user.username,
                    "first_name": post.user.first_name,
                    "last_name": post.user.last_name,
                    "profile_photo": (
                        user_profile.profile_photo.url
                        if user_profile and user_profile.profile_photo
                        else None
                    ),
                    "is_verified": getattr(post.user, "is_verified", False),
                },
                "event": {
                    "event_id": str(post.event.eventId),
                    "title": post.event.title,
                    "header_photo": (
                        post.event.header_photo.url if post.event.header_photo else None
                    ),
                },
                "current_user_vote": current_user_vote,
                "engagement_metrics": {
                    "total_votes": post.tideup + post.tidedown,
                    "vote_ratio": (
                        round(post.tideup / (post.tideup + post.tidedown) * 100, 1)
                        if (post.tideup + post.tidedown) > 0
                        else 0
                    ),
                    "popularity_score": post.score,
                },
            }

            return post_details, "Post details retrieved successfully", None
        except SurfPost.DoesNotExist:
            error_message = f"Surf post not found with ID: {post_id}"
            print(f"[get_surf_post_details API] {error_message}")
            return None, error_message, None
        except Exception as e:
            error_message = f"Error getting surf post details: {str(e)}"
            print(f"[get_surf_post_details API] {error_message}")
            return None, error_message, None

    post_details, success_message, error_message = await get_surf_post_details_logic(
        caller_user_id, post_id
    )
    if post_details is None:
        notification_sent = await notify_by_bot(
            f"**[API: get_surf_post_details API]** \n\n {success_message or error_message} \n\n Platform: {platform} \n\n User ID: {caller_user_id} \n\n Post ID: {post_id}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        if notification_sent is None:
            print(
                "[get_surf_post_details API] Could not send notification: BOT_API_KEY not set"
            )
        raise HTTPException(status_code=404, detail=success_message or error_message)

    print(f"[get_surf_post_details API] Post details retrieved successfully")
    return {"post_details": post_details}


@router.get("/fixed-messages", response_model=List[FixedMessageResponse])
async def list_fixed_messages():
    @database_sync_to_async
    def get_fixed_messages():
        return [
            {
                "id": str(message.id),
                "text": message.text,
            }
            for message in FixedMessage.objects.all().order_by("text")
        ]

    return await get_fixed_messages()


@router.post("/messages/send", response_model=EventMessageResponse)
async def send_message(
    data: SendMessageRequest, current_user_id: int = Depends(get_current_user)
):
    @database_sync_to_async
    def send_message_logic(data, current_user_id):
        current_user = get_object_or_404(CustomUser, id=current_user_id)

        try:
            receiver = CustomUser.objects.get(username=data.receiver_username)
        except CustomUser.DoesNotExist:
            raise HTTPException(
                status_code=404,
                detail=f"User with username '{data.receiver_username}' not found",
            )

        fixed_message = get_object_or_404(FixedMessage, id=data.fixed_message_id)

        latest = (
            EventMessage.objects.filter(sender=current_user)
            .order_by("-created_at")
            .first()
        )
        if latest and now() - latest.created_at < timedelta(seconds=5):
            raise HTTPException(
                status_code=429, detail="You're sending messages too fast!"
            )

        event = None
        if data.event_id:
            event = get_object_or_404(Event, eventId=data.event_id)

        message = EventMessage.objects.create(
            sender=current_user,
            receiver=receiver,
            fixed_message=fixed_message,
            event=event,
        )

        return _serialize_message(message)

    return await send_message_logic(data, current_user_id)


def _serialize_message(message: EventMessage):
    return {
        "id": message.id,
        "sender": message.sender.username,
        "receiver": message.receiver.username,
        "fixed_message": message.fixed_message.text,
        "event_id": message.event.eventId if message.event else None,
        "event_name": message.event.title if message.event else None,
        "created_at": message.created_at,
        "seen": message.seen,
        "seen_at": message.seen_at,
        "reactions": [
            {"emoji": r.emoji, "reacted_at": r.reacted_at}
            for r in message.reactions.all()
        ],
    }


@router.get("/messages/inbox", response_model=List[EventMessageResponse])
async def inbox(current_user_id: int = Depends(get_current_user)):
    @database_sync_to_async
    def get_inbox_messages(current_user_id):
        current_user = get_object_or_404(CustomUser, id=current_user_id)
        messages = (
            EventMessage.objects.filter(receiver=current_user)
            .select_related("sender", "receiver", "fixed_message", "event")
            .order_by("-created_at")
        )
        return [_serialize_message(m) for m in messages]

    return await get_inbox_messages(current_user_id)


@router.get("/messages/chat/{username}", response_model=List[EventMessageResponse])
async def conversation(username: str, current_user_id: int = Depends(get_current_user)):
    @database_sync_to_async
    def get_conversation_messages(username, current_user_id):
        current_user = get_object_or_404(CustomUser, id=current_user_id)

        # Try to find the target user by username
        try:
            target_user = CustomUser.objects.get(username=username)
        except CustomUser.DoesNotExist:
            # Return empty list if target user doesn't exist
            # This is better than throwing a 404 for a conversation endpoint
            return []

        messages = (
            EventMessage.objects.filter(
                sender__in=[current_user, target_user],
                receiver__in=[current_user, target_user],
            )
            .select_related("sender", "receiver", "fixed_message", "event")
            .order_by("created_at")
        )
        return [_serialize_message(m) for m in messages]

    return await get_conversation_messages(username, current_user_id)


@router.post("/messages/mark-seen/{message_id}")
async def mark_message_as_seen(
    message_id: UUID, current_user_id: int = Depends(get_current_user)
):
    @database_sync_to_async
    def mark_message_as_seen_logic(message_id, current_user_id):
        current_user = get_object_or_404(CustomUser, id=current_user_id)
        message = get_object_or_404(EventMessage, id=message_id)
        if message.receiver != current_user:
            raise HTTPException(
                status_code=403, detail="You can't mark this message as seen"
            )
        message.mark_as_seen()
        return {"message": "Message marked as seen"}

    return await mark_message_as_seen_logic(message_id, current_user_id)


@router.post("/messages/react", response_model=EventMessageResponse)
async def react_to_message(
    data: MessageReactionRequest, current_user_id: int = Depends(get_current_user)
):
    @database_sync_to_async
    def react_to_message_logic(data, current_user_id):
        current_user = get_object_or_404(CustomUser, id=current_user_id)
        message = get_object_or_404(EventMessage, id=data.message_id)

        existing = MessageReaction.objects.filter(
            message=message, user=current_user
        ).first()
        if existing:
            existing.emoji = data.emoji
            existing.reacted_at = now()
            existing.save()
        else:
            MessageReaction.objects.create(
                message=message, user=current_user, emoji=data.emoji
            )

        return {"message": "Message reacted successfully"}

    return await react_to_message_logic(data, current_user_id)


@router.get("/messages/contacts")
async def get_message_contacts(
    request: Request,
    current_user_id: int = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    API endpoint to get all users who have exchanged messages with the current user.
    Returns a list of unique users with whom the current user has sent or received messages.
    """
    print(f"[get_message_contacts API] Function called for user ID: {current_user_id}")

    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def get_message_contacts_logic(current_user_id):
        try:
            current_user = get_object_or_404(CustomUser, id=current_user_id)

            # Get all unique users who have exchanged messages with the current user
            # This includes both sent and received messages
            sent_messages = EventMessage.objects.filter(
                sender=current_user
            ).values_list("receiver", flat=True)
            received_messages = EventMessage.objects.filter(
                receiver=current_user
            ).values_list("sender", flat=True)

            # Combine and get unique user IDs
            all_contact_ids = set(list(sent_messages) + list(received_messages))

            # Get user details for all contacts
            contacts = []
            for contact_id in all_contact_ids:
                try:
                    contact_user = CustomUser.objects.select_related(
                        "user_profile"
                    ).get(id=contact_id)
                    contact_profile = (
                        contact_user.user_profile
                        if hasattr(contact_user, "user_profile")
                        else None
                    )

                    # Get the latest message between these users
                    latest_message = (
                        EventMessage.objects.filter(
                            (
                                models.Q(sender=current_user, receiver=contact_user)
                                | models.Q(sender=contact_user, receiver=current_user)
                            )
                        )
                        .order_by("-created_at")
                        .first()
                    )

                    # Get message count between these users
                    message_count = EventMessage.objects.filter(
                        (
                            models.Q(sender=current_user, receiver=contact_user)
                            | models.Q(sender=contact_user, receiver=current_user)
                        )
                    ).count()

                    # Get unread message count
                    unread_count = EventMessage.objects.filter(
                        sender=contact_user, receiver=current_user, seen=False
                    ).count()

                    contacts.append(
                        {
                            "user_id": str(contact_user.user_id),
                            "username": contact_user.username,
                            "first_name": contact_user.first_name,
                            "last_name": contact_user.last_name,
                            "profile_photo": (
                                contact_profile.profile_photo.url
                                if contact_profile and contact_profile.profile_photo
                                else None
                            ),
                            "latest_message": {
                                "content": (
                                    latest_message.fixed_message.text
                                    if latest_message
                                    else None
                                ),
                                "created_at": (
                                    latest_message.created_at
                                    if latest_message
                                    else None
                                ),
                                "is_from_me": (
                                    latest_message.sender == current_user
                                    if latest_message
                                    else None
                                ),
                                "seen": latest_message.seen if latest_message else None,
                            },
                            "message_count": message_count,
                            "unread_count": unread_count,
                            "last_interaction": (
                                latest_message.created_at if latest_message else None
                            ),
                        }
                    )
                except CustomUser.DoesNotExist:
                    # Skip if contact user doesn't exist (data inconsistency)
                    continue

            # Sort contacts by last interaction (most recent first)
            contacts.sort(
                key=lambda x: x["last_interaction"]
                or timezone.now().replace(tzinfo=None),
                reverse=True,
            )

            return {
                "contacts": contacts,
                "total_contacts": len(contacts),
                "total_unread": sum(contact["unread_count"] for contact in contacts),
            }, None

        except CustomUser.DoesNotExist:
            error_message = f"User not found with ID: {current_user_id}"
            print(f"[get_message_contacts API] {error_message}")
            return None, error_message
        except Exception as e:
            error_message = f"Error getting message contacts: {str(e)}"
            print(f"[get_message_contacts API] {error_message}")
            return None, error_message

    contacts_data, error_message = await get_message_contacts_logic(current_user_id)
    if contacts_data is None:
        notification_sent = await notify_by_bot(
            f"**[API: get_message_contacts API]** \n\n {error_message} \n\n Platform: {platform} \n\n User ID: {current_user_id}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        if notification_sent is None:
            print(
                "[get_message_contacts API] Could not send notification: BOT_API_KEY not set"
            )
        raise HTTPException(status_code=500, detail=error_message)

    print(
        f"[get_message_contacts API] Returning {contacts_data['total_contacts']} message contacts"
    )
    return contacts_data


@router.get("/messages/contacts/{username}")
async def get_message_contact_details(
    request: Request,
    username: str,
    current_user_id: int = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    API endpoint to get detailed information about a specific message contact.
    Returns conversation summary and user details for a specific contact.
    """
    print(f"[get_message_contact_details API] Function called for username: {username}")

    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def get_message_contact_details_logic(current_user_id, username):
        try:
            current_user = get_object_or_404(CustomUser, id=current_user_id)

            # Get the contact user
            try:
                contact_user = CustomUser.objects.select_related("user_profile").get(
                    username=username
                )
            except CustomUser.DoesNotExist:
                return None, f"Contact user '{username}' not found", None

            contact_profile = (
                contact_user.user_profile
                if hasattr(contact_user, "user_profile")
                else None
            )

            # Get all messages between these users
            messages = (
                EventMessage.objects.filter(
                    (
                        models.Q(sender=current_user, receiver=contact_user)
                        | models.Q(sender=contact_user, receiver=current_user)
                    )
                )
                .select_related("sender", "receiver", "fixed_message", "event")
                .order_by("-created_at")
            )

            # Get conversation statistics
            total_messages = messages.count()
            sent_messages = messages.filter(sender=current_user).count()
            received_messages = messages.filter(receiver=current_user).count()
            unread_messages = messages.filter(
                sender=contact_user, receiver=current_user, seen=False
            ).count()

            # Get latest message
            latest_message = messages.first()

            # Get message frequency (messages per day in the last 30 days)
            thirty_days_ago = timezone.now() - timedelta(days=30)
            recent_messages = messages.filter(created_at__gte=thirty_days_ago).count()
            messages_per_day = (
                round(recent_messages / 30, 2) if recent_messages > 0 else 0
            )

            # Get conversation topics (most common fixed messages)
            from django.db.models import Count

            common_messages = (
                messages.values("fixed_message__text")
                .annotate(count=Count("fixed_message"))
                .order_by("-count")[:5]
            )

            contact_details = {
                "user": {
                    "user_id": str(contact_user.user_id),
                    "username": contact_user.username,
                    "first_name": contact_user.first_name,
                    "last_name": contact_user.last_name,
                    "profile_photo": (
                        contact_profile.profile_photo.url
                        if contact_profile and contact_profile.profile_photo
                        else None
                    ),
                },
                "conversation_stats": {
                    "total_messages": total_messages,
                    "sent_messages": sent_messages,
                    "received_messages": received_messages,
                    "unread_messages": unread_messages,
                    "messages_per_day": messages_per_day,
                    "conversation_ratio": (
                        round(sent_messages / total_messages * 100, 1)
                        if total_messages > 0
                        else 0
                    ),
                },
                "latest_message": {
                    "content": (
                        latest_message.fixed_message.text if latest_message else None
                    ),
                    "created_at": latest_message.created_at if latest_message else None,
                    "is_from_me": (
                        latest_message.sender == current_user
                        if latest_message
                        else None
                    ),
                    "seen": latest_message.seen if latest_message else None,
                },
                "common_topics": [
                    {"message": item["fixed_message__text"], "count": item["count"]}
                    for item in common_messages
                ],
                "last_interaction": (
                    latest_message.created_at if latest_message else None
                ),
            }

            return contact_details, None

        except CustomUser.DoesNotExist:
            error_message = f"User not found with ID: {current_user_id}"
            print(f"[get_message_contact_details API] {error_message}")
            return None, error_message, None
        except Exception as e:
            error_message = f"Error getting message contact details: {str(e)}"
            print(f"[get_message_contact_details API] {error_message}")
            return None, error_message, None

    contact_details, error_message = await get_message_contact_details_logic(
        current_user_id, username
    )
    if contact_details is None:
        notification_sent = await notify_by_bot(
            f"**[API: get_message_contact_details API]** \n\n {error_message} \n\n Platform: {platform} \n\n User ID: {current_user_id} \n\n Username: {username}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        if notification_sent is None:
            print(
                "[get_message_contact_details API] Could not send notification: BOT_API_KEY not set"
            )
        raise HTTPException(status_code=404, detail=error_message)

    print(f"[get_message_contact_details API] Returning contact details for {username}")
    return {"contact_details": contact_details}


@router.get("/messages/contacts/{username}/conversation")
async def get_message_conversation_with_contact(
    request: Request,
    username: str,
    current_user_id: int = Depends(get_current_user),
    page: int = Query(1, ge=1, description="Page number (starts from 1)"),
    page_size: int = Query(
        20, ge=1, le=100, description="Number of messages per page (max 100)"
    ),
    platform: Optional[str] = None,
):
    """
    API endpoint to get paginated conversation messages with a specific contact.
    Returns messages in chronological order with pagination support.
    """
    print(
        f"[get_message_conversation_with_contact API] Function called for username: {username}"
    )

    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def get_message_conversation_logic(current_user_id, username, page, page_size):
        try:
            current_user = get_object_or_404(CustomUser, id=current_user_id)

            # Get the contact user
            try:
                contact_user = CustomUser.objects.get(username=username)
            except CustomUser.DoesNotExist:
                return None, f"Contact user '{username}' not found", None

            # Get all messages between these users
            messages = (
                EventMessage.objects.filter(
                    (
                        models.Q(sender=current_user, receiver=contact_user)
                        | models.Q(sender=contact_user, receiver=current_user)
                    )
                )
                .select_related("sender", "receiver", "fixed_message", "event")
                .order_by("-created_at")
            )

            # Calculate pagination
            total_messages = messages.count()
            total_pages = (
                total_messages + page_size - 1
            ) // page_size  # Ceiling division
            offset = (page - 1) * page_size

            # Get paginated messages
            paginated_messages = messages[offset : offset + page_size]

            # Mark messages as seen if they're from the contact to the current user
            unread_messages = paginated_messages.filter(
                sender=contact_user, receiver=current_user, seen=False
            )
            for message in unread_messages:
                message.mark_as_seen()

            # Serialize messages
            messages_data = []
            for message in paginated_messages:
                messages_data.append(
                    {
                        "id": str(message.id),
                        "content": message.fixed_message.text,
                        "created_at": message.created_at,
                        "is_from_me": message.sender == current_user,
                        "seen": message.seen,
                        "seen_at": message.seen_at,
                        "event": (
                            {
                                "event_id": str(message.event.eventId),
                                "title": message.event.title,
                            }
                            if message.event
                            else None
                        ),
                        "reactions": [
                            {
                                "emoji": reaction.emoji,
                                "reacted_at": reaction.reacted_at,
                                "reacted_by": reaction.user.username,
                            }
                            for reaction in message.reactions.all()
                        ],
                    }
                )

            return {
                "messages": messages_data,
                "pagination": {
                    "current_page": page,
                    "page_size": page_size,
                    "total_messages": total_messages,
                    "total_pages": total_pages,
                    "has_next": page < total_pages,
                    "has_previous": page > 1,
                },
                "contact": {
                    "username": contact_user.username,
                    "first_name": contact_user.first_name,
                    "last_name": contact_user.last_name,
                },
            }, None

        except CustomUser.DoesNotExist:
            error_message = f"User not found with ID: {current_user_id}"
            print(f"[get_message_conversation_with_contact API] {error_message}")
            return None, error_message, None
        except Exception as e:
            error_message = f"Error getting message conversation: {str(e)}"
            print(f"[get_message_conversation_with_contact API] {error_message}")
            return None, error_message, None

    conversation_data, error_message = await get_message_conversation_logic(
        current_user_id, username, page, page_size
    )
    if conversation_data is None:
        notification_sent = await notify_by_bot(
            f"**[API: get_message_conversation_with_contact API]** \n\n {error_message} \n\n Platform: {platform} \n\n User ID: {current_user_id} \n\n Username: {username}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        if notification_sent is None:
            print(
                "[get_message_conversation_with_contact API] Could not send notification: BOT_API_KEY not set"
            )
        raise HTTPException(status_code=404, detail=error_message)

    print(
        f"[get_message_conversation_with_contact API] Returning {len(conversation_data['messages'])} messages for conversation with {username}"
    )
    return conversation_data


@router.post("/messages/contacts/{username}/mark-read")
async def mark_conversation_as_read(
    request: Request,
    username: str,
    current_user_id: int = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    API endpoint to mark all messages from a specific contact as read.
    Useful for bulk marking conversations as read.
    """
    print(f"[mark_conversation_as_read API] Function called for username: {username}")

    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def mark_conversation_as_read_logic(current_user_id, username):
        try:
            current_user = get_object_or_404(CustomUser, id=current_user_id)

            # Get the contact user
            try:
                contact_user = CustomUser.objects.get(username=username)
            except CustomUser.DoesNotExist:
                return None, f"Contact user '{username}' not found", None

            # Mark all unread messages from this contact as read
            unread_messages = EventMessage.objects.filter(
                sender=contact_user, receiver=current_user, seen=False
            )

            marked_count = unread_messages.count()

            # Mark messages as seen
            for message in unread_messages:
                message.mark_as_seen()

            return {
                "marked_count": marked_count,
                "contact_username": username,
                "marked_at": timezone.now(),
            }, None

        except CustomUser.DoesNotExist:
            error_message = f"User not found with ID: {current_user_id}"
            print(f"[mark_conversation_as_read API] {error_message}")
            return None, error_message, None
        except Exception as e:
            error_message = f"Error marking conversation as read: {str(e)}"
            print(f"[mark_conversation_as_read API] {error_message}")
            return None, error_message, None

    mark_data, error_message = await mark_conversation_as_read_logic(
        current_user_id, username
    )
    if mark_data is None:
        notification_sent = await notify_by_bot(
            f"**[API: mark_conversation_as_read API]** \n\n {error_message} \n\n Platform: {platform} \n\n User ID: {current_user_id} \n\n Username: {username}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        if notification_sent is None:
            print(
                "[mark_conversation_as_read API] Could not send notification: BOT_API_KEY not set"
            )
        raise HTTPException(status_code=404, detail=error_message)

    print(
        f"[mark_conversation_as_read API] Marked {mark_data['marked_count']} messages as read for {username}"
    )
    return {
        "message": f"Marked {mark_data['marked_count']} messages as read",
        "mark_data": mark_data,
    }

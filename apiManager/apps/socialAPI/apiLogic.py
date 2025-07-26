import asyncio


from typing import Optional, List
from datetime import timedelta
from channels.db import database_sync_to_async
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    status,
    Query,
    UploadFile,
    File,
    Form,
    Body,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
import bleach
import os
from user_agents import parse as parse_user_agent
from django.db.models import Q, Prefetch
from django.db import transaction
from django.db import models
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
    CrewMessage,
    CrewSharedEvent,
    CrewJoinRequest,
)
from socialApp.forms import (
    SurfPostForm,
    createCrewForm,
    EditCrewImageForm,
    EditCrewNameForm,
    EditCrewBioForm,
)
from eventTicketsApp.views import generateTicket
from apiManager.algorithms.suggested_friends import get_suggested_friends
from socialGraphManagement.graph.crew_graph import suggest_crews_for_user
from django.db import IntegrityError
from apiManager.utilities.notify_by_bot import notify_by_bot

from apiManager.dependencies import get_current_user
from authenticationApp.models import CustomUser
from uuid import UUID
import logging

logger = logging.getLogger(__name__)

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

from apiManager.notifications.notification import send_notification
from apiManager.notifications.crew_ws import crew_manager


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


@router.get("/crew/{crew_id}/info")
async def get_crew_info(
    crew_id: str,
    caller_user_id: Optional[int] = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    Get basic info about a crew by crew_id.
    """

    @database_sync_to_async
    def get_crew():
        from uuid import UUID

        try:
            crew = Crew.objects.select_related("created_by").get(crewId=UUID(crew_id))
            creator = crew.created_by
            return {
                "crewId": str(crew.crewId),
                "name": crew.name,
                "bio": crew.bio,
                "created_at": crew.created_at,
                "crew_image": crew.crew_image.url if crew.crew_image else None,
                "created_by": {
                    "user_id": str(creator.user_id),
                    "username": creator.username,
                    "first_name": creator.first_name,
                    "last_name": creator.last_name,
                },
            }, None
        except Crew.DoesNotExist:
            return None, "Crew not found."
        except Exception as e:
            return None, str(e)

    crew_data, error = await get_crew()
    if crew_data is None:
        raise HTTPException(status_code=404, detail=error or "Crew not found.")
    return {"crew": crew_data}


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


@router.get("/get_all_user_crews")
async def get_all_user_crews(
    request: Request,
    caller_user_id: Optional[int] = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    API endpoint to retrieve all crews a user is in with crew ID, name, and member count.
    """
    print(f"[get_all_user_crews API] Function called for user ID: {caller_user_id}")

    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def get_all_user_crews_data(caller_user_id):
        try:
            user = CustomUser.objects.get(id=caller_user_id)

            # Get all crews the user is a member of
            crew_memberships = CrewMember.objects.filter(user=user).select_related(
                "crew", "crew__created_by"
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

            return crews_data, None
        except CustomUser.DoesNotExist:
            error_message = f"User not found with ID: {caller_user_id}"
            print(f"[get_all_user_crews API] {error_message}")
            return None, error_message
        except Exception as e:
            error_message = f"Error retrieving user crews: {str(e)}"
            print(f"[get_all_user_crews API] {error_message}")
            return None, error_message

    try:
        crews_data, error_message = await get_all_user_crews_data(caller_user_id)
        if crews_data is None:
            notification_sent = await notify_by_bot(
                f"**[API: get_all_user_crews API]** \n\n {error_message} \n\n Platform: {platform} \n\n User ID: {caller_user_id}",
                platform or "Unknown",
                "ERROR",
                device_info,
            )
            if notification_sent is None:
                print(
                    "[get_all_user_crews API] Could not send notification: BOT_API_KEY not set"
                )
            raise HTTPException(status_code=500, detail=error_message)

        print(
            f"[get_all_user_crews API] Returning {len(crews_data)} crews for user_id: {caller_user_id}"
        )
        return {"crews": crews_data}
    except Exception as e:
        if not isinstance(e, HTTPException):
            error_trace = traceback.format_exc()
            print(
                f"[get_all_user_crews API] Unhandled exception: {str(e)}\n{error_trace}"
            )
            await notify_by_bot(
                f"**[API: get_all_user_crews API]** \n\n Unhandled exception: user_id={caller_user_id}, error={str(e)} \n\n Platform: {platform}",
                platform or "Unknown",
                "ERROR",
                device_info,
            )
            raise HTTPException(status_code=500, detail="Internal server error")
        raise e


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
                    None,
                    None,
                    None,
                )
            # Get sender user
            sender_user = CustomUser.objects.get(id=sender_user_id)

            # Check if trying to send request to self
            if receiver_username == sender_user.username:
                return (
                    None,
                    "You cannot send a friend request to yourself.",
                    None,
                    None,
                    None,
                    None,
                )

            # Get receiver user profile - use full Discord-style username
            try:
                receiver_user_profile = UserProfile.objects.select_related("user").get(
                    user__username=receiver_username
                )
                receiver_user = receiver_user_profile.user
            except UserProfile.DoesNotExist:
                return None, "User not found.", None, None, None, None

            # Check if already friends
            if sender_user.user_profile.is_friends_with(receiver_user):
                return (
                    None,
                    "You are already friends with this user.",
                    None,
                    None,
                    None,
                    None,
                )

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
                            None,
                            None,
                            None,
                        )
                    else:
                        return (
                            None,
                            f"{receiver_username} has already sent you a friend request. Check your notifications to respond.",
                            None,
                            None,
                            None,
                            None,
                        )
                else:  # status is 'accepted'
                    # Double-check if friendship actually exists
                    if sender_user.user_profile.is_friends_with(receiver_user):
                        return (
                            None,
                            "You are already friends with this user.",
                            None,
                            None,
                            None,
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
                                None,
                                None,
                                None,
                            )
                        except Exception as e:
                            print(
                                f"[send_friend_request API] Error fixing friendship relationship: {str(e)}"
                            )
                            # If fixing fails, allow new request (treat as if no accepted request exists)
                            pass

                # Note: Previously we tried to reuse canceled requests, but now they are deleted
                # so we always create a new friend request
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
                    return None, error_message, None, None, None, None

            # Return receiver info for notification
            return (
                {
                    "status": friend_request.status,
                    "created_at": friend_request.created_at,
                },
                "Friend request sent successfully.",
                None,
                receiver_user.user_id,
                sender_user.username,
                sender_user.first_name,  # Include sender's first name
            )

        except CustomUser.DoesNotExist:
            error_message = f"Sender user not found with ID: {sender_user_id}"
            print(f"[send_friend_request API] {error_message}")
            return None, error_message, None, None, None, None
        except Exception as e:
            error_message = f"Error sending friend request: {str(e)}"
            print(f"[send_friend_request API] {error_message}")
            return None, error_message, None, None, None, None

    (
        friend_request_data,
        success_message,
        error_message,
        receiver_user_id,
        sender_username,
        sender_first_name,
    ) = await send_friend_request_logic(caller_user_id, receiver_username)

    # Send notification if friend request was successful
    if friend_request_data is not None and receiver_user_id and sender_username:
        # Use the first name retrieved from the database function, with fallbacks
        notification_first_name = (
            sender_first_name
            if sender_first_name and sender_first_name.strip()
            else sender_username
        )

        # Ensure we have a valid name for the notification
        if not notification_first_name or notification_first_name.strip() == "":
            notification_first_name = "Someone"

        notification_message = (
            f"You have a new friend request from {notification_first_name}"
        )
        await send_notification(
            receiver_user_id,
            notification_message,
            "Friend Request",
            navigate_to="friend_requests",
            params={
                "request_id": str(friend_request_data.get("request_id", "")),
                "sender_username": sender_username,
                "request_type": "friend_request",
                "status": "pending",
            },
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

            # Store info before deletion
            request_info = {
                "request_id": str(friend_request.requestId),
                "canceled_at": timezone.now(),
            }

            # Delete the friend request (no need to keep it after cancellation)
            friend_request.delete()

            return (
                {
                    "status": "canceled_and_deleted",
                    "canceled_at": request_info["canceled_at"],
                    "request_id": request_info["request_id"],
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

                # Store info before deletion
                request_info = {
                    "request_id": str(friend_request.requestId),
                    "accepted_at": timezone.now(),
                }

                # Add both users to each other's friends list
                receiver_user.user_profile.friends.add(sender_user_profile)  # type: ignore[attr-defined]
                sender_user_profile.friends.add(receiver_user.user_profile)  # type: ignore[attr-defined]

                # Delete the friend request (no need to keep it after acceptance)
                friend_request.delete()

            return (
                {
                    "status": "accepted_and_deleted",
                    "accepted_at": request_info["accepted_at"],
                    "friendship_established": True,
                    "request_id": request_info["request_id"],
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

    # Send notification if friend request was accepted successfully
    if friend_request_data is not None and sender_username:
        # Get receiver's (current user's) first name for the notification message
        receiver_first_name = None
        try:

            @database_sync_to_async
            def get_receiver_info(user_id):
                receiver_user = CustomUser.objects.get(id=user_id)
                return receiver_user.first_name, receiver_user.user_id

            receiver_first_name, receiver_user_id = await get_receiver_info(
                caller_user_id
            )
        except Exception:
            receiver_first_name = "Someone"  # fallback

        # Get sender's user_id for notification
        sender_user_id = None
        try:

            @database_sync_to_async
            def get_sender_user_id(username):
                sender_user = CustomUser.objects.get(username=username)
                return sender_user.user_id

            sender_user_id = await get_sender_user_id(sender_username)
        except Exception:
            print(
                f"[accept_friend_request API] Could not get sender user_id for {sender_username}"
            )

        if sender_user_id:
            notification_message = f"{receiver_first_name} accepted your friend request"
            await send_notification(
                sender_user_id,
                notification_message,
                "Friend Request Accepted",
                navigate_to="friend_requests",
                params={
                    "accepter_username": sender_username,
                    "request_type": "friend_request_accepted",
                    "status": "accepted",
                    "receiver_user_id": (
                        str(receiver_user_id) if receiver_user_id else None
                    ),
                },
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

                # Note: Previously we would find and delete accepted friend requests,
                # but now they are deleted immediately when accepted, so this will not find any
                friend_request = FriendRequest.objects.filter(
                    Q(sender=caller_user, receiver=friend_user)
                    | Q(sender=friend_user, receiver=caller_user),
                    status="accepted",
                ).first()

                request_info = None
                if friend_request:
                    # Store request info before deletion (unlikely to be found)
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
    Returns friend requests with status pending only (accepted, declined, and canceled requests are deleted).
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

            # Get sent friend requests (only pending remain, others are deleted)
            sent_requests = (
                FriendRequest.objects.filter(sender=user, status="pending")
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
    Returns friend requests with status pending only (accepted, declined, and canceled requests are deleted).
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

            # Get received friend requests (only pending remain, others are deleted)
            received_requests = (
                FriendRequest.objects.filter(receiver=user, status="pending")
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
    Returns crew invites with status pending only (accepted, declined, and canceled invites are deleted).
    """
    print(f"[get_sent_crew_invites API] Function called for user ID: {caller_user_id}")

    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def get_sent_crew_invites_data(caller_user_id):
        try:
            user = CustomUser.objects.get(id=caller_user_id)

            # Get sent crew invites (only pending remain, others are deleted)
            sent_invites = (
                CrewRequest.objects.filter(sender=user, status="pending")
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
                            "crew_image": (
                                invite.crew.crew_image.url
                                if invite.crew.crew_image
                                else None
                            ),
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
    Returns crew invites with status pending only (accepted, declined, and canceled invites are deleted).
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

            # Get received crew invites (only pending remain, others are deleted)
            received_invites = (
                CrewRequest.objects.filter(receiver=user, status="pending")
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
                            "crew_image": (
                                invite.crew.crew_image.url
                                if invite.crew.crew_image
                                else None
                            ),
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


async def send_crew_invite_accepted_notification(request_id, accepter_user_id):
    """Send notification to all crew members when their invite is accepted."""
    try:

        @database_sync_to_async
        def get_crew_invite_info(request_id, accepter_user_id):
            try:
                crew_request = CrewRequest.objects.select_related(
                    "sender", "receiver", "crew"
                ).get(requestId=request_id)

                accepter = CustomUser.objects.get(id=accepter_user_id)

                # Get all crew members (including creator and admins)
                crew_members = CrewMember.objects.filter(
                    crew=crew_request.crew
                ).select_related("user")

                member_ids = [
                    crew_request.crew.created_by.user_id
                ]  # Always include creator
                member_ids.extend([member.user.user_id for member in crew_members])
                member_ids = list(set(member_ids))  # Remove duplicates

                # Don't notify the accepter themselves
                member_ids = [uid for uid in member_ids if uid != accepter.user_id]

                return {
                    "member_user_ids": member_ids,
                    "accepter_name": accepter.first_name or accepter.username,
                    "crew_name": crew_request.crew.name,
                    "crew_id": str(crew_request.crew.crewId),
                }
            except Exception as e:
                print(
                    f"[send_crew_invite_accepted_notification] Error getting invite info: {str(e)}"
                )
                return None

        invite_info = await get_crew_invite_info(request_id, accepter_user_id)
        if not invite_info:
            return

        notification_title = "Crew Invite Accepted!"
        notification_message = f"{invite_info['accepter_name']} joined your crew {invite_info['crew_name']}"
        navigate_to = "crew_details"
        params = {
            "crew_id": invite_info["crew_id"],
            "crew_name": invite_info["crew_name"],
            "accepter_name": invite_info["accepter_name"],
            "page": "crew_details",
            "target_screen": f"crew_details/{invite_info['crew_id']}",
            "notification_type": "crew_invite_accepted",
        }

        # Send notification to all crew members
        for member_user_id in invite_info["member_user_ids"]:
            try:
                await send_notification(
                    member_user_id,
                    notification_message,
                    notification_title,
                    navigate_to=navigate_to,
                    params=params,
                )
                print(
                    f"[send_crew_invite_accepted_notification] Sent notification to crew member"
                )
            except Exception as e:
                print(
                    f"[send_crew_invite_accepted_notification] Error sending to crew member: {str(e)}"
                )

    except Exception as e:
        print(f"[send_crew_invite_accepted_notification] Error: {str(e)}")


async def send_vote_notification(post_id, voter_user_id, vote_value):
    """Send notification to post creator when someone votes on their post."""
    try:

        @database_sync_to_async
        def get_vote_notification_info(post_id, voter_user_id):
            try:
                post = SurfPost.objects.select_related("user", "event").get(
                    surfId=post_id
                )

                voter = CustomUser.objects.get(id=voter_user_id)

                # Don't notify if user voted on their own post
                if post.user.id == voter_user_id:
                    return None

                vote_type = "tide up" if vote_value == 1 else "tide down"

                return {
                    "post_creator_user_id": post.user.user_id,
                    "voter_name": voter.first_name or voter.username,
                    "vote_type": vote_type,
                    "post_content_preview": (
                        post.content[:30] + "..."
                        if len(post.content) > 30
                        else post.content
                    ),
                    "event_title": post.event.title,
                    "post_id": str(post.surfId),
                }
            except Exception as e:
                print(f"[get_vote_notification_info] Error: {str(e)}")
                return None

        vote_info = await get_vote_notification_info(post_id, voter_user_id)
        if not vote_info:
            return

        notification_title = f"Someone voted on your post!"
        notification_message = (
            f"{vote_info['voter_name']} gave your post a {vote_info['vote_type']}"
        )
        navigate_to = "surf_post_details"
        params = {
            "post_id": vote_info["post_id"],
            "voter_name": vote_info["voter_name"],
            "vote_type": vote_info["vote_type"],
            "post_preview": vote_info["post_content_preview"],
        }

        await send_notification(
            vote_info["post_creator_user_id"],
            notification_message,
            notification_title,
            navigate_to=navigate_to,
            params=params,
        )

        print(f"[send_vote_notification] Sent vote notification to post creator")

    except Exception as e:
        print(f"[send_vote_notification] Error: {str(e)}")


async def check_trending_post_notification(post_id, current_score):
    """Check if post has reached trending milestones and notify creator."""
    try:
        # Define trending milestones (you can adjust these values)
        milestones = [5, 10, 25, 50, 100]

        @database_sync_to_async
        def get_post_milestone_info(post_id, current_score):
            try:
                post = SurfPost.objects.select_related("user", "event").get(
                    surfId=post_id
                )

                # Check which milestone was just reached
                milestone_reached = None
                for milestone in milestones:
                    if current_score >= milestone:
                        milestone_reached = milestone
                    else:
                        break

                # Only notify at first time reaching milestone
                # We'll use the exact score to determine if this is the first time
                if milestone_reached and current_score == milestone_reached:
                    return {
                        "post_creator_user_id": post.user.user_id,
                        "milestone": milestone_reached,
                        "post_content_preview": (
                            post.content[:30] + "..."
                            if len(post.content) > 30
                            else post.content
                        ),
                        "event_title": post.event.title,
                        "post_id": str(post.surfId),
                    }
                return None
            except Exception as e:
                print(f"[get_post_milestone_info] Error: {str(e)}")
                return None

        milestone_info = await get_post_milestone_info(post_id, current_score)
        if not milestone_info:
            return

        notification_title = "🔥 Your post is trending!"
        notification_message = (
            f"Your post reached {milestone_info['milestone']} votes! Keep it up!"
        )
        navigate_to = "surf_post_details"
        params = {
            "post_id": milestone_info["post_id"],
            "milestone": milestone_info["milestone"],
            "post_preview": milestone_info["post_content_preview"],
        }

        await send_notification(
            milestone_info["post_creator_user_id"],
            notification_message,
            notification_title,
            navigate_to=navigate_to,
            params=params,
        )

        print(
            f"[check_trending_post_notification] Sent trending notification for milestone {milestone_info['milestone']}"
        )

    except Exception as e:
        print(f"[check_trending_post_notification] Error: {str(e)}")


async def send_crew_join_notification(crew_id, new_member_user_id):
    """Send notification to crew creator/admins when someone joins."""
    try:

        @database_sync_to_async
        def get_crew_notification_info(crew_id, new_member_user_id):
            try:
                crew = Crew.objects.select_related("created_by").get(crewId=crew_id)
                new_member = CustomUser.objects.get(id=new_member_user_id)

                # Get crew admins (including creator)
                admins = CrewMember.objects.filter(
                    crew=crew, is_admin=True
                ).select_related("user")

                admin_ids = [crew.created_by.user_id]  # Always include creator
                admin_ids.extend([admin.user.user_id for admin in admins])
                admin_ids = list(set(admin_ids))  # Remove duplicates

                # Don't notify the new member themselves
                admin_ids = [uid for uid in admin_ids if uid != new_member.user_id]

                return {
                    "admin_user_ids": admin_ids,
                    "new_member_name": new_member.first_name or new_member.username,
                    "crew_name": crew.name,
                    "crew_id": str(crew.crewId),
                }
            except Exception as e:
                print(f"[get_crew_notification_info] Error: {str(e)}")
                return None

        crew_info = await get_crew_notification_info(crew_id, new_member_user_id)
        if not crew_info:
            return

        notification_title = "New Crew Member!"
        notification_message = (
            f"{crew_info['new_member_name']} joined {crew_info['crew_name']}"
        )
        navigate_to = "crew_details"
        params = {
            "crew_id": crew_info["crew_id"],
            "crew_name": crew_info["crew_name"],
            "new_member_name": crew_info["new_member_name"],
            "page": "crew_details",
            "target_screen": f"crew_details/{crew_info['crew_id']}",
            "notification_type": "crew_member_joined",
        }

        # Send notification to all admins
        for admin_user_id in crew_info["admin_user_ids"]:
            try:
                await send_notification(
                    admin_user_id,
                    notification_message,
                    notification_title,
                    navigate_to=navigate_to,
                    params=params,
                )
                print(f"[send_crew_join_notification] Sent notification to admin")
            except Exception as e:
                print(f"[send_crew_join_notification] Error sending to admin: {str(e)}")

    except Exception as e:
        print(f"[send_crew_join_notification] Error: {str(e)}")


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

                # Store info before deletion
                invite_info = {
                    "request_id": str(crew_invite.requestId),
                    "accepted_at": timezone.now(),
                    "crew": {
                        "crew_id": str(crew_invite.crew.crewId),
                        "name": crew_invite.crew.name,
                    },
                }

                # Create crew membership
                CrewMember.objects.create(
                    user=receiver_user,
                    crew=crew_invite.crew,
                    is_admin=False,  # New members are not admins by default
                )

                # Delete the crew invite (no need to keep it after acceptance)
                crew_invite.delete()

            return (
                {
                    "status": "accepted_and_deleted",
                    "accepted_at": invite_info["accepted_at"],
                    "crew": invite_info["crew"],
                    "membership_established": True,
                    "request_id": invite_info["request_id"],
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

    # Send notifications for crew invite acceptance and new member joining
    await send_crew_invite_accepted_notification(request_id, caller_user_id)

    # Also notify crew admins about the new member
    if invite_data and "crew" in invite_data:
        crew_id = invite_data["crew"]["crew_id"]
        await send_crew_join_notification(crew_id, caller_user_id)

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

            # Store invite info before deletion
            invite_info = {
                "request_id": str(crew_invite.requestId),
                "crew_id": str(crew_invite.crew.crewId),
                "crew_name": crew_invite.crew.name,
                "sender_username": crew_invite.sender.username,
                "declined_at": timezone.now(),
            }

            # Delete the crew invite (no need to keep it after declining)
            crew_invite.delete()

            return (
                {
                    "status": "declined_and_deleted",
                    "declined_at": invite_info["declined_at"],
                    "crew": {
                        "crew_id": invite_info["crew_id"],
                        "name": invite_info["crew_name"],
                    },
                    "sender": {"username": invite_info["sender_username"]},
                    "request_id": invite_info["request_id"],
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

            # Store invite info before deleting
            invite_info = {
                "request_id": str(crew_invite.requestId),
                "crew_id": str(crew_invite.crew.crewId),
                "crew_name": crew_invite.crew.name,
                "receiver_username": crew_invite.receiver.username,
                "canceled_at": timezone.now(),
            }

            # Delete the invite from database
            crew_invite.delete()

            return (
                {
                    "request_id": invite_info["request_id"],
                    "canceled_at": invite_info["canceled_at"],
                    "crew": {
                        "crew_id": invite_info["crew_id"],
                        "name": invite_info["crew_name"],
                    },
                    "receiver": {"username": invite_info["receiver_username"]},
                },
                "Crew invite canceled and removed successfully.",
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
                        "crew_image": crew.crew_image.url if crew.crew_image else None,
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


@router.get("/create-crew/form-fields")
async def get_create_crew_form_fields(request: Request, platform: Optional[str] = None):
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    is_mobile = request.headers.get("X-Platform") == "mobile"

    FormClass = createCrewForm
    fields_info = get_form_fields(FormClass)
    return JSONResponse(content=fields_info, status_code=status.HTTP_200_OK)


@router.get("/edit-crew-image/form-fields")
async def get_edit_crew_image_form_fields(
    request: Request, platform: Optional[str] = None
):
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    is_mobile = request.headers.get("X-Platform") == "mobile"

    FormClass = EditCrewImageForm
    fields_info = get_form_fields(FormClass)
    return JSONResponse(content=fields_info, status_code=status.HTTP_200_OK)


@router.get("/edit-crew-name/form-fields")
async def get_edit_crew_name_form_fields(
    request: Request, platform: Optional[str] = None
):
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    is_mobile = request.headers.get("X-Platform") == "mobile"

    FormClass = EditCrewNameForm
    fields_info = get_form_fields(FormClass)
    return JSONResponse(content=fields_info, status_code=status.HTTP_200_OK)


@router.get("/edit-crew-bio/form-fields")
async def get_edit_crew_bio_form_fields(
    request: Request, platform: Optional[str] = None
):
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    is_mobile = request.headers.get("X-Platform") == "mobile"

    FormClass = EditCrewBioForm
    fields_info = get_form_fields(FormClass)
    return JSONResponse(content=fields_info, status_code=status.HTTP_200_OK)


@router.post("/crew/{crew_id}/edit-image")
async def edit_crew_image(
    request: Request,
    crew_id: str,
    crew_image: UploadFile = File(...),
    caller_user_id: Optional[int] = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    Edit crew image.
    """

    @database_sync_to_async
    def edit_crew_image_sync():
        from uuid import UUID

        try:
            crew = Crew.objects.get(crewId=UUID(crew_id))
            user = CustomUser.objects.get(id=caller_user_id)

            # Check if user is the crew creator
            if crew.created_by != user:
                return False, "Only the crew creator can edit the crew image."

            # Save the new image
            crew.crew_image.save(crew_image.filename, crew_image.file, save=True)
            return True, None
        except Crew.DoesNotExist:
            return False, "Crew not found."
        except CustomUser.DoesNotExist:
            return False, "User not found."
        except Exception as e:
            return False, f"Error updating crew image: {str(e)}"

    success, error_message = await edit_crew_image_sync()

    if not success:
        raise HTTPException(status_code=400, detail=error_message)

    return {"message": "Crew image updated successfully"}


@router.post("/crew/{crew_id}/edit-name")
async def edit_crew_name(
    request: Request,
    crew_id: str,
    name: str = Form(...),
    caller_user_id: Optional[int] = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    Edit crew name.
    """

    @database_sync_to_async
    def edit_crew_name_sync():
        from uuid import UUID

        try:
            crew = Crew.objects.get(crewId=UUID(crew_id))
            user = CustomUser.objects.get(id=caller_user_id)

            # Check if user is the crew creator
            if crew.created_by != user:
                return False, "Only the crew creator can edit the crew name."

            # Validate and update the name
            crew.name = name.strip()
            crew.save()
            return True, None
        except Crew.DoesNotExist:
            return False, "Crew not found."
        except CustomUser.DoesNotExist:
            return False, "User not found."
        except Exception as e:
            return False, f"Error updating crew name: {str(e)}"

    success, error_message = await edit_crew_name_sync()

    if not success:
        raise HTTPException(status_code=400, detail=error_message)

    return {"message": "Crew name updated successfully"}


@router.post("/crew/{crew_id}/edit-bio")
async def edit_crew_bio(
    request: Request,
    crew_id: str,
    bio: str = Form(...),
    caller_user_id: Optional[int] = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    Edit crew bio.
    """

    @database_sync_to_async
    def edit_crew_bio_sync():
        from uuid import UUID

        try:
            crew = Crew.objects.get(crewId=UUID(crew_id))
            user = CustomUser.objects.get(id=caller_user_id)

            # Check if user is the crew creator
            if crew.created_by != user:
                return False, "Only the crew creator can edit the crew bio."

            # Validate and update the bio
            crew.bio = bio.strip()
            crew.save()
            return True, None
        except Crew.DoesNotExist:
            return False, "Crew not found."
        except CustomUser.DoesNotExist:
            return False, "User not found."
        except Exception as e:
            return False, f"Error updating crew bio: {str(e)}"

    success, error_message = await edit_crew_bio_sync()

    if not success:
        raise HTTPException(status_code=400, detail=error_message)

    return {"message": "Crew bio updated successfully"}


@router.post("/crew/create")
async def create_crew(
    request: Request,
    name: str = Form(...),
    bio: str = Form(...),
    crew_image: Optional[UploadFile] = File(None),
    caller_user_id: Optional[int] = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    API endpoint to create a new crew.
    """
    if not caller_user_id:
        raise HTTPException(status_code=401, detail="Authentication required.")

    @database_sync_to_async
    def create_crew_sync():
        try:
            user = CustomUser.objects.get(id=caller_user_id)
            crew = Crew(name=name, bio=bio, created_by=user)
            if crew_image:
                crew.crew_image.save(crew_image.filename, crew_image.file, save=False)
            crew.save()
            # Add creator as admin member
            CrewMember.objects.create(crew=crew, user=user, is_admin=True)
            return crew
        except Exception as e:
            return str(e)

    result = await create_crew_sync()
    if isinstance(result, str):
        raise HTTPException(status_code=400, detail=f"Error creating crew: {result}")

    return {
        "crewId": str(result.crewId),
        "name": result.name,
        "bio": result.bio,
        "created_at": result.created_at,
        "crew_image": result.crew_image.url if result.crew_image else None,
    }


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
                "crew_image": (crew.crew_image.url if crew.crew_image else None),
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


async def send_surf_post_notifications(post_data, user_id, event_title):
    """
    Send push notifications to all friends when a surf post is created.
    """
    try:

        @database_sync_to_async
        def get_friends_for_notification(user_id):
            """Get all friends who should receive notifications for this surf post."""
            try:
                user = CustomUser.objects.get(id=user_id)
                user_profile = user.user_profile

                # Get all friends
                friends = user_profile.friends.all().select_related("user")

                friend_list = []
                for friend_profile in friends:
                    if friend_profile.user:
                        friend_list.append(
                            {
                                "user_id": friend_profile.user.user_id,
                                "username": friend_profile.user.username,
                            }
                        )

                return friend_list
            except Exception as e:
                print(f"[send_surf_post_notifications] Error getting friends: {str(e)}")
                return []

        # Get all friends
        friends = await get_friends_for_notification(user_id)

        if not friends:
            print(f"[send_surf_post_notifications] User has no friends to notify")
            return

        # Prepare notification data
        # Truncate content to include only first 50 characters for notification
        content_preview = post_data["content"][:50]
        if len(post_data["content"]) > 50:
            content_preview += "..."

        notification_title = (
            f"{await get_user_first_name(user_id)} posted about {event_title}"
        )
        notification_message = f"{content_preview}"
        navigate_to = "surf_post_details"
        params = {
            "post_id": str(post_data["post_id"]),
            "event_id": str(post_data["event_id"]),
            "content_preview": content_preview,
        }

        # Send notifications to all friends
        for friend in friends:
            try:
                await send_notification(
                    friend["user_id"],
                    notification_message,
                    notification_title,
                    navigate_to=navigate_to,
                    params=params,
                )
                print(
                    f"[send_surf_post_notifications] Sent notification to {friend['username']}"
                )
            except Exception as e:
                print(
                    f"[send_surf_post_notifications] Error sending notification to {friend['username']}: {str(e)}"
                )

        print(
            f"[send_surf_post_notifications] Total notifications sent: {len(friends)}"
        )

    except Exception as e:
        print(f"[send_surf_post_notifications] Error in notification process: {str(e)}")
        # Don't raise the exception as we don't want notification failures to prevent post creation


@database_sync_to_async
def get_user_first_name(user_id):
    """Get user's first name for notification message."""
    try:
        user = CustomUser.objects.get(id=user_id)
        return user.first_name or user.username
    except Exception:
        return "Someone"


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
                "event_title": event.title,  # Include event title for notifications
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

    # Send notifications to friends after successful post creation
    event_title = post_data.pop(
        "event_title"
    )  # Remove event_title from post_data before returning
    await send_surf_post_notifications(post_data, caller_user_id, event_title)

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

    # Send notification to post creator for any vote (new or update)
    if vote_data is not None:
        await send_vote_notification(data.post_id, caller_user_id, data.vote)

    # Check if post is trending (reaches popularity milestones)
    current_score = vote_data.get("score", 0)
    await check_trending_post_notification(data.post_id, current_score)

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


@router.get("/surf-posts/my-posts")
async def get_my_surf_posts(
    request: Request,
    caller_user_id: Optional[int] = Depends(get_current_user),
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
    API endpoint to get surf posts created by the current user with pagination and sorting support.
    """
    print(
        f"[get_my_surf_posts API] Function called with page: {page}, page_size: {page_size}"
    )

    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def get_my_surf_posts_logic(caller_user_id, page, page_size, sort_by, order):
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

            # Get total count of surf posts by the current user
            total_posts = SurfPost.objects.filter(user_id=caller_user_id).count()

            # Calculate pagination
            total_pages = (total_posts + page_size - 1) // page_size  # Ceiling division
            offset = (page - 1) * page_size

            # Get paginated surf posts by the current user with user and event information
            posts = (
                SurfPost.objects.filter(user_id=caller_user_id)
                .select_related("user", "user__user_profile", "event")
                .order_by(sort_field)[offset : offset + page_size]
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
                    "total_pages": total_pages,
                    "total_posts": total_posts,
                    "page_size": page_size,
                    "has_next": page < total_pages,
                    "has_previous": page > 1,
                },
            }, None
        except Exception as e:
            error_message = f"Error getting my surf posts: {str(e)}"
            print(f"[get_my_surf_posts API] {error_message}")
            return None, error_message

    posts_data, error_message = await get_my_surf_posts_logic(
        caller_user_id, page, page_size, sort_by, order
    )
    if posts_data is None:
        notification_sent = await notify_by_bot(
            f"**[API: get_my_surf_posts API]** \n\n {error_message} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        if notification_sent is None:
            print(
                "[get_my_surf_posts API] Could not send notification: BOT_API_KEY not set"
            )
        raise HTTPException(status_code=500, detail=error_message)

    print(f"[get_my_surf_posts API] Returning {len(posts_data['posts'])} surf posts")
    return posts_data


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


async def send_message_notification(receiver, sender, fixed_message, event):
    """
    Send push notification to receiver when they get a new message.
    """
    try:
        # Prepare notification data
        sender_name = sender.first_name or sender.username

        # Create message preview - limit to 50 characters
        message_preview = fixed_message.text[:50]
        if len(fixed_message.text) > 50:
            message_preview += "..."

        # Create notification title and message
        if event:
            notification_title = f"New message from {sender_name} about {event.title}"
            notification_message = f"{message_preview}"
        else:
            notification_title = f"New message from {sender_name}"
            notification_message = f"{message_preview}"

        navigate_to = "message_conversation"
        params = {
            "sender_username": sender.username,
            "sender_name": sender_name,
            "message_preview": message_preview,
            "event_id": str(event.eventId) if event else None,
            "event_title": event.title if event else None,
        }

        # Send notification to receiver
        await send_notification(
            receiver.user_id,
            notification_message,
            notification_title,
            navigate_to=navigate_to,
            params=params,
        )

        print(
            f"[send_message_notification] Sent message notification to {receiver.username}"
        )

    except Exception as e:
        print(f"[send_message_notification] Error sending notification: {str(e)}")
        # Don't raise the exception as we don't want notification failures to prevent message sending


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

        # Return message data and receiver info for notification
        return _serialize_message(message), receiver, current_user, fixed_message, event

    # Execute the send message logic
    message_data, receiver, sender, fixed_message, event = await send_message_logic(
        data, current_user_id
    )

    # Send notification to receiver after successful message creation
    await send_message_notification(receiver, sender, fixed_message, event)

    return message_data


def _serialize_message(message: EventMessage):
    return {
        "id": message.id,
        "sender": message.sender.username,
        "receiver": message.receiver.username,
        "fixed_message": message.fixed_message.text,
        "event_id": message.event.eventId if message.event else None,
        "event_name": message.event.title if message.event else None,
        "event_header_image": (
            message.event.header_photo.url
            if message.event and message.event.header_photo
            else None
        ),
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
                return None, f"Contact user '{username}' not found"

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
            paginated_messages = list(messages[offset : offset + page_size])

            # Mark messages as seen if they're from the contact to the current user
            for message in paginated_messages:
                if (
                    message.sender == contact_user
                    and message.receiver == current_user
                    and not message.seen
                ):
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
                                "header_image": (
                                    message.event.header_photo.url
                                    if message.event.header_photo
                                    else None
                                ),
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
            return None, error_message
        except Exception as e:
            error_message = f"Error getting message conversation: {str(e)}"
            print(f"[get_message_conversation_with_contact API] {error_message}")
            return None, error_message

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


@router.get("/surf-posts/top/{event_id}")
async def get_top_surf_posts_for_event(
    request: Request,
    event_id: UUID,
    platform: Optional[str] = None,
):
    """
    API endpoint to get the top 3 surf posts for a specific event, ordered by score.
    """
    print(
        f"[get_top_surf_posts_for_event API] Function called for event_id: {event_id}"
    )

    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def get_top_surf_posts_logic(event_id):
        try:
            # Get the event
            event = Event.objects.get(eventId=event_id)

            # Get all posts for this event
            all_posts = (
                SurfPost.objects.filter(event=event)
                .select_related("user", "user__user_profile")
                .prefetch_related("votes")
            )

            # Calculate scores and sort by score (highest first)
            posts_with_scores = []
            for post in all_posts:
                score = (
                    post.score
                )  # This uses the property that calculates sum of votes
                posts_with_scores.append((post, score))

            # Sort by score (highest first), then by creation date (newest first)
            posts_with_scores.sort(key=lambda x: (x[1], x[0].created_at), reverse=True)

            # Take top 3 posts
            top_posts = posts_with_scores[:3]
            posts = [post for post, score in top_posts]

            posts_data = []
            for post in posts:
                # Get vote counts
                tide_up_count = TideUpTideDown.objects.filter(
                    post=post, value=1
                ).count()
                tide_down_count = TideUpTideDown.objects.filter(
                    post=post, value=-1
                ).count()

                posts_data.append(
                    {
                        "post_id": str(post.surfId),
                        "content": post.content,
                        "score": post.score,
                        "created_at": post.created_at,
                        "user": {
                            "user_id": str(post.user.user_id),
                            "username": post.user.username,
                            "first_name": post.user.first_name,
                            "last_name": post.user.last_name,
                            "profile_photo": (
                                post.user.user_profile.profile_photo.url
                                if post.user.user_profile.profile_photo
                                else None
                            ),
                        },
                        "event": {
                            "event_id": str(post.event.eventId),
                            "title": post.event.title,
                            "date": post.event.date,
                        },
                        "votes": {
                            "tide_up": tide_up_count,
                            "tide_down": tide_down_count,
                            "total": tide_up_count + tide_down_count,
                        },
                    }
                )

            return posts_data, None
        except Event.DoesNotExist:
            error_message = f"Event not found with ID: {event_id}"
            print(f"[get_top_surf_posts_for_event API] {error_message}")
            return None, error_message
        except Exception as e:
            error_message = f"Error retrieving top surf posts: {str(e)}"
            print(f"[get_top_surf_posts_for_event API] {error_message}")
            return None, error_message

    try:
        posts_data, error_message = await get_top_surf_posts_logic(event_id)
        if posts_data is None:
            notification_sent = await notify_by_bot(
                f"**[API: get_top_surf_posts_for_event API]** \n\n {error_message} \n\n Platform: {platform} \n\n Event ID: {event_id}",
                platform or "Unknown",
                "ERROR",
                device_info,
            )
            if notification_sent is None:
                print(
                    "[get_top_surf_posts_for_event API] Could not send notification: BOT_API_KEY not set"
                )
            raise HTTPException(status_code=404, detail=error_message)

        print(
            f"[get_top_surf_posts_for_event API] Returning {len(posts_data)} top posts for event_id: {event_id}"
        )
        return {"top_posts": posts_data}
    except Exception as e:
        if not isinstance(e, HTTPException):
            error_trace = traceback.format_exc()
            print(
                f"[get_top_surf_posts_for_event API] Unhandled exception: {str(e)}\n{error_trace}"
            )
            await notify_by_bot(
                f"**[API: get_top_surf_posts_for_event API]** \n\n Unhandled exception: event_id={event_id}, error={str(e)} \n\n Platform: {platform}",
                platform or "Unknown",
                "ERROR",
                device_info,
            )
            raise HTTPException(status_code=500, detail="Internal server error")
        raise e


@router.post("/crew/{crew_id}/invite-friend")
async def invite_friend_to_crew(
    crew_id: str,
    friend_user_id: str = Body(..., embed=True),
    caller_user_id: Optional[int] = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    Invite a friend to a crew (creates a CrewRequest if not already a member or invited).
    """

    @database_sync_to_async
    def invite_logic():
        try:
            from uuid import UUID

            crew = Crew.objects.get(crewId=UUID(crew_id))
            user = CustomUser.objects.get(id=caller_user_id)
            friend = CustomUser.objects.get(user_id=friend_user_id)
            # Check if already a member
            if CrewMember.objects.filter(crew=crew, user=friend).exists():
                return None, "User is already a member of the crew.", None, None, None

            # Delete any existing crew invites between these users for this crew
            existing_requests = CrewRequest.objects.filter(
                crew=crew, sender=user, receiver=friend
            )
            if existing_requests.exists():
                existing_requests.delete()

            # Create new invite
            crew_request = CrewRequest.objects.create(
                crew=crew,
                sender=user,
                receiver=friend,
                status="pending",
            )

            # Return notification data
            return (
                True,
                None,
                {
                    "friend_user_id": friend.user_id,
                    "sender_name": user.first_name or user.username,
                    "crew_name": crew.name,
                    "crew_id": str(crew.crewId),
                    "request_id": str(crew_request.requestId),
                },
            )
        except Exception as e:
            return None, str(e), None

    result, error, notification_data = await invite_logic()
    if not result:
        raise HTTPException(status_code=400, detail=error or "Could not invite friend.")

    # Send notification to the friend being invited
    if notification_data:
        notification_title = "Crew Invite"
        notification_message = f"{notification_data['sender_name']} invited you to join {notification_data['crew_name']}"
        navigate_to = "crew_invites"
        params = {
            "crew_id": notification_data["crew_id"],
            "crew_name": notification_data["crew_name"],
            "sender_name": notification_data["sender_name"],
            "request_id": notification_data["request_id"],
            "notification_type": "crew_invite",
            "status": "pending",
        }

        await send_notification(
            notification_data["friend_user_id"],
            notification_message,
            notification_title,
            navigate_to=navigate_to,
            params=params,
        )

    return {"message": "Friend invited successfully."}


@router.get("/crew/{crew_id}/friends-not-in-crew")
async def friends_not_in_crew(
    crew_id: str,
    caller_user_id: Optional[int] = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    List all friends of the user who are not already in the crew.
    """

    @database_sync_to_async
    def get_friends():
        from uuid import UUID

        user = CustomUser.objects.get(id=caller_user_id)
        user_profile = user.user_profile
        crew = Crew.objects.get(crewId=UUID(crew_id))
        member_ids = set(
            CrewMember.objects.filter(crew=crew).values_list("user_id", flat=True)
        )
        friends = user_profile.friends.exclude(user__id__in=member_ids)
        return [
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

    friends = await get_friends()
    return {"friends": friends}


@router.get("/crew/{crew_id}/search-friends")
async def search_friends_not_in_crew(
    crew_id: str,
    query: str,
    caller_user_id: Optional[int] = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    Search friends to invite to a crew, excluding those already in the crew.
    """

    @database_sync_to_async
    def search_friends():
        from uuid import UUID

        user = CustomUser.objects.get(id=caller_user_id)
        user_profile = user.user_profile
        crew = Crew.objects.get(crewId=UUID(crew_id))
        member_ids = set(
            CrewMember.objects.filter(crew=crew).values_list("user_id", flat=True)
        )
        friends = user_profile.friends.exclude(user__id__in=member_ids)
        # Simple search by username, first_name, or last_name
        filtered = friends.filter(
            models.Q(user__username__icontains=query)
            | models.Q(user__first_name__icontains=query)
            | models.Q(user__last_name__icontains=query)
        )
        return [
            {
                "user_id": str(friend.user.user_id),
                "username": friend.user.username,
                "first_name": friend.user.first_name,
                "last_name": friend.user.last_name,
                "profile_photo": (
                    friend.profile_photo.url if friend.profile_photo else None
                ),
            }
            for friend in filtered
        ]

    results = await search_friends()
    return {"friends": results}


@router.post("/crew/{crew_id}/leave")
async def leave_crew(
    crew_id: str,
    caller_user_id: Optional[int] = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    Allow a user to leave a crew.
    """

    @database_sync_to_async
    def leave_logic():
        from uuid import UUID

        try:
            crew = Crew.objects.get(crewId=UUID(crew_id))
            user = CustomUser.objects.get(id=caller_user_id)
            membership = CrewMember.objects.filter(crew=crew, user=user)
            if not membership.exists():
                return False, "You are not a member of this crew."
            membership.delete()
            return True, None
        except Exception as e:
            return False, str(e)

    success, error = await leave_logic()
    if not success:
        raise HTTPException(status_code=400, detail=error or "Could not leave crew.")
    return {"message": "Left crew successfully."}


@router.post("/crew/{crew_id}/kick-member")
async def kick_member_from_crew(
    crew_id: str,
    member_user_id: str = Body(..., embed=True),
    caller_user_id: Optional[int] = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    Allow the host (creator) to kick a member from the crew.
    """

    @database_sync_to_async
    def kick_logic():
        from uuid import UUID

        try:
            crew = Crew.objects.get(crewId=UUID(crew_id))
            host = CustomUser.objects.get(id=caller_user_id)
            if crew.created_by != host:
                return False, "Only the crew creator can kick members."
            member = CustomUser.objects.get(user_id=member_user_id)
            membership = CrewMember.objects.filter(crew=crew, user=member)
            if not membership.exists():
                return False, "User is not a member of this crew."
            membership.delete()
            return True, None
        except Exception as e:
            return False, str(e)

    success, error = await kick_logic()
    if not success:
        raise HTTPException(status_code=400, detail=error or "Could not kick member.")
    return {"message": "Member kicked from crew successfully."}


@router.delete("/crew/{crew_id}/delete")
async def delete_crew(
    crew_id: str,
    caller_user_id: Optional[int] = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    Allow the creator to delete the crew and all related data, including shared events.
    """

    @database_sync_to_async
    def delete_logic():
        from uuid import UUID

        try:
            crew = Crew.objects.get(crewId=UUID(crew_id))
            creator = CustomUser.objects.get(id=caller_user_id)
            if crew.created_by != creator:
                return False, "Only the crew creator can delete the crew."
            # Delete all related CrewMember, CrewRequest, and SharedEvent objects
            CrewMember.objects.filter(crew=crew).delete()
            CrewRequest.objects.filter(crew=crew).delete()
            from eventManagementApp.models import SharedEvent

            SharedEvent.objects.filter(crew=crew).delete()
            # Optionally, delete related posts, etc. if needed
            crew.delete()
            return True, None
        except Exception as e:
            return False, str(e)

    success, error = await delete_logic()
    if not success:
        raise HTTPException(status_code=400, detail=error or "Could not delete crew.")
    return {"message": "Crew and all related data deleted successfully."}


@router.post("/crew/{crew_id}/message")
async def send_crew_message(
    crew_id: str,
    content: Optional[str] = Form(None),
    event_id: Optional[str] = Form(None),
    caller_user_id: Optional[int] = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    Send a message to the crew chat (only if member).
    Can be a text message, event share, or both.
    """

    @database_sync_to_async
    def send_message():
        from uuid import UUID

        try:
            crew = Crew.objects.get(crewId=UUID(crew_id))
            user = CustomUser.objects.select_related("user_profile").get(
                id=caller_user_id
            )
            if not CrewMember.objects.filter(crew=crew, user=user).exists():
                return None, None, "You are not a member of this crew."

            # Validate that either content or event_id is provided
            if not content and not event_id:
                return None, None, "Either content or event_id must be provided."

            event = None
            if event_id:
                try:
                    event = Event.objects.get(eventId=UUID(event_id))
                except Event.DoesNotExist:
                    return None, None, f"Event with ID {event_id} not found."

            msg = CrewMessage.objects.create(
                crew=crew,
                sender=user,
                content=content if content is not None else "",
                event=event,
            )

            # Get all member user_ids except sender
            member_ids = list(
                crew.members.exclude(id=user.id).values_list("user_id", flat=True)
            )
            # Get sender profile info
            sender_profile = (
                user.user_profile if hasattr(user, "user_profile") else None
            )
            sender_data = {
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "profile_photo": (
                    sender_profile.profile_photo.url
                    if sender_profile and sender_profile.profile_photo
                    else None
                ),
            }
            return msg, member_ids, sender_data, None
        except Exception as e:
            return None, None, None, str(e)

    msg, member_ids, sender_data, error = await send_message()
    if not msg:
        raise HTTPException(status_code=400, detail=error or "Could not send message.")

    # Prepare WebSocket data based on message type
    ws_data = {
        "type": "crew_message",
        "id": str(msg.id),
        "content": msg.content,
        "created_at": str(msg.created_at),
        "sender": sender_data,
    }

    # Add event data if present
    if msg.event:
        ws_data["event"] = {
            "event_id": str(msg.event.eventId),
            "title": msg.event.title,
            "header_image": (
                msg.event.header_photo.url if msg.event.header_photo else None
            ),
        }
        ws_data["type"] = "crew_event_message"

    # Broadcast via WebSocket
    await crew_manager.broadcast(
        crew_id,
        ws_data,
        exclude_user_id=str(caller_user_id),
    )

    # Send notification to all members except sender
    sender_display_name = (
        msg.sender.first_name if msg.sender.first_name else msg.sender.username
    )

    # Prepare notification based on message type
    if msg.event:
        notification_message = f"{sender_display_name} shared {msg.event.title}"
        if msg.content:
            notification_message += f": {msg.content[:30]}"
        notification_title = f"Event shared in {msg.crew.name}"
        navigate_to = "crew_chat"
        params = {
            "crew_id": crew_id,
            "crew_name": msg.crew.name,
            "sender_username": msg.sender.username,
            "sender_name": sender_display_name,
            "event_id": str(msg.event.eventId),
            "event_title": msg.event.title,
            "message_id": str(msg.id),
            "page": "crew_chat",
            "target_screen": f"crew_chat/{crew_id}",
        }
    else:
        message_preview = (
            msg.content[:50] + "..." if len(msg.content) > 50 else msg.content
        )
        notification_message = f"{sender_display_name}: {message_preview}"
        notification_title = f"New message in {msg.crew.name}"
        navigate_to = "crew_chat"
        params = {
            "crew_id": crew_id,
            "crew_name": msg.crew.name,
            "sender_username": msg.sender.username,
            "sender_name": sender_display_name,
            "message_preview": message_preview,
            "message_id": str(msg.id),
            "page": "crew_chat",
            "target_screen": f"crew_chat/{crew_id}",
        }

    for member_user_id in member_ids:
        await send_notification(
            member_user_id,
            notification_message,
            title=notification_title,
            navigate_to=navigate_to,
            params=params,
        )

    # Prepare response
    response_data = {
        "message": "Message sent",
        "id": str(msg.id),
        "content": msg.content,
        "created_at": msg.created_at,
        "sender": sender_data,
    }

    if msg.event:
        response_data["event"] = {
            "event_id": str(msg.event.eventId),
            "title": msg.event.title,
            "header_image": (
                msg.event.header_photo.url if msg.event.header_photo else None
            ),
        }

    return response_data


@router.get("/crew/{crew_id}/messages")
async def get_crew_messages(
    crew_id: str,
    page: int = 1,
    page_size: int = 20,
    caller_user_id: Optional[int] = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    Get recent messages for the crew (paginated, only if member).
    """

    @database_sync_to_async
    def get_messages():
        from uuid import UUID

        try:
            crew = Crew.objects.get(crewId=UUID(crew_id))
            user = CustomUser.objects.get(id=caller_user_id)
            if not CrewMember.objects.filter(crew=crew, user=user).exists():
                return None, "You are not a member of this crew."
            qs = (
                CrewMessage.objects.filter(crew=crew)
                .select_related("sender", "sender__user_profile", "event")
                .order_by("-created_at")
            )
            total = qs.count()
            start = (page - 1) * page_size
            end = start + page_size
            messages = list(qs[start:end])
            data = []
            for m in messages:
                sender_profile = (
                    m.sender.user_profile if hasattr(m.sender, "user_profile") else None
                )
                message_data = {
                    "id": str(m.id),
                    "content": m.content,
                    "created_at": m.created_at,
                    "sender": {
                        "username": m.sender.username,
                        "first_name": m.sender.first_name,
                        "last_name": m.sender.last_name,
                        "profile_photo": (
                            sender_profile.profile_photo.url
                            if sender_profile and sender_profile.profile_photo
                            else None
                        ),
                    },
                }

                # Add event data if present
                if m.event:
                    message_data["event"] = {
                        "event_id": str(m.event.eventId),
                        "title": m.event.title,
                        "header_image": (
                            m.event.header_photo.url if m.event.header_photo else None
                        ),
                    }

                data.append(message_data)
            return {
                "messages": data,
                "total": total,
                "page": page,
                "page_size": page_size,
            }, None
        except Exception as e:
            return None, str(e)

    result, error = await get_messages()
    if not result:
        raise HTTPException(status_code=400, detail=error or "Could not get messages.")
    return result


@router.websocket("/ws/crew/{crew_id}")
async def crew_chat_ws(websocket: WebSocket, crew_id: str, user_id: str):
    await crew_manager.connect(crew_id, user_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            # Optionally handle incoming messages from client if needed
    except WebSocketDisconnect:
        crew_manager.disconnect(crew_id, user_id)


@router.get("/crew/{crew_id}/invite-status/{target_username}")
async def check_crew_invite_status(
    request: Request,
    crew_id: UUID,
    target_username: str,
    caller_user_id: Optional[int] = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    Check if a crew invite has already been sent to a specific user for a specific crew.
    Returns the status of any existing invite or indicates no invite exists.
    """
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def check_invite_status():
        try:
            # Get the calling user
            caller = CustomUser.objects.get(id=caller_user_id)

            # Get the target user
            target_user = CustomUser.objects.get(username=target_username)

            # Get the crew
            crew = Crew.objects.get(crewId=crew_id)

            # Check if target user is already a member of the crew
            is_member = CrewMember.objects.filter(crew=crew, user=target_user).exists()

            if is_member:
                return {
                    "invite_exists": False,
                    "is_member": True,
                    "status": "already_member",
                    "message": f"{target_username} is already a member of this crew",
                }, None

            # Check for existing crew invite
            existing_invite = CrewRequest.objects.filter(
                sender=caller, receiver=target_user, crew=crew
            ).first()

            if existing_invite:
                return {
                    "invite_exists": True,
                    "is_member": False,
                    "status": existing_invite.status,
                    "invite_id": str(existing_invite.requestId),
                    "created_at": existing_invite.created_at,
                    "updated_at": existing_invite.updated_at,
                    "message": f"Crew invite {existing_invite.status}",
                }, None
            else:
                return {
                    "invite_exists": False,
                    "is_member": False,
                    "status": "no_invite",
                    "message": f"No crew invite sent to {target_username} for this crew",
                }, None

        except CustomUser.DoesNotExist:
            if not CustomUser.objects.filter(id=caller_user_id).exists():
                return None, "Caller user not found"
            else:
                return None, f"Target user '{target_username}' not found"
        except Crew.DoesNotExist:
            return None, f"Crew with ID '{crew_id}' not found"
        except Exception as e:
            logger.error(f"Error checking crew invite status: {e}")
            return None, f"Error checking crew invite status: {str(e)}"

    try:
        result, error = await check_invite_status()

        if error:
            await notify_by_bot(
                f"**[API: check_crew_invite_status]** \n\n Error: {error} \n\n crew_id={crew_id}, target_username={target_username}, caller_user_id={caller_user_id} \n\n Platform: {platform}",
                platform or "Unknown",
                "ERROR",
                device_info,
            )
            raise HTTPException(status_code=404, detail=error)

        return JSONResponse(status_code=200, content={"success": True, "data": result})

    except HTTPException:
        raise
    except Exception as e:
        await notify_by_bot(
            f"**[API: check_crew_invite_status]** \n\n Unexpected error: {str(e)} \n\n crew_id={crew_id}, target_username={target_username}, caller_user_id={caller_user_id} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/crews/{crew_id}/request-join")
async def request_join_crew(
    request: Request,
    crew_id: str,
    current_user_id: int = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    Allow a user to request to join a crew. Creates a CrewJoinRequest and sends notifications.
    """
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]
    try:
        user = await database_sync_to_async(CustomUser.objects.get)(id=current_user_id)
        crew = await database_sync_to_async(Crew.objects.get)(crewId=crew_id)
        # Create join request if not already exists
        try:
            join_request, created = await database_sync_to_async(
                CrewJoinRequest.objects.get_or_create
            )(user=user, crew=crew, defaults={"status": "pending"})

            # Notification logic
            async def send_async_notification(*args, **kwargs):
                await notify_by_bot(*args, **kwargs)

            if created and join_request.status == "pending":
                admins = await database_sync_to_async(
                    lambda: list(crew.crew_members.filter(is_admin=True))
                )()
                for admin in admins:
                    try:
                        asyncio.create_task(
                            send_async_notification(
                                f"{user.username} requested to join your crew '{crew.name}'.",
                                platform="CrewJoinRequest",
                                level="INFO",
                                device_info="",
                            )
                        )
                    except Exception as e:
                        print(f"Error notifying crew admin: {e}")
            elif not created:
                if join_request.status == "accepted":
                    try:
                        asyncio.create_task(
                            send_async_notification(
                                f"Your request to join crew '{crew.name}' was accepted!",
                                platform="CrewJoinRequest",
                                level="INFO",
                                device_info="",
                            )
                        )
                    except Exception as e:
                        print(f"Error notifying user of accepted join request: {e}")
                elif join_request.status == "declined":
                    try:
                        asyncio.create_task(
                            send_async_notification(
                                f"Your request to join crew '{crew.name}' was declined.",
                                platform="CrewJoinRequest",
                                level="INFO",
                                device_info="",
                            )
                        )
                    except Exception as e:
                        print(f"Error notifying user of declined join request: {e}")
            if not created and join_request.status == "pending":
                return {"detail": "Join request already pending.", "status": "pending"}
            elif not created and join_request.status == "accepted":
                return {
                    "detail": "You are already a member of this crew.",
                    "status": "accepted",
                }
            elif not created and join_request.status == "declined":
                # Optionally allow resubmission
                join_request.status = "pending"
                await database_sync_to_async(join_request.save)()
                return {"detail": "Join request resubmitted.", "status": "pending"}
            return {"detail": "Join request submitted.", "status": "pending"}
        except IntegrityError:
            return {
                "detail": "A join request already exists for this user and crew.",
                "status": "pending",
            }
    except Crew.DoesNotExist:
        raise HTTPException(status_code=404, detail="Crew not found")
    except Exception as e:
        await notify_by_bot(
            f"**[API: request_join_crew]** \n\n Error: {str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(
            status_code=500, detail=f"Error requesting to join crew: {str(e)}"
        )


@router.get("/crews/{crew_id}/join-requests")
async def list_pending_crew_join_requests(
    crew_id: str,
    current_user_id: int = Depends(get_current_user),
):
    """
    List all pending join requests for a crew. Only accessible by crew admins.
    """
    crew = await database_sync_to_async(Crew.objects.get)(crewId=crew_id)
    admin_user = await database_sync_to_async(CustomUser.objects.get)(
        id=current_user_id
    )
    is_admin = await database_sync_to_async(
        lambda: crew.crew_members.filter(user=admin_user, is_admin=True).exists()
    )()
    if not is_admin:
        raise HTTPException(
            status_code=403, detail="Only crew admins can view join requests."
        )
    pending_requests = await database_sync_to_async(
        lambda: list(crew.join_requests.filter(status="pending"))
    )()
    result = [
        {
            "requestId": str(r.requestId),
            "user_id": r.user.id,
            "username": r.user.username,
            "created_at": r.created_at.isoformat(),
            "status": r.status,
        }
        for r in pending_requests
    ]
    return {"pending_requests": result}


@router.post("/crews/{crew_id}/join-requests/{request_id}/accept")
async def accept_crew_join_request(
    request: Request,
    crew_id: str,
    request_id: str,
    current_user_id: int = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    Allow a crew admin to accept a CrewJoinRequest. Adds the user as a CrewMember and sends notifications.
    """
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]
    try:
        admin_user = await database_sync_to_async(CustomUser.objects.get)(
            id=current_user_id
        )
        crew = await database_sync_to_async(Crew.objects.get)(crewId=crew_id)
        is_admin = await database_sync_to_async(
            lambda: crew.crew_members.filter(user=admin_user, is_admin=True).exists()
        )()
        if not is_admin:
            raise HTTPException(
                status_code=403, detail="Only crew admins can accept join requests."
            )
        join_request = await database_sync_to_async(CrewJoinRequest.objects.get)(
            requestId=request_id
        )
        if join_request.status != "pending":
            return {
                "detail": f"Request is already {join_request.status}.",
                "status": join_request.status,
            }
        join_request.status = "accepted"
        await database_sync_to_async(join_request.save)()
        from socialApp.models import CrewMember

        member_exists = await database_sync_to_async(
            lambda: CrewMember.objects.filter(
                crew=crew, user=join_request.user
            ).exists()
        )()
        if not member_exists:
            await database_sync_to_async(CrewMember.objects.create)(
                crew=crew, user=join_request.user
            )
        crew_members = await database_sync_to_async(
            lambda: list(crew.crew_members.exclude(user=join_request.user))
        )()

        async def send_async_notification(*args, **kwargs):
            await notify_by_bot(*args, **kwargs)

        for member in crew_members:
            try:
                asyncio.create_task(
                    send_async_notification(
                        f"{join_request.user.username} has joined your crew '{crew.name}'.",
                        platform="CrewJoinRequest",
                        level="INFO",
                        device_info="",
                    )
                )
            except Exception as e:
                print(f"Error notifying crew member: {e}")
        try:
            asyncio.create_task(
                send_async_notification(
                    f"You have been accepted into the crew '{crew.name}'.",
                    platform="CrewJoinRequest",
                    level="INFO",
                    device_info="",
                )
            )
        except Exception as e:
            print(f"Error notifying new member: {e}")
        return {
            "detail": "Join request accepted and user added to crew.",
            "status": "accepted",
        }
    except Crew.DoesNotExist:
        raise HTTPException(status_code=404, detail="Crew not found")
    except CrewJoinRequest.DoesNotExist:
        raise HTTPException(status_code=404, detail="Join request not found")
    except Exception as e:
        await notify_by_bot(
            f"**[API: accept_crew_join_request]** \n\n Error: {str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(
            status_code=500, detail=f"Error accepting crew join request: {str(e)}"
        )


@router.post("/crews/{crew_id}/join-requests/{request_id}/decline")
async def decline_crew_join_request(
    request: Request,
    crew_id: str,
    request_id: str,
    current_user_id: int = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    Allow a crew admin to decline a CrewJoinRequest. Updates status and notifies the user.
    """
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]
    try:
        admin_user = await database_sync_to_async(CustomUser.objects.get)(
            id=current_user_id
        )
        crew = await database_sync_to_async(Crew.objects.get)(crewId=crew_id)
        is_admin = await database_sync_to_async(
            lambda: crew.crew_members.filter(user=admin_user, is_admin=True).exists()
        )()
        if not is_admin:
            raise HTTPException(
                status_code=403, detail="Only crew admins can decline join requests."
            )
        join_request = await database_sync_to_async(CrewJoinRequest.objects.get)(
            requestId=request_id
        )
        if join_request.status != "pending":
            return {
                "detail": f"Request is already {join_request.status}.",
                "status": join_request.status,
            }
        join_request.status = "declined"
        await database_sync_to_async(join_request.save)()

        async def send_async_notification(*args, **kwargs):
            await notify_by_bot(*args, **kwargs)

        try:
            asyncio.create_task(
                send_async_notification(
                    f"Your request to join crew '{crew.name}' was declined.",
                    platform="CrewJoinRequest",
                    level="INFO",
                    device_info="",
                )
            )
        except Exception as e:
            print(f"Error notifying user of declined join request: {e}")
        return {"detail": "Join request declined.", "status": "declined"}
    except Crew.DoesNotExist:
        raise HTTPException(status_code=404, detail="Crew not found")
    except CrewJoinRequest.DoesNotExist:
        raise HTTPException(status_code=404, detail="Join request not found")
    except Exception as e:
        await notify_by_bot(
            f"**[API: decline_crew_join_request]** \n\n Error: {str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(
            status_code=500, detail=f"Error declining crew join request: {str(e)}"
        )


@router.get("/crews/{crew_id}/check-join-request")
async def check_crew_join_request_status(
    request: Request,
    crew_id: str,
    current_user_id: int = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    Check if the current user has already sent a request to join the specified crew.
    Returns the status of the join request if it exists.
    """
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:

        @database_sync_to_async
        def check_join_request_status():
            try:
                user = CustomUser.objects.get(id=current_user_id)
                crew = Crew.objects.get(crewId=crew_id)

                # Check if user is already a member of the crew
                is_member = CrewMember.objects.filter(user=user, crew=crew).exists()
                if is_member:
                    return {
                        "has_request": False,
                        "status": "member",
                        "message": "User is already a member of this crew",
                    }

                # Check if there's an existing join request
                try:
                    join_request = CrewJoinRequest.objects.get(user=user, crew=crew)
                    return {
                        "has_request": True,
                        "status": join_request.status,
                        "request_id": str(join_request.requestId),
                        "created_at": (
                            join_request.created_at.isoformat()
                            if hasattr(join_request, "created_at")
                            else None
                        ),
                        "message": f"Join request is {join_request.status}",
                    }
                except CrewJoinRequest.DoesNotExist:
                    return {
                        "has_request": False,
                        "status": "none",
                        "message": "No join request found",
                    }

            except CustomUser.DoesNotExist:
                raise HTTPException(status_code=404, detail="User not found")
            except Crew.DoesNotExist:
                raise HTTPException(status_code=404, detail="Crew not found")

        result = await check_join_request_status()
        return result

    except HTTPException:
        raise
    except Exception as e:
        await notify_by_bot(
            f"**[API: check_crew_join_request_status]** \n\n Error: {str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(
            status_code=500, detail=f"Error checking crew join request status: {str(e)}"
        )

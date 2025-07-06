from typing import Optional
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


from apiManager.utilities.notify_by_bot import notify_by_bot
from apiManager.utilities.device_info import get_device_info

from eventManagementApp.models import Event
from accountManagementApp.models import UserProfile
from socialApp.models import (
    Crew,
    CrewMember,
    FriendRequest,
    CrewRequest,
    SocialActivity,
)
from eventTicketsApp.views import generateTicket
from apiManager.algorithms.suggested_friends import get_suggested_friends


from apiManager.dependencies import get_current_user
from authenticationApp.models import CustomUser
from uuid import UUID

from .serializers import MyPassSerializer, SearchResult, UserFriends, UserCrewsResponse


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

            # Get user's friends (max 4)
            friends = []
            for friend in user_profile.friends.all()[:4]:
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

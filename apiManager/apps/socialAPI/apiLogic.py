from typing import Optional
from channels.db import database_sync_to_async
from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
import bleach
import os
from user_agents import parse as parse_user_agent
from django.db.models import Q, Prefetch


from apiManager.utilities.notify_by_bot import notify_by_bot
from apiManager.utilities.device_info import get_device_info

from eventManagementApp.models import Event
from accountManagementApp.models import UserProfile
from socialApp.models import Crew, CrewMember
from eventTicketsApp.views import generateTicket


from apiManager.dependencies import get_current_user
from authenticationApp.models import CustomUser
from uuid import UUID

from .serializers import MyPassSerializer, SearchResult


router = APIRouter()


@router.get("/user/{username}")
async def get_user_details(
    username: str, caller_user_id: Optional[int] = Depends(get_current_user)
):
    """
    API endpoint to retrieve comprehensive information about a specific user by username.
    """
    print(f"[get_user_details API] Function called with username: {username}")

    @database_sync_to_async
    def get_user_data(username, caller_user_id):
        try:
            # Get user with related profile in a single query
            user = CustomUser.objects.select_related("user_profile").get(
                username=username
            )
            user_profile = user.user_profile

            # Determine if the calling user is viewing their own profile
            is_own_profile = False
            if caller_id:
                try:
                    calling_user = CustomUser.objects.get(id=caller_id)
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

            # Get user's favorite events (limit for performance)
            favorite_events = []
            for event in user_profile.favorite_events.all()[:20]:
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

            # Get user's purchased events (limit for performance)
            purchased_events = []
            for event in user_profile.purchased_events.all()[:20]:
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

            # Get user's hosted events (if they are a host)
            hosted_events = []
            for event in Event.objects.filter(host=user)[:20]:
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
                    "crew_memberships": crew_memberships,
                    "favorite_events": favorite_events,
                    "purchased_events": purchased_events,
                    "hosted_events": hosted_events,
                },
                "is_own_profile": is_own_profile,
            }
        except CustomUser.DoesNotExist:
            print(f"[get_user_details API] User not found with username: {username}")
            return None
        except Exception as e:
            print(f"[get_user_details API] Error retrieving user data: {str(e)}")
            return None

    user_data = await get_user_data(username, caller_user_id)
    if user_data is None:
        return {"error": "User not found"}

    print(
        f"[get_user_details API] Returning details for user: {user_data['user']['username']}"
    )

    return {"user_details": user_data}


@router.get("/crew/{crew_id}")
async def get_crew_details(
    crew_id: UUID, user_id: Optional[int] = Depends(get_current_user)
):
    """
    API endpoint to retrieve comprehensive information about a specific crew.
    """
    print(f"[get_crew_details API] Function called with crew_id: {crew_id}")

    @database_sync_to_async
    def get_crew_data(crew_id):
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
            for crew_member in CrewMember.objects.filter(crew=crew).select_related(
                "user", "user__user_profile"
            ):
                member_profile = (
                    crew_member.user.user_profile
                    if hasattr(crew_member.user, "user_profile")
                    else None
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
            }
        except Crew.DoesNotExist:
            print(f"[get_crew_details API] Crew not found with ID: {crew_id}")
            return None
        except Exception as e:
            print(f"[get_crew_details API] Error retrieving crew data: {str(e)}")
            return None

    crew_data = await get_crew_data(crew_id)
    if crew_data is None:
        raise HTTPException(status_code=404, detail="Crew not found")

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
            user_profile = user.user_profile

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
            f"**[API: get_my_pass API]** \n\n {error_message}",
            platform,
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
            f"**[API: search API]** \n\n {error_message}",
            platform,
            "ERROR",
            device_info,
        )
        if notification_sent is None:
            print("[search API] Could not send notification: BOT_API_KEY not set")
        raise HTTPException(status_code=500, detail="Error searching users")

    return {"users": users, "crews": crews}

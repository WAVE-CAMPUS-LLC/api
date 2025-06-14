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
from socialApp.models import Crew, CrewMember, FriendRequest
from eventTicketsApp.views import generateTicket
from apiManager.algorithms.suggested_friends import get_suggested_friends


from apiManager.dependencies import get_current_user
from authenticationApp.models import CustomUser
from uuid import UUID

from .serializers import MyPassSerializer, SearchResult, UserFriends, UserCrewsResponse


router = APIRouter()


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
            user_profile = user.user_profile

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
                            elif friend_request.status == "declined":
                                friend_request_status = "declined"
                            elif friend_request.status == "canceled":
                                friend_request_status = "canceled"
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
            
            for crew_member in CrewMember.objects.filter(crew=crew).select_related(
                "user", "user__user_profile"
            ):
                member_profile = (
                    crew_member.user.user_profile
                    if hasattr(crew_member.user, "user_profile")
                    else None
                )
                
                # Check if the caller is this crew member
                if caller_user_id and crew_member.user.id == caller_user_id:
                    user_is_member = True
                    user_is_admin = crew_member.is_admin
                
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
                "user_is_member": user_is_member,
                "user_is_admin": user_is_admin,
            }
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
            user_profile = user.user_profile
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
            # Get sender user
            sender_user = CustomUser.objects.get(id=sender_user_id)

            # Check if trying to send request to self
            if receiver_username == sender_user.username:
                return None, "You cannot send a friend request to yourself.", None

            # Get receiver user profile
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
                            active_request,
                        )
                    else:
                        return (
                            None,
                            f"{receiver_username} has already sent you a friend request. Check your notifications to respond.",
                            active_request,
                        )
                else:  # status is 'accepted'
                    return (
                        None,
                        "You are already friends with this user.",
                        active_request,
                    )

            # Check for canceled/declined requests to reuse
            old_request = FriendRequest.objects.filter(
                sender=sender_user,
                receiver=receiver_user,
                status__in=["canceled", "declined"],
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
            # Get sender user
            sender_user = CustomUser.objects.get(id=sender_user_id)

            # Check if trying to cancel request to self
            if receiver_username == sender_user.username:
                return None, "You cannot cancel a friend request to yourself.", None

            # Get receiver user profile
            try:
                receiver_user_profile = UserProfile.objects.select_related("user").get(
                    user__username=receiver_username
                )
                receiver_user = receiver_user_profile.user
            except UserProfile.DoesNotExist:
                return None, "User not found.", None

            # Find the pending friend request sent by the caller
            friend_request = FriendRequest.objects.filter(
                sender=sender_user, receiver=receiver_user, status="pending"
            ).first()

            if not friend_request:
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
            # Get receiver user (the one accepting the request)
            receiver_user = CustomUser.objects.get(id=receiver_user_id)

            # Check if trying to accept request from self
            if sender_username == receiver_user.username:
                return None, "You cannot accept a friend request from yourself.", None

            # Get sender user profile
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
                return None, "No pending friend request found to accept.", None

            # Update the request status to accepted
            friend_request.status = "accepted"
            friend_request.save()

            # Add both users to each other's friends list
            receiver_user.user_profile.friends.add(sender_user_profile)
            sender_user_profile.friends.add(receiver_user.user_profile)

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
            # Get receiver user (the one declining the request)
            receiver_user = CustomUser.objects.get(id=receiver_user_id)

            # Check if trying to decline request from self
            if sender_username == receiver_user.username:
                return None, "You cannot decline a friend request from yourself.", None

            # Get sender user profile
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
                return None, "No pending friend request found to decline.", None

            # Update the request status to declined
            friend_request.status = "declined"
            friend_request.save()

            return (
                {
                    "status": friend_request.status,
                    "declined_at": friend_request.updated_at,
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
            # Get caller user
            caller_user = CustomUser.objects.get(id=caller_user_id)

            # Check if trying to remove self
            if friend_username == caller_user.username:
                return None, "You cannot remove yourself as a friend.", None

            # Get friend user profile
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

            # Remove friendship from both users' friend lists
            caller_user.user_profile.friends.remove(friend_user_profile)
            friend_user_profile.friends.remove(caller_user.user_profile)

            # Update any accepted friend request to "removed" status (optional - for tracking)
            friend_request = FriendRequest.objects.filter(
                Q(sender=caller_user, receiver=friend_user)
                | Q(sender=friend_user, receiver=caller_user),
                status="accepted",
            ).first()

            friendship_removed_at = None
            if friend_request:
                # Optional: You can track when friendship was removed
                # For now, we'll just update the timestamp
                friend_request.save()  # This will update the updated_at field
                friendship_removed_at = friend_request.updated_at

            return (
                {
                    "friendship_removed": True,
                    "removed_at": friendship_removed_at,
                    "friend_username": friend_username,
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

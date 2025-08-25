from datetime import datetime, timedelta
from uuid import UUID
import time
from django.http import Http404
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    Request,
    Header,
    UploadFile,
    Form,
    Body,
    Query,
)
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from channels.db import database_sync_to_async
import traceback
import os
from django.core.files.base import ContentFile
from django.conf import settings
from django.db.models import (
    Count,
    Max,
    Avg,
    F,
    Sum,
    Q,
    Case,
    When,
    IntegerField,
    Subquery,
    OuterRef,
)
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth, TruncHour
from django.utils.timezone import now
from django.core.cache import cache

from authenticationApp.models import CustomUser
from authenticationApp.serializers import CustomUserSerializer
from django.contrib.auth import authenticate

from apiManager.dependencies import get_current_user
from apiManager.middleware.adminAccess import (
    require_admin_role,
    require_super_admin_role,
    require_member_role,
    get_user_with_roles,
    require_roles,
    require_permissions,
    require_marketing_lead_role,
)
from django.shortcuts import get_object_or_404
from .serializers import (
    UserResponse,
    UserUpdateRequest,
    EventWithTickets,
    FriendInfo,
    UserProfileInfo,
)

from eventManagementApp.models import Event
from ambassadorManagement.models import AmbassadorApplication, AmbassadorProgramDetails
from ambassadorManagement.forms import AmbassadorProgramDetailsForm
from eventTicketsApp.models import RSVPTicket, PaidFreeTicket, Ticket
from eventTicketsApp.models import Ticket, RSVPTicket
from accountManagementApp.models import UserProfile
from adminDashboardApp.models import College, LoginHistoryModel
from socialApp.models import FixedMessage
from socialApp.forms import FixedMessageForm, FixedMessageEditForm

from adminDashboardApp.models import College
from collegeManagementApp.models import Membership, CollegeEventLink
from adminDashboardApp.forms import CollegeForm, EditCollegeForm
from apiManager.utilities.form_fields import get_form_fields
from apiManager.utilities.notify_by_bot import notify_by_bot
from apiManager.utilities.device_info import get_device_info

router = APIRouter()


# USERS
@router.get("/dashboard")
async def admin_dashboard(
    request: Request,
    current_user: CustomUser = Depends(require_admin_role),
    platform: Optional[str] = None,
):
    """
    Admin dashboard endpoint - requires Admin or Super Admin role.
    """
    print(f"[admin_dashboard] API called with user_id: {current_user.pk}")

    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:
        # Get current user info
        user_groups = await database_sync_to_async(list)(
            current_user.groups.values_list("name", flat=True)
        )

        # Get dashboard stats
        total_users = await database_sync_to_async(CustomUser.objects.count)()
        active_users = await database_sync_to_async(
            CustomUser.objects.filter(is_active=True).count
        )()
        suspended_users = await database_sync_to_async(
            CustomUser.objects.filter(is_suspended=True).count
        )()

        return {
            "message": "Admin dashboard",
            "user": {
                "id": current_user.pk,
                "username": current_user.username,
                "roles": user_groups,
            },
            "stats": {
                "total_users": total_users,
                "active_users": active_users,
                "suspended_users": suspended_users,
            },
        }
    except Exception as e:
        await notify_by_bot(
            f"**[API: admin_dashboard]** \n\n Error loading dashboard: user_id={current_user.pk}, error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(
            status_code=500, detail=f"Error loading dashboard: {str(e)}"
        )


@router.get("/users", response_model=List[UserResponse])
async def get_users(
    request: Request,
    skip: int = 0,
    limit: int = 0,  # 0 means no limit (return all users)
    current_user: CustomUser = Depends(require_admin_role),
    platform: Optional[str] = None,
):
    """
    Get list of users - requires Admin or Super Admin role.
    If limit is 0, returns all users. Otherwise uses pagination.
    """
    print(f"[get_users] API called with user_id: {current_user.pk}")

    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:
        # Get users with optional pagination - if limit is 0, get all users
        if limit == 0:
            users_queryset = CustomUser.objects.select_related(
                "user_profile"
            ).prefetch_related("groups")
        else:
            users_queryset = CustomUser.objects.select_related(
                "user_profile"
            ).prefetch_related("groups")[skip : skip + limit]

        users = await database_sync_to_async(list)(users_queryset)
        print(f"[get_users] Retrieved {len(users)} users from database")

        # Convert to response format
        user_responses = []
        for user in users:
            groups = await database_sync_to_async(list)(
                user.groups.values_list("name", flat=True)
            )

            # Get profile photo URL if it exists
            profile_photo_url = None
            try:
                if (
                    hasattr(user, "user_profile")
                    and user.user_profile
                    and user.user_profile.profile_photo
                ):
                    profile_photo_url = user.user_profile.profile_photo.url
            except Exception as e:
                print(
                    f"[get_users] Warning: Could not get profile photo for user {user.id}: {str(e)}"
                )

            user_responses.append(
                UserResponse(
                    id=user.id,
                    username=user.username,
                    email=user.email,
                    first_name=user.first_name or "",
                    last_name=user.last_name or "",
                    is_active=user.is_active,
                    is_staff=user.is_staff,
                    is_suspended=user.is_suspended,
                    groups=groups,
                    date_joined=user.date_joined,
                    profile_photo=profile_photo_url,
                )
            )

        print(f"[get_users] Returning {len(user_responses)} users in response")
        return user_responses

    except Exception as e:
        await notify_by_bot(
            f"**[API: get_users]** \n\n Error fetching users: user_id={current_user.pk}, error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(status_code=500, detail=f"Error fetching users: {str(e)}")


@router.get("/user/{user_id}", response_model=UserResponse)
async def get_user_detail(
    user_id: int,
    request: Request,
    current_user: CustomUser = Depends(require_admin_role),
    platform: Optional[str] = None,
):
    """
    Get detailed user information including tickets, friends, and profile - requires Admin or Super Admin role.
    """
    print(f"[get_user_detail] API called for user_id: {user_id} by {current_user.pk}")

    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def get_user_complete_data(user_id):
        try:
            # Get user with related data
            user = (
                CustomUser.objects.select_related("user_profile")
                .prefetch_related("groups")
                .get(id=user_id)
            )

            # Get user groups
            groups = list(user.groups.values_list("name", flat=True))

            # Get profile photo URL if it exists
            profile_photo_url = None
            user_profile_info = None
            try:
                user_profile = getattr(user, "user_profile", None)
                if user_profile:
                    if user_profile.profile_photo:
                        profile_photo_url = user_profile.profile_photo.url

                    # Get user profile information
                    college_name = None
                    if user_profile.college:
                        college_name = user_profile.college.name

                    user_profile_info = {
                        "college": college_name,
                        "is_campus_manager": user_profile.is_campus_manager,
                        "profile_photo": profile_photo_url,
                        "was_host": user_profile.was_host,
                    }
            except Exception as e:
                print(
                    f"[get_user_detail] Warning: Could not get profile info for user {user.id}: {str(e)}"
                )

            # Get events user has tickets to
            events_with_tickets = []
            try:
                # Get RSVP tickets
                rsvp_tickets = RSVPTicket.objects.filter(
                    email=user.email
                ).select_related("event")
                for rsvp in rsvp_tickets:
                    event = rsvp.event
                    events_with_tickets.append(
                        {
                            "eventId": str(event.eventId),
                            "title": event.title,
                            "date": event.date,
                            "header_photo": (
                                event.header_photo.url if event.header_photo else None
                            ),
                            "event_type": event.event_type,
                            "city": event.city,
                            "state": event.state,
                            "ticket_type": "rsvp",
                            "ticket_status": "confirmed",
                        }
                    )

                # Get paid tickets
                paid_tickets = Ticket.objects.filter(user=user).select_related("event")
                for ticket in paid_tickets:
                    event = ticket.event
                    events_with_tickets.append(
                        {
                            "eventId": str(event.eventId),
                            "title": event.title,
                            "date": event.date,
                            "header_photo": (
                                event.header_photo.url if event.header_photo else None
                            ),
                            "event_type": event.event_type,
                            "city": event.city,
                            "state": event.state,
                            "ticket_type": "paid",
                            "ticket_status": ticket.status,
                        }
                    )
            except Exception as e:
                print(
                    f"[get_user_detail] Warning: Could not get tickets for user {user.id}: {str(e)}"
                )

            # Get friends
            friends_list = []
            try:
                if hasattr(user, "user_profile") and user.user_profile:
                    friends = user.user_profile.friends.all().select_related("user")
                    for friend_profile in friends:
                        friend_user = friend_profile.user
                        friend_photo_url = None
                        if friend_profile.profile_photo:
                            friend_photo_url = friend_profile.profile_photo.url

                        friends_list.append(
                            {
                                "id": friend_user.id,
                                "username": friend_user.username,
                                "first_name": friend_user.first_name,
                                "last_name": friend_user.last_name,
                                "profile_photo": friend_photo_url,
                            }
                        )
            except Exception as e:
                print(
                    f"[get_user_detail] Warning: Could not get friends for user {user.id}: {str(e)}"
                )

            return {
                "user": user,
                "groups": groups,
                "profile_photo_url": profile_photo_url,
                "user_profile_info": user_profile_info,
                "events_with_tickets": events_with_tickets,
                "friends_list": friends_list,
            }

        except CustomUser.DoesNotExist:
            return None

    try:
        user_data = await get_user_complete_data(user_id)
        if user_data is None:
            raise HTTPException(status_code=404, detail="User not found")

        user = user_data["user"]

        # Convert events to Pydantic models
        events_models = [
            EventWithTickets(**event) for event in user_data["events_with_tickets"]
        ]

        # Convert friends to Pydantic models
        friends_models = [FriendInfo(**friend) for friend in user_data["friends_list"]]

        # Convert user profile to Pydantic model
        user_profile_model = None
        if user_data["user_profile_info"]:
            user_profile_model = UserProfileInfo(**user_data["user_profile_info"])

        print(
            f"[get_user_detail] Returning details for user {user.username} with {len(events_models)} events and {len(friends_models)} friends"
        )

        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            first_name=user.first_name or "",
            last_name=user.last_name or "",
            is_active=user.is_active,
            is_staff=user.is_staff,
            is_suspended=user.is_suspended,
            groups=user_data["groups"],
            date_joined=user.date_joined,
            profile_photo=user_data["profile_photo_url"],
            events_with_tickets=events_models,
            friends=friends_models,
            user_profile=user_profile_model,
        )

    except Exception as e:
        if "does not exist" in str(e).lower():
            raise HTTPException(status_code=404, detail="User not found")
        await notify_by_bot(
            f"**[API: get_user_detail]** \n\n Error fetching user: user_id={user_id}, error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(status_code=500, detail=f"Error fetching user: {str(e)}")


@router.post("/user/{user_id}/suspend")
async def suspend_user(
    user_id: int,
    request: Request,
    current_user: CustomUser = Depends(require_super_admin_role),
    platform: Optional[str] = None,
):
    """
    Suspend a user - requires Super Admin role.
    """
    print(f"[suspend_user] API called for user_id: {user_id} by {current_user.id}")

    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:
        user = await database_sync_to_async(get_object_or_404)(CustomUser, id=user_id)

        # Don't allow suspending yourself
        if user.id == current_user.id:
            raise HTTPException(status_code=400, detail="You cannot suspend yourself")

        await database_sync_to_async(user.suspend)()

        return {"message": f"User {user.username} has been suspended"}

    except Exception as e:
        if "does not exist" in str(e).lower():
            raise HTTPException(status_code=404, detail="User not found")
        await notify_by_bot(
            f"**[API: suspend_user]** \n\n Error suspending user: user_id={user_id}, error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(status_code=500, detail=f"Error suspending user: {str(e)}")


@router.post("/user/{user_id}/delete")
async def delete_user(
    user_id: int,
    request: Request,
    current_user: CustomUser = Depends(require_super_admin_role),
    platform: Optional[str] = None,
):
    """
    Delete a user - requires Super Admin role.
    """
    print(f"[delete_user] API called for user_id: {user_id} by {current_user.id}")

    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:
        # Check if user exists first
        user_exists = await database_sync_to_async(
            CustomUser.objects.filter(id=user_id).exists
        )()
        if not user_exists:
            print(f"[delete_user] User with ID {user_id} does not exist")
            raise HTTPException(
                status_code=404, detail=f"User with ID {user_id} not found"
            )

        user = await database_sync_to_async(get_object_or_404)(CustomUser, id=user_id)
        username = user.username  # Store username before deletion
        await database_sync_to_async(user.delete)()

        print(f"[delete_user] Successfully deleted user {username} (ID: {user_id})")
        return {"message": f"User {username} has been deleted"}
    except HTTPException:
        # Re-raise HTTP exceptions (like 404)
        raise
    except Exception as e:
        print(f"[delete_user] Error deleting user {user_id}: {str(e)}")
        await notify_by_bot(
            f"**[API: delete_user]** \n\n Error deleting user: user_id={user_id}, error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(status_code=500, detail=f"Error deleting user: {str(e)}")


@router.post("/user/{user_id}/unsuspend")
async def unsuspend_user(
    user_id: int,
    request: Request,
    current_user: CustomUser = Depends(require_super_admin_role),
    platform: Optional[str] = None,
):
    """
    Remove suspension from a user - requires Super Admin role.
    """
    print(f"[unsuspend_user] API called for user_id: {user_id} by {current_user.id}")

    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:
        user = await database_sync_to_async(get_object_or_404)(CustomUser, id=user_id)
        await database_sync_to_async(user.remove_suspension_OR_ban)()

        return {"message": f"User {user.username} suspension has been removed"}

    except Exception as e:
        if "does not exist" in str(e).lower():
            raise HTTPException(status_code=404, detail="User not found")
        await notify_by_bot(
            f"**[API: unsuspend_user]** \n\n Error removing suspension: user_id={user_id}, error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(
            status_code=500, detail=f"Error removing suspension: {str(e)}"
        )


@router.post("/user/{user_id}/roles/add")
async def add_role_to_user(
    user_id: int,
    request: Request,
    current_user: CustomUser = Depends(require_admin_role),
    platform: Optional[str] = None,
):
    """
    Add a role (group) to a specific user - requires Admin or Super Admin role.
    """
    print(f"[add_role_to_user] API called for user_id: {user_id} by {current_user.pk}")

    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:
        # Get the role name from request body
        request_data = await request.json()
        role_name = request_data.get("role_name", "").strip()

        if not role_name:
            raise HTTPException(status_code=400, detail="Role name is required")

        @database_sync_to_async
        def add_user_role(user_id, role_name):
            try:
                # Get the user
                user = get_object_or_404(CustomUser, id=user_id)
                print(f"[add_role_to_user] Found user: {user.username}")

                # Import Group model
                from django.contrib.auth.models import Group

                # Get or create the group/role
                group, created = Group.objects.get_or_create(name=role_name)

                if created:
                    print(f"[add_role_to_user] Created new group: {role_name}")
                else:
                    print(f"[add_role_to_user] Using existing group: {role_name}")

                # Check if user already has this role
                if user.groups.filter(name=role_name).exists():
                    return {
                        "success": False,
                        "message": f"User {user.username} already has the role '{role_name}'",
                        "user": {
                            "id": user.pk,
                            "username": user.username,
                            "first_name": user.first_name,
                            "last_name": user.last_name,
                        },
                        "role": role_name,
                        "already_had_role": True,
                    }

                # Add the user to the group
                user.groups.add(group)
                print(
                    f"[add_role_to_user] Added role '{role_name}' to user {user.username}"
                )

                # Get updated user groups for response
                updated_groups = list(user.groups.values_list("name", flat=True))

                return {
                    "success": True,
                    "message": f"Successfully added role '{role_name}' to user {user.username}",
                    "user": {
                        "id": user.pk,
                        "username": user.username,
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                        "all_roles": updated_groups,
                    },
                    "role_added": role_name,
                    "group_was_created": created,
                }

            except CustomUser.DoesNotExist:
                print(f"[add_role_to_user] User not found with ID: {user_id}")
                return {
                    "success": False,
                    "message": "User not found",
                    "error_type": "user_not_found",
                }
            except Exception as e:
                print(f"[add_role_to_user] Database error: {str(e)}")
                return {
                    "success": False,
                    "message": f"Database error: {str(e)}",
                    "error_type": "database_error",
                }

        # Execute the role addition
        result = await add_user_role(user_id, role_name)

        if not result["success"]:
            if result.get("error_type") == "user_not_found":
                raise HTTPException(status_code=404, detail=result["message"])
            elif result.get("already_had_role"):
                # Return 200 for already having role (not an error)
                return JSONResponse(content=result, status_code=200)
            else:
                raise HTTPException(status_code=500, detail=result["message"])

        print(f"[add_role_to_user] Role addition successful: {result['message']}")
        return JSONResponse(content=result, status_code=200)

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        await notify_by_bot(
            f"**[API: add_role_to_user]** \n\n Error adding role to user: user_id={user_id}, role_name={role_name if 'role_name' in locals() else 'unknown'}, error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(
            status_code=500, detail=f"Error adding role to user: {str(e)}"
        )


@router.post("/user/{user_id}/roles/remove")
async def remove_role_from_user(
    user_id: int,
    request: Request,
    current_user: CustomUser = Depends(require_admin_role),
    platform: Optional[str] = None,
):
    """
    Remove a role (group) from a specific user - requires Admin or Super Admin role.
    """
    print(
        f"[remove_role_from_user] API called for user_id: {user_id} by {current_user.pk}"
    )

    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:
        # Get the role name from request body
        request_data = await request.json()
        role_name = request_data.get("role_name", "").strip()

        if not role_name:
            raise HTTPException(status_code=400, detail="Role name is required")

        @database_sync_to_async
        def remove_user_role(user_id, role_name):
            try:
                # Get the user
                user = get_object_or_404(CustomUser, id=user_id)
                print(f"[remove_role_from_user] Found user: {user.username}")

                # Import Group model
                from django.contrib.auth.models import Group

                # Check if the group exists
                try:
                    group = Group.objects.get(name=role_name)
                except Group.DoesNotExist:
                    return {
                        "success": False,
                        "message": f"Role '{role_name}' does not exist",
                        "error_type": "role_not_found",
                    }

                # Check if user has this role
                if not user.groups.filter(name=role_name).exists():
                    return {
                        "success": False,
                        "message": f"User {user.username} does not have the role '{role_name}'",
                        "user": {
                            "id": user.pk,
                            "username": user.username,
                            "first_name": user.first_name,
                            "last_name": user.last_name,
                        },
                        "role": role_name,
                        "user_didnt_have_role": True,
                    }

                # Remove the user from the group
                user.groups.remove(group)
                print(
                    f"[remove_role_from_user] Removed role '{role_name}' from user {user.username}"
                )

                # Get updated user groups for response
                updated_groups = list(user.groups.values_list("name", flat=True))

                return {
                    "success": True,
                    "message": f"Successfully removed role '{role_name}' from user {user.username}",
                    "user": {
                        "id": user.pk,
                        "username": user.username,
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                        "all_roles": updated_groups,
                    },
                    "role_removed": role_name,
                }

            except CustomUser.DoesNotExist:
                print(f"[remove_role_from_user] User not found with ID: {user_id}")
                return {
                    "success": False,
                    "message": "User not found",
                    "error_type": "user_not_found",
                }
            except Exception as e:
                print(f"[remove_role_from_user] Database error: {str(e)}")
                return {
                    "success": False,
                    "message": f"Database error: {str(e)}",
                    "error_type": "database_error",
                }

        # Execute the role removal
        result = await remove_user_role(user_id, role_name)

        if not result["success"]:
            if result.get("error_type") == "user_not_found":
                raise HTTPException(status_code=404, detail=result["message"])
            elif result.get("error_type") == "role_not_found":
                raise HTTPException(status_code=404, detail=result["message"])
            elif result.get("user_didnt_have_role"):
                # Return 200 for user not having role (not an error)
                return JSONResponse(content=result, status_code=200)
            else:
                raise HTTPException(status_code=500, detail=result["message"])

        print(f"[remove_role_from_user] Role removal successful: {result['message']}")
        return JSONResponse(content=result, status_code=200)

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        await notify_by_bot(
            f"**[API: remove_role_from_user]** \n\n Error removing role from user: user_id={user_id}, role_name={role_name if 'role_name' in locals() else 'unknown'}, error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(
            status_code=500, detail=f"Error removing role from user: {str(e)}"
        )


# Event Management Admin API
@router.get("/events/getAll")
async def get_events(
    request: Request,
    current_user: CustomUser = Depends(require_admin_role),
    platform: Optional[str] = None,
):
    """
    Get list of events with only name and header_photo URL.
    """
    print(f"[get_events] API called with user_id: {current_user.id}")

    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:
        events_qs = Event.objects.only("title", "header_photo", "eventId")
        events = await database_sync_to_async(list)(events_qs)

        event_list = []
        for event in events:
            try:
                header_photo_url = (
                    event.header_photo.url if event.header_photo else None
                )
            except Exception as e:
                print(
                    f"[get_events] Warning: header_photo error for event {event.eventId}: {e}"
                )
                header_photo_url = None

            event_list.append(
                {
                    "title": event.title,
                    "header_photo": header_photo_url,
                    "eventId": event.eventId,
                }
            )

        return event_list

    except Exception as e:
        await notify_by_bot(
            f"**[API: get_events]** \n\n Error fetching events: error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(status_code=500, detail=f"Error fetching events: {str(e)}")


@router.get("/eventDetails/{event_id}")
async def get_event_detail(
    event_id: UUID,
    request: Request,
    current_user: CustomUser = Depends(require_admin_role),
    platform: Optional[str] = None,
):
    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:
        # Safely print user ID
        user_id = await database_sync_to_async(
            lambda: current_user.id, thread_sensitive=True
        )()
        print(f"[get_event_detail] API called for event_id: {event_id} by {user_id}")

        # Fetch event safely
        event = await database_sync_to_async(get_object_or_404, thread_sensitive=True)(
            Event, eventId=event_id
        )

        # Extract event fields safely
        event_fields = await database_sync_to_async(
            lambda: {
                "eventId": str(event.eventId),
                "stripeProductId": event.stripeProductId,
                "views": event.views,
                "status": event.status,
                "admin_status": event.admin_status,
                "title": event.title,
                "event_type": event.event_type,
                "date": event.date.isoformat() if event.date else None,
                "start_time": (
                    event.start_time.isoformat() if event.start_time else None
                ),
                "end_time": event.end_time.isoformat() if event.end_time else None,
                "description": event.description,
                "ticketing": event.ticketing,
                "building_name": event.building_name,
                "display_event_on_college": event.display_event_on_college,
                "country": event.country,
                "street": event.street,
                "apt_suite_unit": event.apt_suite_unit,
                "city": event.city,
                "state": event.state,
                "zip_code": event.zip_code,
                "hide_address": event.hide_address,
                "header_photo": event.header_photo.url if event.header_photo else None,
                "body_photo_one": (
                    event.body_photo_one.url if event.body_photo_one else None
                ),
                "body_photo_two": (
                    event.body_photo_two.url if event.body_photo_two else None
                ),
                "body_photo_three": (
                    event.body_photo_three.url if event.body_photo_three else None
                ),
                "body_photo_four": (
                    event.body_photo_four.url if event.body_photo_four else None
                ),
                "body_photo_five": (
                    event.body_photo_five.url if event.body_photo_five else None
                ),
                "age_restriction": event.age_restriction,
                "crew_discount": event.crew_discount,
                "minimum_crew_size": event.minimum_crew_size,
                "crew_discount_percentage": (
                    float(event.crew_discount_percentage)
                    if event.crew_discount_percentage
                    else None
                ),
                "couponsActivated": event.couponsActivated,
                "show_guest_list": event.show_guest_list,
                "forAllDisplay": event.forAllDisplay,
                "forCollegesDisplay": event.forCollegesDisplay,
                "created_at": (
                    event.created_at.isoformat() if event.created_at else None
                ),
                "updated_at": (
                    event.updated_at.isoformat() if event.updated_at else None
                ),
            },
            thread_sensitive=True,
        )()

        return event_fields

    except Exception as e:
        await notify_by_bot(
            f"**[API: get_event_detail]** \n\n Error fetching event: event_id={event_id}, error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        if "does not exist" in str(e).lower():
            raise HTTPException(status_code=404, detail="Event not found")
        raise HTTPException(status_code=500, detail=f"Error fetching event: {str(e)}")


@router.post("/delete/event/{event_id}")
async def delete_event(
    event_id: UUID,
    request: Request,
    current_user: CustomUser = Depends(require_admin_role),
    platform: Optional[str] = None,
):
    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:
        # Safely print user ID
        user_id = await database_sync_to_async(
            lambda: current_user.id, thread_sensitive=True
        )()
        print(f"[delete_event] API called for event_id: {event_id} by {user_id}")

        # Fetch event safely
        event = await database_sync_to_async(get_object_or_404, thread_sensitive=True)(
            Event, eventId=event_id
        )

        # Delete event safely
        await database_sync_to_async(event.delete, thread_sensitive=True)()

        return {"message": f"Event {event.title} has been deleted"}

    except Exception as e:
        await notify_by_bot(
            f"**[API: delete_event]** \n\n Error deleting event: event_id={event_id}, error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        if "does not exist" in str(e).lower():
            raise HTTPException(status_code=404, detail="Event not found")
        raise HTTPException(status_code=500, detail=f"Error deleting event: {str(e)}")


@router.get("/userAnalytics/signups")
async def get_user_signups(
    request: Request,
    period: str = Query("daily", description="Time period: daily, weekly, or monthly"),
    current_user: CustomUser = Depends(require_admin_role),
    platform: Optional[str] = None,
):
    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def get_signup_data(period):
        if period == "monthly":
            # Get signups grouped by month and count the number of signups per month
            signups = (
                CustomUser.objects.annotate(month=TruncMonth("date_joined"))
                .values("month")
                .annotate(count=Count("id"))
                .order_by("month")
            )

            # Prepare data for the chart
            labels = [
                signup["month"].strftime("%B %Y") for signup in signups
            ]  # Format month as "January 2024"
            counts = [signup["count"] for signup in signups]

        elif period == "weekly":
            # Get signups grouped by week
            signups = (
                CustomUser.objects.annotate(week=TruncWeek("date_joined"))
                .values("week")
                .annotate(count=Count("id"))
                .order_by("week")
            )

            labels = [
                f"Week of {signup['week'].strftime('%d %b %Y')}" for signup in signups
            ]
            counts = [signup["count"] for signup in signups]

        else:  # Daily
            # Get daily signups
            signups = (
                CustomUser.objects.annotate(day=TruncDay("date_joined"))
                .values("day")
                .annotate(count=Count("id"))
                .order_by("day")
            )

            labels = [signup["day"].strftime("%Y-%m-%d") for signup in signups]
            counts = [signup["count"] for signup in signups]

        return {"labels": labels, "counts": counts}

    try:
        result = await get_signup_data(period)
        print(f"[get_user_signups] Returning {len(result['labels'])} data points")
        return result

    except Exception as e:
        await notify_by_bot(
            f"**[API: get_user_signups]** \n\n Error fetching signup analytics: period={period}, error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(
            status_code=500, detail=f"Error fetching signup analytics: {str(e)}"
        )


@router.get("/userAnalytics/logins")
async def get_user_logins(
    request: Request,
    trend: str = Query(
        "general",
        description="Trend type: general, user_activity, time_trends, ip_insights, security, retention",
    ),
    time_frame: str = Query(
        "hourly", description="Time frame for time_trends: hourly, daily, monthly"
    ),
    current_user: CustomUser = Depends(require_admin_role),
    platform: Optional[str] = None,
):
    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def get_login_data(trend_type, time_frame):
        if trend_type == "general":
            data = {
                "total_logins": LoginHistoryModel.objects.count(),
                "unique_users": LoginHistoryModel.objects.values("user")
                .distinct()
                .count(),
                "active_sessions": LoginHistoryModel.objects.filter(
                    logout_time__isnull=True
                ).count(),
                "average_session_duration": LoginHistoryModel.objects.aggregate(
                    avg_duration=Avg(
                        F("session_duration_minutes")
                        + F("session_duration_seconds") / 60
                    )
                )["avg_duration"]
                or 0,
            }

        elif trend_type == "user_activity":
            data = list(
                LoginHistoryModel.objects.values("user__username")
                .annotate(count=Count("id"))
                .order_by("-count")[:10]  # Top 10 users
            )

        elif trend_type == "time_trends":
            trunc_function = {
                "hourly": TruncHour,
                "daily": TruncDay,
                "monthly": TruncMonth,
            }.get(time_frame, TruncHour)

            data = list(
                LoginHistoryModel.objects.annotate(
                    time_period=trunc_function("login_time")
                )
                .values("time_period")
                .annotate(count=Count("id"))
                .order_by("time_period")
            )

            # Convert datetime objects to strings for JSON serialization
            for item in data:
                if item["time_period"]:
                    item["time_period"] = item["time_period"].isoformat()

        elif trend_type == "ip_insights":
            data = list(
                LoginHistoryModel.objects.values("ip_address")
                .annotate(count=Count("id"))
                .order_by("-count")[:10]  # Top 10 IP addresses
            )

        elif trend_type == "security":
            data = {}

            # Track failed login attempts for users who are not in any group
            data["failed_login_attempts"] = LoginHistoryModel.objects.filter(
                user__groups__isnull=True  # Users who are not in any group
            ).count()

            # Track active sessions with users not in any group
            data["active_sessions_with_no_groups"] = LoginHistoryModel.objects.filter(
                logout_time__isnull=True,  # Active sessions
                user__groups__isnull=True,  # Users not in any group
            ).count()

            # Track failed login attempts for users in each group
            group_data = (
                LoginHistoryModel.objects.filter(
                    role__isnull=True  # You can keep role filtering or remove this as per your logic
                )
                .values("user__groups__name")
                .annotate(failed_attempts=Count("id"))
                .order_by("-failed_attempts")
            )

            # Convert queryset to list
            data["failed_login_attempts_by_group"] = list(group_data)

            # Track active sessions grouped by the groups
            active_sessions_by_group = (
                LoginHistoryModel.objects.filter(
                    logout_time__isnull=True  # Active sessions
                )
                .values("user__groups__name")
                .annotate(active_sessions=Count("id"))
                .order_by("-active_sessions")
            )

            # Convert queryset to list
            data["active_sessions_by_group"] = list(active_sessions_by_group)

        elif trend_type == "retention":
            today = now()

            # Get unique users for the last 7 days
            last_7_days = (
                LoginHistoryModel.objects.filter(
                    login_time__gte=today - timedelta(days=7)
                )
                .values("user")
                .distinct()
                .count()
            )  # Count distinct users

            # Get unique users for the last 30 days
            last_30_days = (
                LoginHistoryModel.objects.filter(
                    login_time__gte=today - timedelta(days=30)
                )
                .values("user")
                .distinct()
                .count()
            )  # Count distinct users

            data = {
                "last_7_days": last_7_days,
                "last_30_days": last_30_days,
            }

        else:
            raise ValueError(f"Invalid trend type: {trend_type}")

        return data

    try:
        if trend not in [
            "general",
            "user_activity",
            "time_trends",
            "ip_insights",
            "security",
            "retention",
        ]:
            raise HTTPException(status_code=400, detail="Invalid trend type")

        result = await get_login_data(trend, time_frame)
        print(f"[get_user_logins] Returning login analytics for trend: {trend}")
        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await notify_by_bot(
            f"**[API: get_user_logins]** \n\n Error fetching login analytics: trend={trend}, time_frame={time_frame}, error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(
            status_code=500, detail=f"Error fetching login analytics: {str(e)}"
        )


@router.get("/eventAnalytics/getAll")
async def get_all_events(
    request: Request,
    current_user: CustomUser = Depends(require_admin_role),
    platform: Optional[str] = None,
):
    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def get_events_data():
        """
        Fetch events data with proper sync database operations
        """
        try:
            events_qs = Event.objects.select_related("host").only(
                "eventId",
                "title",
                "date",
                "header_photo",
                "host__username",
                "host__first_name",
                "host__last_name",
            )
            events = list(events_qs)
            events_info = []

            for event in events:
                # Safely get header photo URL
                header_photo_url = None
                try:
                    header_photo_url = (
                        event.header_photo.url if event.header_photo else None
                    )
                except Exception as e:
                    print(
                        f"[get_all_events] Warning: header_photo error for event {event.eventId}: {e}"
                    )

                events_info.append(
                    {
                        "eventId": str(event.eventId),
                        "host": {
                            "username": event.host.username,
                            "first_name": event.host.first_name,
                            "last_name": event.host.last_name,
                        },
                        "title": event.title,
                        "date": event.date.isoformat() if event.date else None,
                        "header_photo_url": header_photo_url,
                    }
                )

            print(f"[get_all_events] Successfully processed {len(events_info)} events")
            return events_info

        except Exception as e:
            print(f"[get_all_events] Database error: {str(e)}")
            raise e

    try:
        events_info = await get_events_data()
        return events_info

    except Exception as e:
        await notify_by_bot(
            f"**[API: get_all_events]** \n\n Error fetching all events analytics: error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(
            status_code=500, detail=f"Error fetching all events analytics: {str(e)}"
        )


@router.get("/eventAnalytics/specific/{event_id}")
async def get_event_specific_analytics(
    event_id: UUID,
    request: Request,
    time_period: str = Query(
        "daily", description="Time period: daily, weekly, or monthly"
    ),
    current_user: CustomUser = Depends(require_admin_role),
    platform: Optional[str] = None,
):
    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def get_event_analytics_data(event_id, time_period):
        try:
            # Verify event exists
            event = get_object_or_404(Event, eventId=event_id)

            # Debug: Confirm time period being used
            print(
                f"[get_event_specific_analytics] DEBUG: Using time_period '{time_period}' for event analytics"
            )

            # Determine truncation function
            trunc_function = {
                "daily": TruncDay,
                "weekly": TruncWeek,
                "monthly": TruncMonth,
            }.get(time_period, TruncDay)

            if time_period not in ["daily", "weekly", "monthly"]:
                print(
                    f"[get_event_specific_analytics] WARNING: Invalid time_period '{time_period}', defaulting to daily"
                )
                trunc_function = TruncDay

            # Basic event information
            event_info = {
                "eventId": str(event.eventId),
                "title": event.title,
                "event_type": event.event_type,
                "ticketing": event.ticketing,
                "date": event.date.isoformat() if event.date else None,
                "status": event.status,
                "admin_status": event.admin_status,
                "views": event.views,
                "host": {
                    "username": event.host.username,
                    "first_name": event.host.first_name,
                    "last_name": event.host.last_name,
                },
                "location": {
                    "city": event.city,
                    "state": event.state,
                    "country": event.country,
                },
            }

            # Determine event ticketing type
            is_free_event = event.ticketing == "Free"
            is_paid_event = event.ticketing == "Paid"

            # Initialize analytics data
            rsvp_trends = []
            paid_ticket_trends = []
            total_rsvps = 0
            total_paid_tickets = 0
            rsvps_on_guestlist = 0
            ticket_types = []
            total_revenue = 0

            # RSVP analytics (only for free events)
            if is_free_event:
                rsvp_trends = list(
                    RSVPTicket.objects.filter(event=event)
                    .annotate(period=trunc_function("created_at"))
                    .values("period")
                    .annotate(count=Count("ticket_id"))
                    .order_by("period")
                )

                # Convert datetime objects to strings
                for item in rsvp_trends:
                    if item["period"]:
                        item["period"] = item["period"].isoformat()

                # RSVP summary
                total_rsvps = RSVPTicket.objects.filter(event=event).count()

                # Guest list visibility analytics
                rsvps_on_guestlist = RSVPTicket.objects.filter(
                    event=event, display_on_guestlist=True
                ).count()

            # Paid ticket analytics (only for paid events)
            if is_paid_event:
                paid_ticket_trends = list(
                    Ticket.objects.filter(event=event)
                    .annotate(period=trunc_function("created_at"))
                    .values("period")
                    .annotate(count=Count("ticketId"))
                    .order_by("period")
                )

                # Convert datetime objects to strings
                for item in paid_ticket_trends:
                    if item["period"]:
                        item["period"] = item["period"].isoformat()

                # Ticket type breakdown
                ticket_types = list(
                    event.tickets.all().values(
                        "ticket_name", "ticket_quantity", "ticket_sold", "ticket_price"
                    )
                )

                # Revenue calculation
                for ticket_type in ticket_types:
                    sold = ticket_type.get("ticket_sold", 0) or 0
                    price = ticket_type.get("ticket_price", 0) or 0
                    total_revenue += sold * float(price)

                # Paid tickets summary
                total_paid_tickets = Ticket.objects.filter(event=event).count()

            # Build response based on event type
            response_data = {
                "event_info": event_info,
                "summary_stats": {
                    "ticketing_type": event.ticketing,
                    "total_attendees": total_rsvps + total_paid_tickets,
                },
                "trends": {},
            }

            # Add RSVP-specific data for free events
            if is_free_event:
                response_data["summary_stats"].update(
                    {
                        "total_rsvps": total_rsvps,
                        "rsvps_on_guestlist": rsvps_on_guestlist,
                    }
                )
                response_data["trends"]["rsvp_trends"] = rsvp_trends

            # Add paid ticket-specific data for paid events
            if is_paid_event:
                response_data["summary_stats"].update(
                    {
                        "total_paid_tickets": total_paid_tickets,
                        "total_revenue": total_revenue,
                        "ticket_types_count": len(ticket_types),
                    }
                )
                response_data["trends"]["paid_ticket_trends"] = paid_ticket_trends
                response_data["ticket_breakdown"] = ticket_types

            return response_data

        except Event.DoesNotExist:
            return None
        except Exception as e:
            print(f"[get_event_specific_analytics] Database error: {str(e)}")
            raise e

    try:
        if time_period not in ["daily", "weekly", "monthly"]:
            raise HTTPException(status_code=400, detail="Invalid time period")

        result = await get_event_analytics_data(event_id, time_period)
        if result is None:
            raise HTTPException(status_code=404, detail="Event not found")

        print(
            f"[get_event_specific_analytics] Returning analytics for event: {result['event_info']['title']}"
        )
        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await notify_by_bot(
            f"**[API: get_event_specific_analytics]** \n\n Error fetching event analytics: event_id={event_id}, time_period={time_period}, error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(
            status_code=500, detail=f"Error fetching event analytics: {str(e)}"
        )


@router.get("/eventAnalytics/overall")
async def get_overall_event_analytics(
    request: Request,
    time_period: str = Query(
        "daily", description="Time period: daily, weekly, or monthly"
    ),
    current_user: CustomUser = Depends(require_admin_role),
    platform: Optional[str] = None,
):
    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def get_overall_analytics_data(time_period):
        """
        🚀 PERFORMANCE OPTIMIZED: This function uses:
        - Database indexes for all time-based and filter queries
        - Efficient QuerySet slicing with LIMIT instead of Python slicing
        - Granular caching strategy
        - Minimal field selection with .only()
        - Batched aggregation queries
        """
        start_time = time.time()
        try:
            # Check cache first (5 minute timeout)
            cache_key = f"overall_analytics_{time_period}"
            cached_data = cache.get(cache_key)
            if cached_data:
                print(
                    f"[get_overall_event_analytics] Returning cached data for {time_period}"
                )
                # Update cache info to show it was cached
                cached_data["cache_info"]["cached"] = True
                return cached_data

            # Check for partial cached data (longer cache for static data)
            static_cache_key = "overall_analytics_static"
            static_data = cache.get(static_cache_key)

            # Determine truncation function
            trunc_function = {
                "daily": TruncDay,
                "weekly": TruncWeek,
                "monthly": TruncMonth,
            }.get(time_period, TruncDay)

            # 🔁 1. Optimized event statistics - combine multiple queries into one
            event_stats = Event.objects.only("eventId", "status").aggregate(
                total_events=Count("eventId"),
                active_events=Count("eventId", filter=Q(status="active")),
                live_events=Count("eventId", filter=Q(status="live")),
                archived_events=Count("eventId", filter=Q(status="archived")),
            )

            # 🔁 2. FIXED: Simplified and accurate revenue calculation
            total_revenue = 0
            try:
                # Method 1: Direct calculation from PaidFreeTicket model (most accurate)
                revenue_data = PaidFreeTicket.objects.filter(
                    ticket_sold__gt=0, ticket_price__gt=0
                ).aggregate(total_revenue=Sum(F("ticket_sold") * F("ticket_price")))
                total_revenue = float(revenue_data["total_revenue"] or 0)

                # Method 2: If no revenue from PaidFreeTicket, calculate from successful Ticket purchases
                if total_revenue == 0:
                    # Get all successful ticket purchases and sum their ticket type prices
                    successful_tickets = (
                        Ticket.objects.filter(status="Valid")
                        .select_related("event")
                        .prefetch_related("event__tickets")
                    )

                    for ticket in successful_tickets:
                        try:
                            # Find the first available ticket type for this event
                            # In a real scenario, you'd want to match by ticket_type_id or similar
                            ticket_type = ticket.event.tickets.first()
                            if ticket_type and ticket_type.ticket_price:
                                total_revenue += float(ticket_type.ticket_price)
                        except Exception:
                            # Skip problematic tickets
                            continue

                print(
                    f"[get_overall_event_analytics] DEBUG: Calculated total revenue: ${total_revenue}"
                )
            except Exception as e:
                print(
                    f"[get_overall_event_analytics] Revenue calculation error: {str(e)}"
                )
                # Final fallback: estimate based on average ticket price
                try:
                    paid_tickets_count = Ticket.objects.filter(status="Valid").count()
                    avg_price = PaidFreeTicket.objects.filter(
                        ticket_price__gt=0
                    ).aggregate(avg_price=Avg("ticket_price"))["avg_price"]
                    total_revenue = paid_tickets_count * float(avg_price or 25.0)
                except Exception:
                    total_revenue = 0.0  # Final fallback

            # 📊 3. Total tickets - use count() instead of loading all records
            total_rsvps = RSVPTicket.objects.count()
            total_paid_tickets = Ticket.objects.count()

            # 🕒 4. Event creation trends - limit to last 90 periods for performance
            event_creation_trends = list(
                Event.objects.annotate(period=trunc_function("created_at"))
                .values("period")
                .annotate(count=Count("eventId"))
                .order_by("-period")[:90]  # Last 90 periods (DESC order)
            )
            # Reverse to get chronological order
            event_creation_trends.reverse()

            # Convert datetime objects to strings
            for item in event_creation_trends:
                if item["period"]:
                    item["period"] = item["period"].isoformat()

            # 📊 5. Event type distribution - use .only() for efficiency
            event_type_distribution = list(
                Event.objects.only("event_type")
                .values("event_type")
                .annotate(count=Count("eventId"))
                .order_by("-count")
            )

            # 📊 6. Geographic distribution - use .only() and limit to top 10
            geographic_distribution = list(
                Event.objects.only("state")
                .values("state")
                .annotate(count=Count("eventId"))
                .order_by("-count")[:10]
            )

            # 🕒 7. RSVP trends - limit to last 90 periods
            overall_rsvp_trends = list(
                RSVPTicket.objects.annotate(period=trunc_function("created_at"))
                .values("period")
                .annotate(count=Count("ticket_id"))
                .order_by("-period")[:90]
            )
            # Reverse to get chronological order
            overall_rsvp_trends.reverse()

            # Convert datetime objects to strings
            for item in overall_rsvp_trends:
                if item["period"]:
                    item["period"] = item["period"].isoformat()

            # 🕒 8. Paid ticket trends - limit to last 90 periods
            overall_paid_ticket_trends = list(
                Ticket.objects.annotate(period=trunc_function("created_at"))
                .values("period")
                .annotate(count=Count("ticketId"))
                .order_by("-period")[:90]
            )
            # Reverse to get chronological order
            overall_paid_ticket_trends.reverse()

            # Convert datetime objects to strings
            for item in overall_paid_ticket_trends:
                if item["period"]:
                    item["period"] = item["period"].isoformat()

            # 📈 9. FIXED: Accurate popular events with optimized attendee counting
            # Use subqueries to efficiently calculate attendee counts

            popular_events = list(
                Event.objects.only("eventId", "title", "event_type", "date", "views")
                .select_related("host")
                .annotate(
                    rsvp_count=Subquery(
                        RSVPTicket.objects.filter(event=OuterRef("pk")).aggregate(
                            count=Count("ticket_id")
                        )["count"]
                    )
                    or 0,
                    paid_ticket_count=Subquery(
                        Ticket.objects.filter(event=OuterRef("pk")).aggregate(
                            count=Count("ticketId")
                        )["count"]
                    )
                    or 0,
                )
                .annotate(total_attendees=F("rsvp_count") + F("paid_ticket_count"))
                .filter(total_attendees__gt=0)  # Only events with attendees
                .order_by("-total_attendees")[:10]
                .values(
                    "eventId",
                    "title",
                    "event_type",
                    "date",
                    "views",
                    "host__username",
                    "rsvp_count",
                    "paid_ticket_count",
                    "total_attendees",
                )
            )

            # Convert UUIDs and dates to strings
            for event in popular_events:
                event["eventId"] = str(event["eventId"])
                if event["date"]:
                    event["date"] = event["date"].isoformat()

            # 📈 10. Host performance analytics - optimized query
            top_hosts = list(
                Event.objects.only("host")
                .select_related("host")
                .values("host__username", "host__first_name", "host__last_name")
                .annotate(
                    event_count=Count("eventId"),
                    total_rsvps=Count("rsvp_tickets", distinct=True),
                    total_paid_tickets=Count("ticket", distinct=True),
                )
                .order_by("-event_count")[:10]
            )

            result = {
                "summary_stats": {
                    "total_events": event_stats["total_events"],
                    "active_events": event_stats["active_events"],
                    "live_events": event_stats["live_events"],
                    "archived_events": event_stats["archived_events"],
                    "total_rsvps": total_rsvps,
                    "total_paid_tickets": total_paid_tickets,
                    "total_attendees": total_rsvps + total_paid_tickets,
                    "total_revenue": total_revenue,
                },
                "trends": {
                    "event_creation_trends": event_creation_trends,
                    "rsvp_trends": overall_rsvp_trends,
                    "paid_ticket_trends": overall_paid_ticket_trends,
                },
                "distributions": {
                    "event_type_distribution": event_type_distribution,
                    "geographic_distribution": geographic_distribution,
                },
                "popular_events": popular_events,
                "top_hosts": top_hosts,
                "cache_info": {
                    "cached": False,
                    "time_period": time_period,
                    "cache_duration": "5 minutes",
                    "query_time_seconds": round(time.time() - start_time, 3),
                },
            }

            # 📈 11. Smart caching strategy
            # Cache full result for 5 minutes
            cache.set(cache_key, result, timeout=300)

            # Cache static data (event stats, distributions) for 15 minutes
            static_data = {
                "summary_stats": result["summary_stats"],
                "distributions": result["distributions"],
            }
            cache.set(static_cache_key, static_data, timeout=900)  # 15 minutes

            print(
                f"[get_overall_event_analytics] Cached analytics data for {time_period} (full: 5min, static: 15min)"
            )

            return result

        except Exception as e:
            print(f"[get_overall_event_analytics] Database error: {str(e)}")
            raise e

    try:
        if time_period not in ["daily", "weekly", "monthly"]:
            raise HTTPException(status_code=400, detail="Invalid time period")

        result = await get_overall_analytics_data(time_period)
        print(
            f"[get_overall_event_analytics] Returning overall analytics with {result['summary_stats']['total_events']} total events"
        )
        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await notify_by_bot(
            f"**[API: get_overall_event_analytics]** \n\n Error fetching overall event analytics: time_period={time_period}, error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(
            status_code=500, detail=f"Error fetching overall event analytics: {str(e)}"
        )


# COLLEGE MANAGEMENT ADMIN API
@router.get("/colleges/getAll")
async def get_colleges(
    request: Request,
    current_user: CustomUser = Depends(require_admin_role),
    platform: Optional[str] = None,
):
    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def get_colleges_data():
        """
        Optimized database query to fetch all college data with student and event counts.
        """
        try:
            # Use select_related and annotate to get all data in efficient queries
            colleges_qs = (
                College.objects.select_related("created_by")
                .annotate(
                    student_count=Count("membership", distinct=True),
                    event_count=Count("college_events", distinct=True),
                )
                .order_by("name")
            )

            college_list = []
            for college in colleges_qs:
                # Safely get file URLs with error handling
                logo_url = None
                campus_image_url = None

                try:
                    logo_url = college.logo.url if college.logo else None
                except Exception as e:
                    print(
                        f"[get_colleges] Warning: logo error for college {college.name}: {e}"
                    )

                try:
                    campus_image_url = (
                        college.campus_image.url if college.campus_image else None
                    )
                except Exception as e:
                    print(
                        f"[get_colleges] Warning: campus_image error for college {college.name}: {e}"
                    )

                # Safely get creator username
                created_by_username = None
                try:
                    created_by_username = (
                        college.created_by.username if college.created_by else None
                    )
                except Exception as e:
                    print(
                        f"[get_colleges] Warning: created_by error for college {college.name}: {e}"
                    )

                college_list.append(
                    {
                        "name": college.name,
                        "logo": logo_url,
                        "college_id": str(college.collegeId),
                        "city": college.city,
                        "state": college.state,
                        "campus_image": campus_image_url,
                        "student_count": college.student_count,
                        "event_count": college.event_count,
                        "created_by": created_by_username,
                        "address": college.address,
                        "zip_code": college.zip_code,
                        "country": college.country,
                        "motto": college.motto,
                        "email_domain": college.email_domain,
                        "contact_website": college.contact_website,
                    }
                )

            print(f"[get_colleges] Successfully processed {len(college_list)} colleges")
            return college_list

        except Exception as e:
            print(f"[get_colleges] Database error: {str(e)}")
            raise e

    try:
        college_list = await get_colleges_data()
        return college_list

    except Exception as e:
        await notify_by_bot(
            f"**[API: get_colleges]** \n\n Error fetching colleges: error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(
            status_code=500, detail=f"Error fetching colleges: {str(e)}"
        )


@router.get("/colleges/create/form/fields")
async def get_college_create_form_fields(
    request: Request,
    platform: Optional[str] = None,
):
    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:
        return {
            "fields": [
                {
                    "name": "name",
                    "type": "text",
                    "label": "College Name",
                    "required": True,
                    "placeholder": "Enter college name",
                },
                {
                    "name": "description",
                    "type": "textarea",
                    "label": "Description",
                    "required": False,
                    "placeholder": "Enter college description",
                },
                {
                    "name": "logo",
                    "type": "file",
                    "label": "College Logo",
                    "required": False,
                    "accept": "image/*",
                },
            ]
        }
    except Exception as e:
        await notify_by_bot(
            f"**[API: get_college_create_form_fields]** \n\n Error fetching form fields: error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(
            status_code=500, detail=f"Error fetching form fields: {str(e)}"
        )


@router.post("/colleges/create")
async def create_college(
    request: Request,
    current_user: CustomUser = Depends(require_admin_role),
    platform: Optional[str] = None,
):
    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:
        form_data = await request.form()
        file_data = await request.form()

        @database_sync_to_async
        def validate_and_create_college(form_data, file_data, created_by_user):
            print(f"[create_college] Form data keys: {list(form_data.keys())}")
            print(f"[create_college] File data keys: {list(file_data.keys())}")

            # Create and validate the form with both regular data and files
            form = CollegeForm(form_data, file_data)

            if form.is_valid():
                # Save the college with the current user as creator
                college = form.save(commit=False)
                college.created_by = created_by_user
                college.save()

                # Log successful file attachments
                if college.logo:
                    print(
                        f"[create_college] Logo saved successfully: {college.logo.name}"
                    )
                if college.campus_image:
                    print(
                        f"[create_college] Campus image saved successfully: {college.campus_image.name}"
                    )

                return None, status.HTTP_201_CREATED
            else:
                print(f"[create_college] Form validation errors: {form.errors}")
                return form.errors, status.HTTP_400_BAD_REQUEST

        # Run validation and college creation
        errors, status_code = await validate_and_create_college(
            form_dict, file_dict, current_user
        )

        if errors:
            print(f"[create_college] College creation failed with errors: {errors}")
            return JSONResponse(content=errors, status_code=status_code)
        else:
            print(
                f"[create_college] College created successfully with status code {status_code}"
            )
            return JSONResponse(
                content={"message": "College created successfully"},
                status_code=status_code,
            )
    except Exception as e:
        traceback_str = traceback.format_exc()
        print(f"[create_college] College creation error: {str(e)}\n{traceback_str}")
        await notify_by_bot(
            f"**[API: create_college]** \n\n Error creating college: error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(status_code=500, detail=f"Error creating college: {str(e)}")


@router.post("/colleges/{college_id}/delete")
async def delete_college(
    college_id: UUID,
    request: Request,
    current_user: CustomUser = Depends(require_admin_role),
    platform: Optional[str] = None,
):
    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:
        college = await database_sync_to_async(get_object_or_404)(
            College, collegeId=college_id
        )
        await database_sync_to_async(college.delete)()

        return {"message": f"College {college.name} has been deleted"}

    except Exception as e:
        await notify_by_bot(
            f"**[API: delete_college]** \n\n Error deleting college: college_id={college_id}, error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        if "does not exist" in str(e).lower():
            raise HTTPException(status_code=404, detail="College not found")
        raise HTTPException(status_code=500, detail=f"Error deleting college: {str(e)}")


@router.get("/colleges/{college_id}/info")
async def get_college_info(
    college_id: UUID,
    request: Request,
    current_user: CustomUser = Depends(require_admin_role),
    platform: Optional[str] = None,
):
    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def get_college_details(college_id):
        try:
            # Get college with related data
            college = get_object_or_404(College, collegeId=college_id)

            # Get member count
            member_count = UserProfile.objects.filter(college=college).count()

            # Get event count through CollegeEventLink
            event_count = 0
            try:
                event_count = CollegeEventLink.objects.filter(college=college).count()
            except Exception as e:
                print(
                    f"[get_college_info] Warning: Could not get event count: {str(e)}"
                )

            # Get event count from hosted events as well
            hosted_events_count = 0
            try:
                # Get user profiles for this college first
                college_user_profiles = UserProfile.objects.filter(college=college)
                college_users = [
                    profile.user for profile in college_user_profiles if profile.user
                ]

                if college_users:
                    hosted_events_count = Event.objects.filter(
                        display_event_on_college=True, host__in=college_users
                    ).count()
            except Exception as e:
                print(
                    f"[get_college_info] Warning: Could not get hosted events count: {str(e)}"
                )

            total_events = event_count + hosted_events_count

            # Safely get file URLs
            logo_url = None
            campus_image_url = None

            try:
                logo_url = college.logo.url if college.logo else None
            except Exception as e:
                print(
                    f"[get_college_info] Warning: logo error for college {college.name}: {e}"
                )

            try:
                campus_image_url = (
                    college.campus_image.url if college.campus_image else None
                )
            except Exception as e:
                print(
                    f"[get_college_info] Warning: campus_image error for college {college.name}: {e}"
                )

            # Safely get creator information
            created_by_info = None
            if college.created_by:
                try:
                    created_by_info = {
                        "id": college.created_by.id,
                        "username": college.created_by.username,
                        "first_name": college.created_by.first_name,
                        "last_name": college.created_by.last_name,
                        "email": college.created_by.email,
                    }
                except Exception as e:
                    print(
                        f"[get_college_info] Warning: created_by error for college {college.name}: {e}"
                    )

            # Build comprehensive college data
            college_data = {
                "collegeId": str(college.collegeId),
                "name": college.name,
                "address": college.address,
                "city": college.city,
                "state": college.state,
                "zip_code": college.zip_code,
                "country": college.country,
                "motto": college.motto,
                "email_domain": college.email_domain,
                "contact_website": college.contact_website,
                "logo": logo_url,
                "campus_image": campus_image_url,
                "created_by": created_by_info,
                "stats": {
                    "member_count": member_count,
                    "event_count": total_events,
                    "linked_events": event_count,
                    "hosted_events": hosted_events_count,
                },
            }

            print(
                f"[get_college_info] Successfully retrieved info for college: {college.name}"
            )
            return college_data

        except College.DoesNotExist:
            print(f"[get_college_info] College not found with ID: {college_id}")
            return None
        except Exception as e:
            print(f"[get_college_info] Database error: {str(e)}")
            raise e

    try:
        college_info = await get_college_details(college_id)
        if college_info is None:
            raise HTTPException(status_code=404, detail="College not found")

        print(f"[get_college_info] Returning info for college: {college_info['name']}")
        return college_info

    except Exception as e:
        await notify_by_bot(
            f"**[API: get_college_info]** \n\n Error fetching college info: college_id={college_id}, error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        if "does not exist" in str(e).lower():
            raise HTTPException(status_code=404, detail="College not found")
        raise HTTPException(
            status_code=500, detail=f"Error fetching college info: {str(e)}"
        )


@router.get("/colleges/{college_id}/edit/form/fields")
async def get_college_edit_form_fields(
    request: Request,
    platform: Optional[str] = None,
):
    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:
        return {
            "fields": [
                {
                    "name": "name",
                    "type": "text",
                    "label": "College Name",
                    "required": True,
                    "placeholder": "Enter college name",
                },
                {
                    "name": "description",
                    "type": "textarea",
                    "label": "Description",
                    "required": False,
                    "placeholder": "Enter college description",
                },
                {
                    "name": "logo",
                    "type": "file",
                    "label": "College Logo",
                    "required": False,
                    "accept": "image/*",
                },
            ]
        }
    except Exception as e:
        await notify_by_bot(
            f"**[API: get_college_edit_form_fields]** \n\n Error fetching form fields: error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(
            status_code=500, detail=f"Error fetching form fields: {str(e)}"
        )


@router.post("/colleges/{college_id}/edit")
async def edit_college(
    college_id: UUID,
    request: Request,
    current_user: CustomUser = Depends(require_admin_role),
    platform: Optional[str] = None,
):
    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:
        form_data = await request.form()
        file_data = await request.form()

        @database_sync_to_async
        def validate_and_update_college(college_id, form_data, file_data):
            print(f"[edit_college] Form data keys: {list(form_data.keys())}")
            print(f"[edit_college] File data keys: {list(file_data.keys())}")

            try:
                # Get the existing college instance
                college = get_object_or_404(College, collegeId=college_id)
                print(f"[edit_college] Found college: {college.name}")

                # Track what fields are being updated
                updated_fields = []
                changes_made = False

                # Check and update text fields only if they have changed
                text_fields = [
                    "name",
                    "address",
                    "city",
                    "state",
                    "zip_code",
                    "country",
                    "motto",
                    "email_domain",
                    "contact_website",
                ]
                for field in text_fields:
                    if field in form_data and form_data[field]:
                        new_value = form_data[field].strip()
                        current_value = getattr(college, field, "") or ""
                        if new_value != current_value:
                            setattr(college, field, new_value)
                            updated_fields.append(field)
                            changes_made = True
                            print(
                                f"[edit_college] Updating {field}: '{current_value}' -> '{new_value}'"
                            )

                # Handle file uploads separately to avoid overwriting existing files
                files_updated = []

                # Handle logo upload
                if "logo" in file_data:
                    old_logo = college.logo.name if college.logo else "None"
                    college.logo = file_data["logo"]
                    files_updated.append("logo")
                    changes_made = True
                    print(
                        f"[edit_college] Updating logo: '{old_logo}' -> '{file_data['logo'].name}'"
                    )
                elif "logo" in form_data:
                    # Check if form indicates logo should be cleared
                    if not form_data["logo"] or form_data["logo"] == "":
                        if college.logo:
                            print(
                                f"[edit_college] Logo field present but empty - keeping existing logo"
                            )

                # Handle campus_image upload
                if "campus_image" in file_data:
                    old_image = (
                        college.campus_image.name if college.campus_image else "None"
                    )
                    college.campus_image = file_data["campus_image"]
                    files_updated.append("campus_image")
                    changes_made = True
                    print(
                        f"[edit_college] Updating campus_image: '{old_image}' -> '{file_data['campus_image'].name}'"
                    )
                elif "campus_image" in form_data:
                    # Check if form indicates campus_image should be cleared
                    if not form_data["campus_image"] or form_data["campus_image"] == "":
                        print(
                            f"[edit_college] Campus image field present but empty - keeping existing image"
                        )

                # Only save if there are actual changes
                if changes_made:
                    college.save()
                    print(
                        f"[edit_college] College updated successfully. Fields changed: {updated_fields + files_updated}"
                    )

                    # Log file updates specifically
                    if files_updated:
                        if "logo" in files_updated and college.logo:
                            print(
                                f"[edit_college] Logo saved successfully: {college.logo.name}"
                            )
                        if "campus_image" in files_updated and college.campus_image:
                            print(
                                f"[edit_college] Campus image saved successfully: {college.campus_image.name}"
                            )

                    return None, status.HTTP_200_OK
                else:
                    print(f"[edit_college] No changes detected - college not updated")
                    return {
                        "message": "No changes were made to the college"
                    }, status.HTTP_200_OK

            except College.DoesNotExist:
                print(f"[edit_college] College not found with ID: {college_id}")
                return {"error": "College not found"}, status.HTTP_404_NOT_FOUND
            except Exception as e:
                print(f"[edit_college] Database error: {str(e)}")
                return {
                    "error": f"Database error: {str(e)}"
                }, status.HTTP_500_INTERNAL_SERVER_ERROR

        # Run validation and college update
        errors, status_code = await validate_and_update_college(
            college_id, form_dict, file_dict
        )

        if errors:
            print(f"[edit_college] College update failed with errors: {errors}")
            return JSONResponse(content=errors, status_code=status_code)
        else:
            print(
                f"[edit_college] College updated successfully with status code {status_code}"
            )
            return JSONResponse(
                content={"message": "College updated successfully"},
                status_code=status_code,
            )
    except Exception as e:
        traceback_str = traceback.format_exc()
        print(f"[edit_college] College update error: {str(e)}\n{traceback_str}")
        await notify_by_bot(
            f"**[API: edit_college]** \n\n Error editing college: college_id={college_id}, error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(status_code=500, detail=f"Error editing college: {str(e)}")


@router.get("/colleges/{college_id}/members")
async def get_college_members(
    college_id: UUID,
    request: Request,
    current_user: CustomUser = Depends(require_admin_role),
    platform: Optional[str] = None,
):
    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def get_members_data(college_id):
        try:
            # First verify the college exists
            college = get_object_or_404(College, collegeId=college_id)
            print(f"[get_college_members] Found college: {college.name}")

            # Get all user profiles associated with this college
            user_profiles = UserProfile.objects.filter(college=college).select_related(
                "user"
            )

            # Also get direct memberships if they exist
            memberships = Membership.objects.filter(college=college).select_related(
                "user"
            )

            # Combine users from both sources and avoid duplicates
            member_users = set()

            # Add users from profiles
            for profile in user_profiles:
                if profile.user:
                    member_users.add(profile.user)

            # Add users from memberships
            for membership in memberships:
                if membership.user:
                    member_users.add(membership.user)

            print(
                f"[get_college_members] Found {len(member_users)} members for college {college.name}"
            )

            # Build member data
            members_list = []
            for user in member_users:
                try:
                    # Get user groups
                    user_groups = list(user.groups.values_list("name", flat=True))

                    # Get profile photo if it exists
                    profile_photo_url = None
                    try:
                        if (
                            hasattr(user, "user_profile")
                            and user.user_profile
                            and user.user_profile.profile_photo
                        ):
                            profile_photo_url = user.user_profile.profile_photo.url
                    except Exception as e:
                        print(
                            f"[get_college_members] Warning: Could not get profile photo for user {user.id}: {str(e)}"
                        )

                    # Check if user is campus manager for this college
                    is_campus_manager = False
                    try:
                        if hasattr(user, "user_profile") and user.user_profile:
                            is_campus_manager = user.user_profile.is_campus_manager
                    except Exception as e:
                        print(
                            f"[get_college_members] Warning: Could not check campus manager status for user {user.id}: {str(e)}"
                        )

                    member_data = {
                        "id": user.id,
                        "user_id": str(user.user_id),
                        "username": user.username,
                        "email": user.email,
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                        "is_active": user.is_active,
                        "is_suspended": user.is_suspended,
                        "is_campus_manager": is_campus_manager,
                        "groups": user_groups,
                        "date_joined": (
                            user.date_joined.isoformat() if user.date_joined else None
                        ),
                        "profile_photo": profile_photo_url,
                    }
                    members_list.append(member_data)

                except Exception as e:
                    print(
                        f"[get_college_members] Warning: Error processing member {user.id}: {str(e)}"
                    )
                    continue

            # Sort members by date joined (newest first)
            members_list.sort(key=lambda x: x["date_joined"] or "", reverse=True)

            return {
                "college": {
                    "id": str(college.collegeId),
                    "name": college.name,
                    "city": college.city,
                    "state": college.state,
                },
                "members": members_list,
                "total_members": len(members_list),
            }

        except College.DoesNotExist:
            print(f"[get_college_members] College not found with ID: {college_id}")
            return None
        except Exception as e:
            print(f"[get_college_members] Database error: {str(e)}")
            raise e

    try:
        members_data = await get_members_data(college_id)
        if members_data is None:
            raise HTTPException(status_code=404, detail="College not found")

        print(
            f"[get_college_members] Returning {members_data['total_members']} members for college {members_data['college']['name']}"
        )
        return members_data

    except Exception as e:
        await notify_by_bot(
            f"**[API: get_college_members]** \n\n Error fetching college members: college_id={college_id}, error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        if "does not exist" in str(e).lower():
            raise HTTPException(status_code=404, detail="College not found")
        raise HTTPException(
            status_code=500, detail=f"Error fetching college members: {str(e)}"
        )


@router.post("/colleges/{college_id}/members/{user_id}/remove")
async def remove_college_member(
    college_id: UUID,
    user_id: int,
    request: Request,
    current_user: CustomUser = Depends(require_admin_role),
    platform: Optional[str] = None,
):
    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def remove_member_from_college(college_id, user_id):
        try:
            # First verify the college exists
            college = get_object_or_404(College, collegeId=college_id)
            print(f"[remove_college_member] Found college: {college.name}")

            # Verify the user exists
            user = get_object_or_404(CustomUser, id=user_id)
            print(f"[remove_college_member] Found user: {user.username}")

            # Track what was removed
            removed_items = []

            # Remove college association from UserProfile
            try:
                if hasattr(user, "user_profile") and user.user_profile:
                    user_profile = user.user_profile
                    if user_profile.college == college:
                        user_profile.college = None
                        user_profile.save()
                        removed_items.append("user_profile_college_association")
                        print(
                            f"[remove_college_member] Removed college association from user profile"
                        )
            except Exception as e:
                print(
                    f"[remove_college_member] Warning: Could not remove user profile college association: {str(e)}"
                )

            # Remove Membership records
            try:
                deleted_memberships = Membership.objects.filter(
                    user=user, college=college
                ).delete()
                if deleted_memberships[0] > 0:
                    removed_items.append(f"membership_records_{deleted_memberships[0]}")
                    print(
                        f"[remove_college_member] Removed {deleted_memberships[0]} membership record(s)"
                    )
            except Exception as e:
                print(
                    f"[remove_college_member] Warning: Could not remove membership records: {str(e)}"
                )

            if not removed_items:
                return {
                    "success": False,
                    "message": f"User {user.username} was not a member of {college.name}",
                    "removed_items": [],
                }

            return {
                "success": True,
                "message": f"Successfully removed {user.username} from {college.name}",
                "removed_items": removed_items,
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                },
                "college": {
                    "id": str(college.collegeId),
                    "name": college.name,
                },
            }

        except College.DoesNotExist:
            print(f"[remove_college_member] College not found with ID: {college_id}")
            return {"success": False, "message": "College not found"}
        except CustomUser.DoesNotExist:
            print(f"[remove_college_member] User not found with ID: {user_id}")
            return {"success": False, "message": "User not found"}
        except Exception as e:
            print(f"[remove_college_member] Database error: {str(e)}")
            raise e

    try:
        result = await remove_member_from_college(college_id, user_id)

        if not result["success"]:
            raise HTTPException(status_code=404, detail=result["message"])

        print(
            f"[remove_college_member] Successfully removed member: {result['message']}"
        )
        return result

    except Exception as e:
        await notify_by_bot(
            f"**[API: remove_college_member]** \n\n Error removing college member: college_id={college_id}, user_id={user_id}, error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(
            status_code=500, detail=f"Error removing college member: {str(e)}"
        )


@router.get("/colleges/{college_id}/events")
async def get_college_events(
    college_id: UUID,
    request: Request,
    current_user: CustomUser = Depends(require_admin_role),
    platform: Optional[str] = None,
):
    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def get_events_data(college_id):
        try:
            # First verify the college exists
            college = get_object_or_404(College, collegeId=college_id)
            print(f"[get_college_events] Found college: {college.name}")

            # Get events in multiple ways:
            # 1. Events that are set to display on this college
            # 2. Events hosted by users from this college
            # 3. Events linked to this college through CollegeEventLink

            events_set = set()

            # Method 1: Events with display_event_on_college = True and hosted by users from this college
            college_hosted_events = Event.objects.filter(
                display_event_on_college=True, host__user_profile__college=college
            )

            for event in college_hosted_events:
                events_set.add(event)

            # Method 2: Events linked through CollegeEventLink
            try:
                college_event_links = CollegeEventLink.objects.filter(
                    college=college
                ).select_related("event")
                for link in college_event_links:
                    if link.event:
                        events_set.add(link.event)
            except Exception as e:
                print(
                    f"[get_college_events] Warning: Could not fetch CollegeEventLink: {str(e)}"
                )

            print(
                f"[get_college_events] Found {len(events_set)} events for college {college.name}"
            )

            # Build events data
            events_list = []
            for event in events_set:
                try:
                    # Get event photos safely
                    header_photo_url = None
                    try:
                        header_photo_url = (
                            event.header_photo.url if event.header_photo else None
                        )
                    except Exception as e:
                        print(
                            f"[get_college_events] Warning: Could not get header photo for event {event.eventId}: {str(e)}"
                        )

                    event_data = {
                        "eventId": str(event.eventId),
                        "title": event.title,
                        "event_type": event.event_type,
                        "date": event.date.isoformat() if event.date else None,
                        "header_photo": header_photo_url,
                        "created_at": (
                            event.created_at.isoformat() if event.created_at else None
                        ),
                    }
                    events_list.append(event_data)

                except Exception as e:
                    print(
                        f"[get_college_events] Warning: Error processing event {event.eventId}: {str(e)}"
                    )
                    continue

            # Sort events by date (upcoming events first, then by creation date)
            events_list.sort(
                key=lambda x: (
                    x["date"] or "9999-12-31",  # Put events without dates at the end
                    x["created_at"] or "",
                ),
                reverse=False,
            )

            return {
                "college": {
                    "id": str(college.collegeId),
                    "name": college.name,
                    "city": college.city,
                    "state": college.state,
                },
                "events": events_list,
                "total_events": len(events_list),
                "event_stats": {
                    "total_events": len(events_list),
                    "upcoming_events": len(
                        [
                            e
                            for e in events_list
                            if e["date"]
                            and e["date"] >= datetime.now().date().isoformat()
                        ]
                    ),
                    "past_events": len(
                        [
                            e
                            for e in events_list
                            if e["date"]
                            and e["date"] < datetime.now().date().isoformat()
                        ]
                    ),
                },
            }

        except College.DoesNotExist:
            print(f"[get_college_events] College not found with ID: {college_id}")
            return None
        except Exception as e:
            print(f"[get_college_events] Database error: {str(e)}")
            raise e

    try:
        events_data = await get_events_data(college_id)
        if events_data is None:
            raise HTTPException(status_code=404, detail="College not found")

        print(
            f"[get_college_events] Returning {events_data['total_events']} events for college {events_data['college']['name']}"
        )
        return events_data

    except Exception as e:
        await notify_by_bot(
            f"**[API: get_college_events]** \n\n Error fetching college events: college_id={college_id}, error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        if "does not exist" in str(e).lower():
            raise HTTPException(status_code=404, detail="College not found")
        raise HTTPException(
            status_code=500, detail=f"Error fetching college events: {str(e)}"
        )


@router.get("/member/{user_id}/preferences")
async def get_member_preferences(
    user_id: str,
    request: Request,
    current_user: CustomUser = Depends(require_admin_role),
    platform: Optional[str] = None,
):
    """
    Get user preferences for a specific member - requires Admin or Super Admin role.
    """
    print(f"[get_member_preferences] API called for user_id: {user_id}")

    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def get_user_preferences_data(user_id):
        try:
            # First verify the user exists - handle both UUID and integer IDs
            try:
                # Try UUID first (primary key format)
                from uuid import UUID

                uuid_obj = UUID(user_id)
                user = get_object_or_404(CustomUser, user_id=uuid_obj)
            except ValueError:
                # If not UUID, try integer ID
                try:
                    int_id = int(user_id)
                    user = get_object_or_404(CustomUser, id=int_id)
                except ValueError:
                    raise CustomUser.DoesNotExist("Invalid user ID format")

            print(f"[get_member_preferences] Found user: {user.username}")

            # Get user preferences
            from accountManagementApp.models import UserPreferences

            try:
                user_preferences = UserPreferences.objects.get(user=user)
                print(
                    f"[get_member_preferences] Found preferences for user: {user.username}"
                )

                # Build preferences data - handle JSON fields safely
                preferences_data = {
                    "user_info": {
                        "id": user.pk,
                        "username": user.username,
                        "email": user.email,
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                    },
                    "preferences_completed": user_preferences.preferences_completed,
                    "preferences": {
                        "interests": user_preferences.interests,
                        "vibe": user_preferences.vibe,
                        "people_to_meet": user_preferences.people_to_meet,
                        "preferred_times": user_preferences.preferred_times,
                    },
                    "college_info": {
                        "college": (
                            user_preferences.college.name
                            if user_preferences.college
                            else None
                        ),
                        "college_id": (
                            str(user_preferences.college.collegeId)
                            if user_preferences.college
                            else None
                        ),
                    },
                    "metadata": {
                        "preference_created_at": (
                            user_preferences.preference_created_at.isoformat()
                            if user_preferences.preference_created_at
                            else None
                        ),
                    },
                }

                return preferences_data

            except UserPreferences.DoesNotExist:
                print(
                    f"[get_member_preferences] No preferences found for user: {user.username}"
                )
                # Return default structure with null values
                return {
                    "user_info": {
                        "id": user.pk,
                        "username": user.username,
                        "email": user.email,
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                    },
                    "preferences_completed": False,
                    "preferences": {
                        "interests": None,
                        "vibe": None,
                        "people_to_meet": None,
                        "preferred_times": None,
                    },
                    "college_info": {
                        "college": None,
                        "college_id": None,
                    },
                    "metadata": {
                        "preference_created_at": None,
                        "note": "No preferences record found - user has not completed preferences setup",
                    },
                }

        except CustomUser.DoesNotExist:
            print(f"[get_member_preferences] User not found with ID: {user_id}")
            return None
        except Exception as e:
            print(f"[get_member_preferences] Database error: {str(e)}")
            raise e

    try:
        preferences_data = await get_user_preferences_data(user_id)
        if preferences_data is None:
            raise HTTPException(status_code=404, detail="User not found")

        print(
            f"[get_member_preferences] Returning preferences for user: {preferences_data['user_info']['username']}"
        )
        return preferences_data

    except Exception as e:
        await notify_by_bot(
            f"**[API: get_member_preferences]** \n\n Error fetching member preferences: user_id={user_id}, error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        if "does not exist" in str(e).lower():
            raise HTTPException(status_code=404, detail="User not found")
        raise HTTPException(
            status_code=500, detail=f"Error fetching member preferences: {str(e)}"
        )


@router.get("/tide/ambassador/applications")
async def get_tide_ambassador_applications(
    request: Request,
    current_user: CustomUser = Depends(require_marketing_lead_role),
    platform: Optional[str] = None,
):
    print(f"[get_tide_ambassador_applications] API called")

    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def get_tide_ambassador_applications_data():
        try:
            applications = AmbassadorApplication.objects.all()
            return [
                {
                    "app_id": str(application.app_id),
                    "full_name": application.full_name,
                    "status": application.status,
                    "application_date": application.application_date,
                }
                for application in applications
            ]
        except Exception as e:
            print(f"[get_tide_ambassador_applications] Database error: {str(e)}")
            raise e

    try:
        applications_data = await get_tide_ambassador_applications_data()
        return applications_data
    except Exception as e:
        await notify_by_bot(
            f"**[API: get_tide_ambassador_applications]** \n\n Error fetching tide ambassador applications: error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching tide ambassador applications: {str(e)}",
        )


@router.get("/tide/ambassador/applications/{app_id}")
async def get_tide_ambassador_application(
    app_id: str,
    request: Request,
    current_user: CustomUser = Depends(require_marketing_lead_role),
    platform: Optional[str] = None,
):
    print(f"[get_tide_ambassador_application] API called for app_id: {app_id}")

    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def get_tide_ambassador_application_data(app_id):
        try:
            application = AmbassadorApplication.objects.get(app_id=app_id)
            return {
                "success": True,
                "application": {
                    "app_id": str(application.app_id),
                    "full_name": application.full_name,
                    "college": application.college,
                    "email": application.email,
                    "instagram_handle": application.instagram_handle,
                    "major": application.major,
                    "tiktok_handle": application.tiktok_handle,
                    "graduation_year": application.graduation_year,
                    "status": application.status,
                    "application_date": application.application_date.isoformat(),
                },
                "status_code": status.HTTP_200_OK,
            }
        except AmbassadorApplication.DoesNotExist:
            print(f"[get_tide_ambassador_application] Application not found: {app_id}")
            return {
                "success": False,
                "error": "Application not found",
                "status_code": status.HTTP_404_NOT_FOUND,
            }
        except Exception as e:
            print(f"[get_tide_ambassador_application] Database error: {str(e)}")
            return {
                "success": False,
                "error": f"Database error: {str(e)}",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            }

    try:
        # Get the application data
        result = await get_tide_ambassador_application_data(app_id)

        status_code = result.pop("status_code", status.HTTP_200_OK)

        if not result.get("success", True):
            print(f"[get_tide_ambassador_application] Error with status {status_code}")
            return JSONResponse(content=result, status_code=status_code)

        print(f"[get_tide_ambassador_application] Application retrieved successfully")
        return JSONResponse(content=result, status_code=status_code)

    except Exception as e:
        print(f"[get_tide_ambassador_application] Unexpected error: {str(e)}")
        await notify_by_bot(
            f"**[API: get_tide_ambassador_application]** \n\n Unexpected error: {str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        return JSONResponse(
            content={"error": "An unexpected error occurred"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get("/ambassador/program/details/form/fields")
async def get_ambassador_program_details_form_fields(
    request: Request,
    current_user: CustomUser = Depends(require_marketing_lead_role),
    platform: Optional[str] = None,
):
    """
    Get form fields for creating/editing ambassador program details - requires Marketing Lead role.
    """
    print(f"[get_ambassador_program_details_form_fields] API called")

    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:
        FormClass = AmbassadorProgramDetailsForm
        fields_info = get_form_fields(FormClass)
        print(
            f"[get_ambassador_program_details_form_fields] Returning form fields, field count: {len(fields_info)}"
        )

        return {
            "success": True,
            "form_fields": fields_info,
            "form_name": "AmbassadorProgramDetailsForm",
            "endpoint_info": {
                "create_url": "/ambassador/program/details/create",
                "edit_url": "/ambassador/program/details/edit",
                "get_details_url": "/ambassador/program/details",
            },
        }

    except Exception as e:
        await notify_by_bot(
            f"**[API: get_ambassador_program_details_form_fields]** \n\n Error fetching form fields: error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(
            status_code=500, detail=f"Error fetching form fields: {str(e)}"
        )


@router.post("/ambassador/program/details/create")
async def create_ambassador_program_details(
    request: Request,
    current_user: CustomUser = Depends(require_marketing_lead_role),
    platform: Optional[str] = None,
):
    """
    Create ambassador program details - requires Marketing Lead role.
    """
    print(f"[create_ambassador_program_details] API called")

    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:
        # Get form data from request
        form_data = await request.form()

        @database_sync_to_async
        def validate_and_create_program_details(form_data):
            try:
                # Check if program details already exist (assuming only one should exist)
                existing_details = AmbassadorProgramDetails.objects.first()
                if existing_details:
                    return {
                        "success": False,
                        "errors": {
                            "general": [
                                "Ambassador program details already exist. Use the edit endpoint to update them."
                            ]
                        },
                        "status_code": status.HTTP_400_BAD_REQUEST,
                    }

                # Create and validate form
                form = AmbassadorProgramDetailsForm(form_data)

                if form.is_valid():
                    # Save the program details
                    program_details = form.save()

                    return {
                        "success": True,
                        "message": "Ambassador program details created successfully!",
                        "program_details": {
                            "id": program_details.id,
                            "description": program_details.description,
                            "documentation_link": program_details.documentation_link,
                        },
                        "status_code": status.HTTP_201_CREATED,
                    }
                else:
                    return {
                        "success": False,
                        "errors": form.errors,
                        "status_code": status.HTTP_400_BAD_REQUEST,
                    }

            except Exception as e:
                return {
                    "success": False,
                    "error": f"Database error: {str(e)}",
                    "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                }

        # Execute creation
        result = await validate_and_create_program_details(form_data)
        status_code = result.pop("status_code", status.HTTP_200_OK)

        if not result.get("success", True):
            return JSONResponse(content=result, status_code=status_code)

        print(
            f"[create_ambassador_program_details] Program details created successfully"
        )
        return JSONResponse(content=result, status_code=status_code)

    except Exception as e:
        await notify_by_bot(
            f"**[API: create_ambassador_program_details]** \n\n Error creating program details: error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(
            status_code=500, detail=f"Error creating program details: {str(e)}"
        )


@router.get("/ambassador/program/details")
async def get_ambassador_program_details(
    request: Request,
    current_user: CustomUser = Depends(require_marketing_lead_role),
    platform: Optional[str] = None,
):
    """
    Get existing ambassador program details - requires Marketing Lead role.
    """
    print(f"[get_ambassador_program_details] API called")

    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:

        @database_sync_to_async
        def get_program_details_data():
            try:
                # Get the first (and presumably only) program details record
                program_details = AmbassadorProgramDetails.objects.first()

                if not program_details:
                    return {
                        "success": False,
                        "message": "No ambassador program details found. Create them first.",
                        "status_code": status.HTTP_404_NOT_FOUND,
                    }

                return {
                    "success": True,
                    "program_details": {
                        "description": program_details.description,
                        "documentation_link": program_details.documentation_link,
                    },
                    "status_code": status.HTTP_200_OK,
                }

            except Exception as e:
                return {
                    "success": False,
                    "error": f"Database error: {str(e)}",
                    "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                }

        # Execute retrieval
        result = await get_program_details_data()
        status_code = result.pop("status_code", status.HTTP_200_OK)

        if not result.get("success", True):
            return JSONResponse(content=result, status_code=status_code)

        print(
            f"[get_ambassador_program_details] Program details retrieved successfully"
        )
        return JSONResponse(content=result, status_code=status_code)

    except Exception as e:
        await notify_by_bot(
            f"**[API: get_ambassador_program_details]** \n\n Error fetching program details: error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(
            status_code=500, detail=f"Error fetching program details: {str(e)}"
        )


@router.post("/ambassador/program/details/edit")
async def edit_ambassador_program_details(
    request: Request,
    current_user: CustomUser = Depends(require_marketing_lead_role),
    platform: Optional[str] = None,
):
    """
    Edit existing ambassador program details - requires Marketing Lead role.
    """
    print(f"[edit_ambassador_program_details] API called")

    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:
        # Get form data from request
        form_data = await request.form()

        @database_sync_to_async
        def validate_and_update_program_details(form_data):
            try:
                # Get existing program details
                program_details = AmbassadorProgramDetails.objects.first()

                if not program_details:
                    return {
                        "success": False,
                        "errors": {
                            "general": [
                                "No ambassador program details found. Create them first using the create endpoint."
                            ]
                        },
                        "status_code": status.HTTP_404_NOT_FOUND,
                    }

                # Create form with existing instance and new data
                form = AmbassadorProgramDetailsForm(form_data, instance=program_details)

                if form.is_valid():
                    # Save the updated program details
                    updated_program_details = form.save()

                    return {
                        "success": True,
                        "message": "Ambassador program details updated successfully!",
                        "program_details": {
                            "id": updated_program_details.id,
                            "description": updated_program_details.description,
                            "documentation_link": updated_program_details.documentation_link,
                        },
                        "status_code": status.HTTP_200_OK,
                    }
                else:
                    return {
                        "success": False,
                        "errors": form.errors,
                        "status_code": status.HTTP_400_BAD_REQUEST,
                    }

            except Exception as e:
                return {
                    "success": False,
                    "error": f"Database error: {str(e)}",
                    "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                }

        # Execute update
        result = await validate_and_update_program_details(form_data)
        status_code = result.pop("status_code", status.HTTP_200_OK)

        if not result.get("success", True):
            return JSONResponse(content=result, status_code=status_code)

        print(f"[edit_ambassador_program_details] Program details updated successfully")
        return JSONResponse(content=result, status_code=status_code)

    except Exception as e:
        await notify_by_bot(
            f"**[API: edit_ambassador_program_details]** \n\n Error updating program details: error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(
            status_code=500, detail=f"Error updating program details: {str(e)}"
        )


# FIXED MESSAGES FORM FIELDS
@router.get("/fixedMessages/form/create")
async def get_fixed_message_create_form(
    request: Request,
    current_user: CustomUser = Depends(require_admin_role),
    platform: Optional[str] = None,
):
    """
    Get form fields for creating fixed messages - requires Admin or Super Admin role.
    """
    print(f"[get_fixed_message_create_form] API called with user_id: {current_user.pk}")

    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    from socialApp.forms import FixedMessageForm
    from apiManager.utilities.form_fields import get_form_fields

    FormClass = FixedMessageForm
    fields_info = get_form_fields(FormClass)
    print(
        f"[get_fixed_message_create_form] Returning form fields, field count: {len(fields_info)}"
    )
    return JSONResponse(content=fields_info, status_code=status.HTTP_200_OK)


@router.get("/fixedMessages/form/edit")
async def get_fixed_message_edit_form(
    request: Request,
    current_user: CustomUser = Depends(require_admin_role),
    platform: Optional[str] = None,
):
    """
    Get form fields for editing fixed messages - requires Admin or Super Admin role.
    """
    print(f"[get_fixed_message_edit_form] API called with user_id: {current_user.pk}")

    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    from socialApp.forms import FixedMessageEditForm
    from apiManager.utilities.form_fields import get_form_fields

    FormClass = FixedMessageEditForm
    fields_info = get_form_fields(FormClass)
    print(
        f"[get_fixed_message_edit_form] Returning form fields, field count: {len(fields_info)}"
    )
    return JSONResponse(content=fields_info, status_code=status.HTTP_200_OK)


# FIXED MESSAGES MANAGEMENT
@router.get("/fixedMessages/getAll")
async def get_fixed_messages(
    request: Request,
    current_user: CustomUser = Depends(require_admin_role),
    platform: Optional[str] = None,
):
    """
    Get all fixed messages - requires Admin or Super Admin role.
    """
    print(f"[get_fixed_messages] API called with user_id: {current_user.pk}")

    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def get_fixed_messages_data():
        try:
            fixed_messages = FixedMessage.objects.all().order_by("text")
            return [
                {
                    "id": str(message.id),
                    "text": message.text,
                    "created_at": (
                        message.created_at.isoformat()
                        if hasattr(message, "created_at")
                        else None
                    ),
                }
                for message in fixed_messages
            ]
        except Exception as e:
            print(f"[get_fixed_messages] Database error: {str(e)}")
            raise e

    try:
        messages_data = await get_fixed_messages_data()
        print(f"[get_fixed_messages] Returning {len(messages_data)} fixed messages")
        return messages_data

    except Exception as e:
        await notify_by_bot(
            f"**[API: get_fixed_messages]** \n\n Error fetching fixed messages: error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(
            status_code=500, detail=f"Error fetching fixed messages: {str(e)}"
        )


@router.post("/fixedMessages/create")
async def create_fixed_message(
    request: Request,
    current_user: CustomUser = Depends(require_admin_role),
    platform: Optional[str] = None,
):
    """
    Create a new fixed message - requires Admin or Super Admin role.
    """
    print(f"[create_fixed_message] API called with user_id: {current_user.pk}")

    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:
        # Get form data from request
        form_data = await request.form()
        text = form_data.get("text", "").strip()

        if not text:
            raise HTTPException(status_code=400, detail="Text is required")

        @database_sync_to_async
        def validate_and_create_fixed_message(form_data):
            try:
                # Create and validate the form
                form = FixedMessageForm(form_data)

                if form.is_valid():
                    # Save the fixed message
                    fixed_message = form.save()

                    return {
                        "success": True,
                        "message": "Fixed message created successfully!",
                        "fixed_message": {
                            "id": str(fixed_message.id),
                            "text": fixed_message.text,
                        },
                        "status_code": status.HTTP_201_CREATED,
                    }
                else:
                    # Return form errors
                    return {
                        "success": False,
                        "errors": form.errors,
                        "status_code": status.HTTP_400_BAD_REQUEST,
                    }

            except Exception as e:
                return {
                    "success": False,
                    "error": f"Database error: {str(e)}",
                    "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                }

        # Execute creation
        result = await validate_and_create_fixed_message(form_data)
        status_code = result.pop("status_code", status.HTTP_200_OK)

        if not result.get("success", True):
            return JSONResponse(content=result, status_code=status_code)

        print(f"[create_fixed_message] Fixed message created successfully")
        return JSONResponse(content=result, status_code=status_code)

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        await notify_by_bot(
            f"**[API: create_fixed_message]** \n\n Error creating fixed message: error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(
            status_code=500, detail=f"Error creating fixed message: {str(e)}"
        )


@router.delete("/fixedMessages/{message_id}/delete")
async def delete_fixed_message(
    message_id: str,
    request: Request,
    current_user: CustomUser = Depends(require_admin_role),
    platform: Optional[str] = None,
):
    """
    Delete a fixed message - requires Admin or Super Admin role.
    """
    print(
        f"[delete_fixed_message] API called for message_id: {message_id} by {current_user.pk}"
    )

    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def delete_fixed_message_data(message_id):
        try:
            # Try to get the fixed message
            fixed_message = get_object_or_404(FixedMessage, id=message_id)
            message_text = fixed_message.text

            # Delete the message
            fixed_message.delete()

            return {
                "success": True,
                "message": f"Fixed message '{message_text}' has been deleted",
                "deleted_message": {
                    "id": message_id,
                    "text": message_text,
                },
            }

        except FixedMessage.DoesNotExist:
            return {
                "success": False,
                "error": "Fixed message not found",
                "status_code": status.HTTP_404_NOT_FOUND,
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Database error: {str(e)}",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            }

    try:
        result = await delete_fixed_message_data(message_id)

        if not result.get("success", True):
            status_code = result.pop(
                "status_code", status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            return JSONResponse(content=result, status_code=status_code)

        print(f"[delete_fixed_message] Fixed message deleted successfully")
        return JSONResponse(content=result, status_code=status.HTTP_200_OK)

    except Exception as e:
        await notify_by_bot(
            f"**[API: delete_fixed_message]** \n\n Error deleting fixed message: message_id={message_id}, error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(
            status_code=500, detail=f"Error deleting fixed message: {str(e)}"
        )


@router.put("/fixedMessages/{message_id}/edit")
async def edit_fixed_message(
    message_id: str,
    request: Request,
    current_user: CustomUser = Depends(require_admin_role),
    platform: Optional[str] = None,
):
    """
    Edit a fixed message - requires Admin or Super Admin role.
    """
    print(
        f"[edit_fixed_message] API called for message_id: {message_id} by {current_user.pk}"
    )

    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:
        # Get form data from request
        form_data = await request.form()
        new_text = form_data.get("text", "").strip()

        if not new_text:
            raise HTTPException(status_code=400, detail="Text is required")

        @database_sync_to_async
        def validate_and_update_fixed_message(message_id, form_data):
            try:
                # Get the existing fixed message
                fixed_message = get_object_or_404(FixedMessage, id=message_id)
                old_text = fixed_message.text

                # Create and validate the form with the existing instance
                form = FixedMessageEditForm(form_data, instance=fixed_message)

                if form.is_valid():
                    # Save the updated fixed message
                    updated_fixed_message = form.save()

                    return {
                        "success": True,
                        "message": "Fixed message updated successfully!",
                        "fixed_message": {
                            "id": str(updated_fixed_message.id),
                            "text": updated_fixed_message.text,
                            "old_text": old_text,
                        },
                        "status_code": status.HTTP_200_OK,
                    }
                else:
                    # Return form errors
                    return {
                        "success": False,
                        "errors": form.errors,
                        "status_code": status.HTTP_400_BAD_REQUEST,
                    }

            except FixedMessage.DoesNotExist:
                return {
                    "success": False,
                    "error": "Fixed message not found",
                    "status_code": status.HTTP_404_NOT_FOUND,
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Database error: {str(e)}",
                    "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                }

        # Execute update
        result = await validate_and_update_fixed_message(message_id, form_data)
        status_code = result.pop("status_code", status.HTTP_200_OK)

        if not result.get("success", True):
            return JSONResponse(content=result, status_code=status_code)

        print(f"[edit_fixed_message] Fixed message updated successfully")
        return JSONResponse(content=result, status_code=status_code)

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        await notify_by_bot(
            f"**[API: edit_fixed_message]** \n\n Error updating fixed message: message_id={message_id}, error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(
            status_code=500, detail=f"Error updating fixed message: {str(e)}"
        )

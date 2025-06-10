from datetime import datetime, timedelta
from uuid import UUID
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
from asgiref.sync import sync_to_async
import traceback
import os
from django.core.files.base import ContentFile
from django.conf import settings
from django.db.models import Count, Max, Avg, F
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth, TruncHour
from django.utils.timezone import now

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
from eventTicketsApp.models import RSVPTicket, PaidFreeTicket, Ticket
from eventTicketsApp.models import Ticket, RSVPTicket
from accountManagementApp.models import UserProfile
from adminDashboardApp.models import College, LoginHistoryModel

from adminDashboardApp.models import College
from collegeManagementApp.models import Membership, CollegeEventLink
from adminDashboardApp.forms import CollegeForm, EditCollegeForm
from apiManager.utilities import get_form_fields

router = APIRouter()


# USERS
@router.get("/dashboard")
async def admin_dashboard(current_user: CustomUser = Depends(require_admin_role)):
    """
    Admin dashboard endpoint - requires Admin or Super Admin role.
    """
    print(f"[admin_dashboard] API called with user_id: {current_user.id}")

    try:
        # Get current user info
        user_groups = await sync_to_async(list)(
            current_user.groups.values_list("name", flat=True)
        )

        # Get dashboard stats
        total_users = await sync_to_async(CustomUser.objects.count)()
        active_users = await sync_to_async(
            CustomUser.objects.filter(is_active=True).count
        )()
        suspended_users = await sync_to_async(
            CustomUser.objects.filter(is_suspended=True).count
        )()

        return {
            "message": "Admin dashboard",
            "user": {
                "id": current_user.id,
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
        raise HTTPException(
            status_code=500, detail=f"Error loading dashboard: {str(e)}"
        )


@router.get("/users", response_model=List[UserResponse])
async def get_users(
    skip: int = 0,
    limit: int = 0,  # 0 means no limit (return all users)
    current_user: CustomUser = Depends(require_admin_role),
):
    """
    Get list of users - requires Admin or Super Admin role.
    If limit is 0, returns all users. Otherwise uses pagination.
    """
    print(f"[get_users] API called with user_id: {current_user.id}")

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

        users = await sync_to_async(list)(users_queryset)
        print(f"[get_users] Retrieved {len(users)} users from database")

        # Convert to response format
        user_responses = []
        for user in users:
            groups = await sync_to_async(list)(
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
                    first_name=user.first_name,
                    last_name=user.last_name,
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
        raise HTTPException(status_code=500, detail=f"Error fetching users: {str(e)}")


@router.get("/user/{user_id}", response_model=UserResponse)
async def get_user_detail(
    user_id: int, current_user: CustomUser = Depends(require_admin_role)
):
    """
    Get detailed user information including tickets, friends, and profile - requires Admin or Super Admin role.
    """
    print(f"[get_user_detail] API called for user_id: {user_id} by {current_user.id}")

    @sync_to_async
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
                if hasattr(user, "user_profile") and user.user_profile:
                    user_profile = user.user_profile
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
            first_name=user.first_name,
            last_name=user.last_name,
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
        raise HTTPException(status_code=500, detail=f"Error fetching user: {str(e)}")


@router.post("/user/{user_id}/suspend")
async def suspend_user(
    user_id: int, current_user: CustomUser = Depends(require_super_admin_role)
):
    """
    Suspend a user - requires Super Admin role.
    """
    print(f"[suspend_user] API called for user_id: {user_id} by {current_user.id}")

    try:
        user = await sync_to_async(get_object_or_404)(CustomUser, id=user_id)

        # Don't allow suspending yourself
        if user.id == current_user.id:
            raise HTTPException(status_code=400, detail="You cannot suspend yourself")

        await sync_to_async(user.suspend)()

        return {"message": f"User {user.username} has been suspended"}

    except Exception as e:
        if "does not exist" in str(e).lower():
            raise HTTPException(status_code=404, detail="User not found")
        raise HTTPException(status_code=500, detail=f"Error suspending user: {str(e)}")


@router.post("/user/{user_id}/delete")
async def delete_user(
    user_id: int, current_user: CustomUser = Depends(require_super_admin_role)
):
    """
    Delete a user - requires Super Admin role.
    """
    print(f"[delete_user] API called for user_id: {user_id} by {current_user.id}")

    try:
        # Check if user exists first
        user_exists = await sync_to_async(
            CustomUser.objects.filter(id=user_id).exists
        )()
        if not user_exists:
            print(f"[delete_user] User with ID {user_id} does not exist")
            raise HTTPException(
                status_code=404, detail=f"User with ID {user_id} not found"
            )

        user = await sync_to_async(get_object_or_404)(CustomUser, id=user_id)
        username = user.username  # Store username before deletion
        await sync_to_async(user.delete)()

        print(f"[delete_user] Successfully deleted user {username} (ID: {user_id})")
        return {"message": f"User {username} has been deleted"}
    except HTTPException:
        # Re-raise HTTP exceptions (like 404)
        raise
    except Exception as e:
        print(f"[delete_user] Error deleting user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting user: {str(e)}")


@router.post("/user/{user_id}/unsuspend")
async def unsuspend_user(
    user_id: int, current_user: CustomUser = Depends(require_super_admin_role)
):
    """
    Remove suspension from a user - requires Super Admin role.
    """
    print(f"[unsuspend_user] API called for user_id: {user_id} by {current_user.id}")

    try:
        user = await sync_to_async(get_object_or_404)(CustomUser, id=user_id)
        await sync_to_async(user.remove_suspension_OR_ban)()

        return {"message": f"User {user.username} suspension has been removed"}

    except Exception as e:
        if "does not exist" in str(e).lower():
            raise HTTPException(status_code=404, detail="User not found")
        raise HTTPException(
            status_code=500, detail=f"Error removing suspension: {str(e)}"
        )


# Event Management Admin API
@router.get("/events/getAll")
async def get_events(current_user: CustomUser = Depends(require_admin_role)):
    """
    Get list of events with only name and header_photo URL.
    """
    print(f"[get_events] API called with user_id: {current_user.id}")
    try:
        events_qs = Event.objects.only("title", "header_photo", "eventId")
        events = await sync_to_async(list)(events_qs)

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
        raise HTTPException(status_code=500, detail=f"Error fetching events: {str(e)}")


@router.get("/eventDetails/{event_id}")
async def get_event_detail(
    event_id: UUID, current_user: CustomUser = Depends(require_admin_role)
):
    try:
        # Safely print user ID
        user_id = await sync_to_async(lambda: current_user.id, thread_sensitive=True)()
        print(f"[get_event_detail] API called for event_id: {event_id} by {user_id}")

        # Fetch event safely
        event = await sync_to_async(get_object_or_404, thread_sensitive=True)(
            Event, eventId=event_id
        )

        # Extract event fields safely
        event_fields = await sync_to_async(
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

        # Extract host fields safely
        host_fields = await sync_to_async(
            lambda: {
                "id": event.host.id,
                "username": event.host.username,
                "email": event.host.email,
                "first_name": event.host.first_name,
                "last_name": event.host.last_name,
            },
            thread_sensitive=True,
        )()

        # RSVP tickets
        rsvp_tickets = await sync_to_async(list)(
            event.rsvp_tickets.all().values(
                "ticket_id",
                "email",
                "first_name",
                "last_name",
                "display_on_guestlist",
                "created_at",
            )
        )
        for ticket in rsvp_tickets:
            ticket["ticket_id"] = str(ticket["ticket_id"])
            ticket["created_at"] = (
                ticket["created_at"].isoformat() if ticket["created_at"] else None
            )

        # Ticket types
        ticket_types = await sync_to_async(list)(
            event.tickets.all().values(
                "ticket_id",
                "ticket_name",
                "ticket_price",
                "ticket_description",
                "ticket_quantity",
                "ticket_sold",
                "crew_discounted_price",
                "stripePriceId",
            )
        )
        for tt in ticket_types:
            tt["ticket_id"] = str(tt["ticket_id"])
            tt["ticket_price"] = (
                float(tt["ticket_price"]) if tt["ticket_price"] else None
            )
            tt["crew_discounted_price"] = (
                float(tt["crew_discounted_price"])
                if tt["crew_discounted_price"]
                else None
            )
            tt["available_tickets"] = tt["ticket_quantity"] - (tt["ticket_sold"] or 0)

        # Purchased tickets
        purchased_tickets = await sync_to_async(list)(
            event.ticket_set.all().values(
                "ticketId",
                "user__username",
                "user__email",
                "user__first_name",
                "user__last_name",
                "guestFirstName",
                "guestLastName",
                "guestEmail",
                "status",
                "created_at",
                "stripe_session_id",
            )
        )
        for pt in purchased_tickets:
            pt["ticketId"] = str(pt["ticketId"])
            pt["created_at"] = (
                pt["created_at"].isoformat() if pt["created_at"] else None
            )
            pt["user"] = (
                {
                    "username": pt.pop("user__username", None),
                    "email": pt.pop("user__email", None),
                    "first_name": pt.pop("user__first_name", None),
                    "last_name": pt.pop("user__last_name", None),
                }
                if pt.get("user__username")
                else None
            )

        # Assemble final response
        return {
            **event_fields,
            "host": host_fields,
            "tickets": {
                "rsvp_tickets": rsvp_tickets,
                "ticket_types": ticket_types,
                "purchased_tickets": purchased_tickets,
                "ticket_stats": {
                    "total_rsvps": len(rsvp_tickets),
                    "total_ticket_types": len(ticket_types),
                    "total_purchased_tickets": len(purchased_tickets),
                    "total_tickets_sold": sum(
                        tt.get("ticket_sold", 0) or 0 for tt in ticket_types
                    ),
                    "total_tickets_available": sum(
                        tt.get("available_tickets", 0) for tt in ticket_types
                    ),
                },
            },
        }

    except Http404:
        raise HTTPException(status_code=404, detail="Event not found.")
    except Exception as e:
        print(f"[ERROR get_event_detail] {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching event: {str(e)}")


@router.post("/delete/event/{event_id}")
async def delete_event(
    event_id: UUID, current_user: CustomUser = Depends(require_admin_role)
):
    """
    Delete an event - requires Admin or Super Admin role.
    """
    print(f"[delete_event] API called for event_id: {event_id} by {current_user.id}")

    try:
        event = await sync_to_async(get_object_or_404)(Event, eventId=event_id)
        await sync_to_async(event.delete)()

        return {"message": f"Event {event.title} has been deleted"}

    except Exception as e:
        print(f"Error with deletion {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting event: {str(e)}")

# USER ANALYTICS ADMIN API
@router.get("/userAnalytics/getAll")
async def get_all_users(current_user: CustomUser = Depends(require_admin_role)):
    """
    Get list of user analytics with optimized database queries.
    """
    print(f"[get_user_analytics] API called with user_id: {current_user.id}")

    try:
        users_qs = CustomUser.objects.only("username", "first_name", "last_name", "user_id")
        users = await sync_to_async(list)(users_qs)
        user_info = [] 
        for user in users:
            user_info.append({
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "user_id": user.user_id,
            })
        return user_info

    except Exception as e:
        print(f"[get_user_analytics] Error in get_user_analytics: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error fetching user analytics: {str(e)}"
        )


@router.get("/userAnalytics/signups")
async def get_user_signups(
    period: str = Query("daily", description="Time period: daily, weekly, or monthly"),
    current_user: CustomUser = Depends(require_admin_role)
):
    """
    Get user signup analytics grouped by time period - requires Admin or Super Admin role.
    """
    print(f"[get_user_signups] API called with user_id: {current_user.id}, period: {period}")

    @sync_to_async
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
        print(f"[get_user_signups] Error: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error fetching signup analytics: {str(e)}"
        )


@router.get("/userAnalytics/logins")
async def get_user_logins(
    trend: str = Query("general", description="Trend type: general, user_activity, time_trends, ip_insights, security, retention"),
    time_frame: str = Query("hourly", description="Time frame for time_trends: hourly, daily, monthly"),
    current_user: CustomUser = Depends(require_admin_role)
):
    """
    Get user login analytics with various trend types - requires Admin or Super Admin role.
    """
    print(f"[get_user_logins] API called with user_id: {current_user.id}, trend: {trend}")

    @sync_to_async
    def get_login_data(trend_type, time_frame):
        if trend_type == "general":
            data = {
                "total_logins": LoginHistoryModel.objects.count(),
                "unique_users": LoginHistoryModel.objects.values("user").distinct().count(),
                "active_sessions": LoginHistoryModel.objects.filter(
                    logout_time__isnull=True
                ).count(),
                "average_session_duration": LoginHistoryModel.objects.aggregate(
                    avg_duration=Avg(
                        F("session_duration_minutes") + F("session_duration_seconds") / 60
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
                LoginHistoryModel.objects.annotate(time_period=trunc_function("login_time"))
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
                LoginHistoryModel.objects.filter(login_time__gte=today - timedelta(days=7))
                .values("user")
                .distinct()
                .count()
            )  # Count distinct users

            # Get unique users for the last 30 days
            last_30_days = (
                LoginHistoryModel.objects.filter(login_time__gte=today - timedelta(days=30))
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
        if trend not in ["general", "user_activity", "time_trends", "ip_insights", "security", "retention"]:
            raise HTTPException(status_code=400, detail="Invalid trend type")

        result = await get_login_data(trend, time_frame)
        print(f"[get_user_logins] Returning login analytics for trend: {trend}")
        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"[get_user_logins] Error: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error fetching login analytics: {str(e)}"
        )


@router.get("/userAnalytics/demographics")
async def get_user_demographics(
    group_by: str = Query("home_state", description="Group by field: gender, home_state, graduation_year, major, status"),
    current_user: CustomUser = Depends(require_admin_role)
):
    """
    Get user demographics analytics grouped by specified field - requires Admin or Super Admin role.
    """
    print(f"[get_user_demographics] API called with user_id: {current_user.id}, group_by: {group_by}")

    @sync_to_async
    def get_demographic_data(group_by):
        valid_fields = ["gender", "home_state", "graduation_year", "major", "status"]
        if group_by not in valid_fields:
            raise ValueError(f"Invalid group_by field. Must be one of: {valid_fields}")

        demographics = (
            UserProfile.objects.values(group_by)
            .annotate(count=Count("id"))
            .order_by(group_by)
        )

        labels = [demo[group_by] or "Unknown" for demo in demographics]
        counts = [demo["count"] for demo in demographics]

        return {"labels": labels, "counts": counts}

    try:
        result = await get_demographic_data(group_by)
        print(f"[get_user_demographics] Returning {len(result['labels'])} demographic groups")
        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"[get_user_demographics] Error: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error fetching demographic analytics: {str(e)}"
        )


# COLLEGE MANAGEMENT ADMIN API
@router.get("/colleges/getAll")
async def get_colleges(current_user: CustomUser = Depends(require_admin_role)):
    """
    Get list of colleges with optimized database queries.
    """
    print(f"[get_colleges] API called with user_id: {current_user.id}")

    @sync_to_async
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
        print(f"[get_colleges] Error in get_colleges: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error fetching colleges: {str(e)}"
        )


@router.get("/colleges/create/form/fields")
async def get_college_create_form_fields():
    return get_form_fields(CollegeForm)


@router.post("/colleges/create")
async def create_college(
    request: Request, current_user: CustomUser = Depends(require_admin_role)
):
    """
    Create a new college - requires Admin or Super Admin role.
    """
    print(f"[create_college] Function called by user_id: {current_user.id}")
    try:
        # Get form data from request
        form_data = await request.form()
        form_dict = {}
        file_dict = {}

        # Separate regular form fields from file uploads
        for key, value in form_data.items():
            # Check if this is an UploadFile by checking for filename and read methods
            if hasattr(value, "filename") and hasattr(
                value, "read"
            ):  # This is an UploadFile
                if value.filename:  # Only process if a file was actually uploaded
                    print(
                        f"[create_college] Processing file upload: {key} = {value.filename}"
                    )
                    # Convert UploadFile to Django-compatible file
                    file_content = await value.read()
                    django_file = ContentFile(file_content, name=value.filename)
                    file_dict[key] = django_file
                    # Reset file position for potential re-reading
                    await value.seek(0)
                else:
                    # Empty file upload, skip it
                    print(
                        f"[create_college] Skipping empty file upload for field: {key}"
                    )
            else:
                form_dict[key] = value

        print(
            f"[create_college] Received form data with fields: {', '.join(form_dict.keys())}"
        )
        if file_dict:
            print(
                f"[create_college] Received file uploads: {', '.join(file_dict.keys())}"
            )

        @sync_to_async
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
        return JSONResponse(
            content={"error": f"An unexpected error occurred: {str(e)}"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.post("/colleges/{college_id}/delete")
async def delete_college(
    college_id: UUID, current_user: CustomUser = Depends(require_admin_role)
):
    """
    Delete a college - requires Admin or Super Admin role.
    """
    print(
        f"[delete_college] API called for college_id: {college_id} by {current_user.id}"
    )

    try:
        college = await sync_to_async(get_object_or_404)(College, collegeId=college_id)
        await sync_to_async(college.delete)()

        return {"message": f"College {college.name} has been deleted"}

    except Exception as e:
        print(f"Error with deletion {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting college: {str(e)}")


@router.get("/colleges/{college_id}/edit/form/fields")
async def get_college_edit_form_fields():
    return get_form_fields(EditCollegeForm)


@router.post("/colleges/{college_id}/edit")
async def edit_college(
    college_id: UUID,
    request: Request,
    current_user: CustomUser = Depends(require_admin_role),
):
    """
    Edit a college - requires Admin or Super Admin role.
    """
    print(
        f"[edit_college] API called for college_id: {college_id} by {current_user.id}"
    )
    try:
        # Get form data from request
        form_data = await request.form()
        form_dict = {}
        file_dict = {}

        # Separate regular form fields from file uploads
        for key, value in form_data.items():
            # Check if this is an UploadFile by checking for filename and read methods
            if hasattr(value, "filename") and hasattr(
                value, "read"
            ):  # This is an UploadFile
                if value.filename:  # Only process if a file was actually uploaded
                    print(
                        f"[edit_college] Processing file upload: {key} = {value.filename}"
                    )
                    # Convert UploadFile to Django-compatible file
                    file_content = await value.read()
                    django_file = ContentFile(file_content, name=value.filename)
                    file_dict[key] = django_file
                    # Reset file position for potential re-reading
                    await value.seek(0)
                else:
                    # Empty file upload, skip it
                    print(f"[edit_college] Skipping empty file upload for field: {key}")
            else:
                form_dict[key] = value

        print(
            f"[edit_college] Received form data with fields: {', '.join(form_dict.keys())}"
        )
        if file_dict:
            print(
                f"[edit_college] Received file uploads: {', '.join(file_dict.keys())}"
            )

        @sync_to_async
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
        return JSONResponse(
            content={"error": f"An unexpected error occurred: {str(e)}"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get("/colleges/{college_id}/members")
async def get_college_members(
    college_id: UUID, current_user: CustomUser = Depends(require_admin_role)
):
    """
    Get members of a college - requires Admin or Super Admin role.
    """
    print(
        f"[get_college_members] API called for college_id: {college_id} by {current_user.id}"
    )

    @sync_to_async
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
        if isinstance(e, HTTPException):
            raise e
        print(f"[get_college_members] Error in get_college_members: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error fetching college members: {str(e)}"
        )


@router.get("/colleges/{college_id}/events")
async def get_college_events(
    college_id: UUID, current_user: CustomUser = Depends(require_admin_role)
):
    """
    Get all events associated with a college - requires Admin or Super Admin role.
    """
    print(
        f"[get_college_events] API called for college_id: {college_id} by {current_user.id}"
    )

    @sync_to_async
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
        if isinstance(e, HTTPException):
            raise e
        print(f"[get_college_events] Error in get_college_events: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error fetching college events: {str(e)}"
        )

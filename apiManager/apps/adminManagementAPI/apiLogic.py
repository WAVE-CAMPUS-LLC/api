from datetime import datetime
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
from django.db.models import Count

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
from adminDashboardApp.models import College
from collegeManagementApp.models import Membership, CollegeEventLink
from adminDashboardApp.forms import CollegeForm
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
                        "id": college.collegeId,
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
        form_dict = dict(form_data)
        print(
            f"[create_college] Received form data with fields: {', '.join(form_dict.keys())}"
        )

        @sync_to_async
        def validate_and_create_college(form_data, created_by_user):
            # Create and validate the form
            form = CollegeForm(form_data)
            if form.is_valid():
                # Save the college with the current user as creator
                college = form.save(commit=False)
                college.created_by = created_by_user
                college.save()
                return None, status.HTTP_201_CREATED
            else:
                return form.errors, status.HTTP_400_BAD_REQUEST

        # Run validation and college creation
        errors, status_code = await validate_and_create_college(form_dict, current_user)

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

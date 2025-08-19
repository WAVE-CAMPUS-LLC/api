from uuid import UUID
import time
import stripe
import json
from django.conf import settings
from django.contrib.auth.models import Group
from stripeManagementApp.customerSetup import ConnectAccount
from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Optional
from channels.db import database_sync_to_async
import traceback

from apiManager.dependencies import get_current_user
from apiManager.utilities.form_fields import get_form_fields
from apiManager.utilities.notify_by_bot import notify_by_bot
from apiManager.utilities.device_info import get_device_info
from apiManager.notifications.notification import send_notification
from .serializers import (
    HostEventExplore,
    EventDetailSerializer,
    EditEventSerializer,
    EditEventResponseSerializer,
    LocationSerializer,
    HostSerializer,
)

from eventTicketsApp.forms import PaidFreeTicketForm
from eventManagementApp.forms import CouponCodeForm

from jose import jwt
from datetime import datetime, timedelta
from decimal import Decimal
from authenticationApp.models import CustomUser
from starlette.datastructures import UploadFile
from django.shortcuts import get_object_or_404
from eventManagementApp.models import Event, HostProfile, CouponCode, SharedEvent
from accountManagementApp.models import UserProfile
from eventTicketsApp.models import RSVPTicket, PaidFreeTicket, Ticket
from socialApp.models import GoWithRequest
from coreApp.models import EventView
from eventTicketsApp.serializers import TicketSerializer
from eventManagementApp.forms import EventForm
from eventManagementApp.serializers import EditEventModelSerializer
from dotenv import load_dotenv
import os

# fastapi → django adapter
from django.core.files.uploadedfile import SimpleUploadedFile


async def starlette_to_django(u: UploadFile) -> SimpleUploadedFile:
    content = await u.read()  # get bytes from Starlette file
    return SimpleUploadedFile(  # Django-friendly object
        name=u.filename,
        content=content,
        content_type=u.content_type or "application/octet-stream",
    )


router = APIRouter()


async def send_event_creation_notifications(event, host_user):
    """
    Send push notifications to campus members and friends when an event is created.
    """
    try:

        @database_sync_to_async
        def get_notification_recipients(event, host_user):
            """Get all users who should receive notifications for this event creation."""
            # Get the host's profile
            host_profile = host_user.user_profile

            # Set to track users who should receive notifications (to avoid duplicates)
            notification_recipients = []
            notified_user_ids = set()

            # Send notifications to campus members if host is in a campus
            if host_profile.college:
                print(
                    f"[send_event_creation_notifications] Host is in campus: {host_profile.college.name}"
                )

                # Get all campus members
                campus_members = (
                    UserProfile.objects.filter(college=host_profile.college)
                    .exclude(user=host_user)
                    .select_related("user")
                )

                for member_profile in campus_members:
                    if (
                        member_profile.user
                        and member_profile.user.user_id not in notified_user_ids
                    ):
                        notification_recipients.append(
                            {
                                "user_id": member_profile.user.user_id,
                                "username": member_profile.user.username,
                                "type": "campus",
                            }
                        )
                        notified_user_ids.add(member_profile.user.user_id)

            # Send notifications to friends
            friends = host_profile.friends.all().select_related("user")
            print(
                f"[send_event_creation_notifications] Host has {friends.count()} friends"
            )

            for friend_profile in friends:
                if (
                    friend_profile.user
                    and friend_profile.user.user_id not in notified_user_ids
                ):
                    notification_recipients.append(
                        {
                            "user_id": friend_profile.user.user_id,
                            "username": friend_profile.user.username,
                            "type": "friend",
                        }
                    )
                    notified_user_ids.add(friend_profile.user.user_id)

            return notification_recipients

        # Get all recipients
        recipients = await get_notification_recipients(event, host_user)

        # Prepare notification data
        notification_title = "New Event Created!"
        notification_message = (
            f"{host_user.first_name} created a new event: {event.title}"
        )
        navigate_to = "event_details"
        params = {
            "event_id": str(event.eventId),
            "event_title": event.title,
            "host_name": f"{host_user.first_name} {host_user.last_name}",
        }

        # Send notifications to all recipients
        for recipient in recipients:
            try:
                await send_notification(
                    recipient["user_id"],
                    notification_message,
                    notification_title,
                    navigate_to=navigate_to,
                    params=params,
                )
                print(
                    f"[send_event_creation_notifications] Sent {recipient['type']} notification to {recipient['username']}"
                )
            except Exception as e:
                print(
                    f"[send_event_creation_notifications] Error sending {recipient['type']} notification to {recipient['username']}: {str(e)}"
                )

        print(
            f"[send_event_creation_notifications] Total notifications sent: {len(recipients)}"
        )

    except Exception as e:
        print(
            f"[send_event_creation_notifications] Error in notification process: {str(e)}"
        )
        # Don't raise the exception as we don't want notification failures to prevent event creation


@router.api_route("/event/{eventId}/editEvent", methods=["POST", "PATCH"])
async def edit_event_endpoint(
    request: Request,
    eventId: str,
    user_id=Depends(get_current_user),
    platform: Optional[str] = None,
):
    print(f"[DEBUG - edit_event_endpoint] Function called with eventId: {eventId}")
    """
    Edit an event, supporting both full updates (POST) and partial updates (PATCH).
    """
    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:
        # Get form data (includes both text fields and files)
        form_data = await request.form()

        # Separate normal data and file data from the form
        data = {}
        files = {}
        print(f"[DEBUG - edit_event_endpoint] Processing form data")
        for key, value in form_data.multi_items():
            if isinstance(value, UploadFile):
                print(f"[DEBUG - edit_event_endpoint] File uploaded: {key}")
                # Convert FastAPI UploadFile to Django file object
                django_file = await starlette_to_django(value)
                files[key] = django_file
            else:
                print(f"[DEBUG - edit_event_endpoint] Text field: {key} = {value}")
                data[key] = value

        # Determine if this is a partial update (PATCH)
        partial = request.method.upper() == "PATCH"

        # Wrap Django ORM calls and serializer processing in a synchronous function
        @database_sync_to_async
        def process_edit_event():
            # Retrieve the event or raise a 404
            try:
                event = Event.objects.get(eventId=eventId)
            except Event.DoesNotExist:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
                )

            print(f"[DEBUG - process_edit_event] Event fields: {event.__dict__}")
            print(f"[DEBUG - process_edit_event] Incoming data: {data}")
            print(f"[DEBUG - process_edit_event] Incoming files: {files}")

            # Get the current user's profile
            user = CustomUser.objects.get(id=user_id)

            # Handle UserProfile that might not exist yet
            try:
                user_profile = UserProfile.objects.get(user=user)
                print(
                    f"[DEBUG - edit_event] UserProfile found for user: {user.username}"
                )
            except UserProfile.DoesNotExist:
                print(
                    f"[DEBUG - edit_event] UserProfile not found for user: {user.username}, creating one..."
                )
                user_profile, created = UserProfile.objects.get_or_create(user=user)
                print(
                    f"[DEBUG - edit_event] UserProfile {'created' if created else 'retrieved'} for user: {user.username}"
                )

            # Get the host profile for the event host
            host_profile = HostProfile.objects.get(user=event.host)

            # Determine whether the user is associated with a college
            is_in_college = user_profile.college is not None

            # Merge data and files for the serializer
            combined_data = {**data}
            combined_data.update(files)

            # Use DRF ModelSerializer for proper partial update support
            serializer = EditEventModelSerializer(
                instance=event, data=combined_data, partial=partial
            )

            if serializer.is_valid():
                updated_event = serializer.save()

                # Retrieve updated related data
                def serialize_queryset(queryset):
                    results = []
                    for item in queryset:
                        for key, value in item.items():
                            if isinstance(value, UUID):
                                item[key] = str(value)
                            elif isinstance(value, datetime):
                                item[key] = value.isoformat()
                        results.append(item)
                    return results

                rsvp_list_raw = RSVPTicket.objects.filter(event=updated_event).values()
                paid_free_tickets_raw = PaidFreeTicket.objects.filter(
                    event=updated_event
                ).values()

                rsvp_list = serialize_queryset(rsvp_list_raw)
                paid_free_tickets = serialize_queryset(paid_free_tickets_raw)

                # Create location serializer instance
                location = LocationSerializer(
                    building_name=updated_event.building_name,
                    street=updated_event.street,
                    apt_suite_unit=updated_event.apt_suite_unit,
                    city=updated_event.city,
                    state=updated_event.state,
                    zip_code=updated_event.zip_code,
                    country=updated_event.country,
                    hide_address=updated_event.hide_address,
                )

                # Create host serializer instance
                host = HostSerializer(
                    id=str(host_profile.hostProfileId),
                    name=f"{host_profile.user.first_name} {host_profile.user.last_name}",
                )

                # Create event response serializer instance
                event_data = EditEventResponseSerializer(
                    id=str(updated_event.eventId),
                    title=updated_event.title,
                    description=updated_event.description,
                    date=updated_event.date,
                    location=location,
                    host=host,
                    isInCollege=is_in_college,
                    rsvpList=rsvp_list,
                    paidFreeTickets=paid_free_tickets,
                )

                # Create the final response serializer
                response = EditEventSerializer(
                    message="Event updated successfully.", event=event_data
                )

                # Return the serialized data with JSON-compatible values
                return response.model_dump(mode="json")
            else:
                # Return validation errors in a structured format
                raise ValueError({"validation_errors": serializer.errors})

        # Await the synchronous process
        result = await process_edit_event()
        print(
            f"[DEBUG - edit_event_endpoint] Success response: {result.get('message', 'No message')}"
        )
        return JSONResponse(content=result, status_code=status.HTTP_200_OK)
    except ValueError as ve:
        # Return validation errors in a structured format
        error_content = {"message": "Failed to update event."}

        # Check if this is our structured validation error
        if str(ve).startswith('{"validation_errors"'):
            try:
                import json

                error_dict = json.loads(str(ve).replace("'", '"'))
                error_content.update(error_dict)
            except:
                error_content["errors"] = str(ve)
        else:
            error_content["errors"] = str(ve)

        return JSONResponse(
            content=error_content,
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        # Log the exception details and return a server error
        traceback_str = traceback.format_exc()
        print(f"Edit event error: {str(e)}\n{traceback_str}")
        await notify_by_bot(
            f"**[API: edit_event_endpoint]** \n\n Error editing event: eventId={eventId}, error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        return JSONResponse(
            content={"error": f"An unexpected error occurred: {str(e)}"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get("/getEvents")
async def get_events(
    request: Request,
    user_id: int = Depends(get_current_user),
    platform: Optional[str] = None,
):
    print(f"[DEBUG - get_events] Function called with user_id: {user_id}")
    """
    API endpoint for getting all events for a user
    """
    try:
        user_agent_str = request.headers.get("user-agent", "")
        device_data = get_device_info(user_agent_str)
        device_info = device_data["device_info"]

        @database_sync_to_async
        def validate_user(user_id):
            user = CustomUser.objects.get(id=user_id)
            return user

        @database_sync_to_async
        def get_events(user_id):
            user = CustomUser.objects.get(id=user_id)
            events = Event.objects.filter(host=user)
            events_list = []
            for event in events:
                header_photo = event.header_photo.url if event.header_photo else None
                events_list.append(
                    {
                        "eventId": str(event.eventId),
                        "title": event.title,
                        "header_photo": header_photo,
                        "date": event.date,
                        "event_type": event.event_type,
                        "ticketing": str(event.ticketing),
                        "status": event.status,
                        "city": event.city,
                        "state": event.state,
                    }
                )
            return events_list

        # Validate user exists
        await validate_user(user_id)

        events_before_serializing = await get_events(user_id)
        events = [HostEventExplore(**event) for event in events_before_serializing]
        print(f"[DEBUG - get_events] Returning {len(events)} events")

        return {"events": events}
    except HTTPException as http_ex:
        # Handle HTTP exceptions separately if needed
        return JSONResponse(
            content={"error": str(http_ex.detail)},
            status_code=http_ex.status_code,
        )
    except CustomUser.DoesNotExist:
        return JSONResponse(
            content={"error": "User not found."},
            status_code=status.HTTP_404_NOT_FOUND,
        )

    except Exception as e:
        traceback_str = traceback.format_exc()
        print(f"Get Events error: {str(e)}\n{traceback_str}")
        await notify_by_bot(
            f"**[API: get_events]** \n\n Unexpected error: user_id={user_id}, error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )

        # Check if it's a validation error from Pydantic
        if "ValidationError" in str(type(e)):
            return JSONResponse(
                content={
                    "errors": str(e),
                    "message": "Failed to serialize event data.",
                },
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Handle all other exceptions
        return JSONResponse(
            content={"error": f"An unexpected error occurred: {str(e)}"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get("/getEvent/{eventId}")
async def get_event_details(
    eventId: str,
    request: Request,
    user_id: int = Depends(get_current_user),
    platform: Optional[str] = None,
):
    print(
        f"[DEBUG - get_event_details] Function called with eventId: {eventId}, user_id: {user_id}"
    )
    """
    API endpoint for getting event details
    """
    try:
        user_agent_str = request.headers.get("user-agent", "")
        device_data = get_device_info(user_agent_str)
        device_info = device_data["device_info"]

        @database_sync_to_async
        def get_event(eventId):
            try:
                event = Event.objects.get(eventId=eventId)
                return event
            except Event.DoesNotExist:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Event not found."
                )
            except Event.MultipleObjectsReturned:
                # Log this critical issue but return the first one to maintain functionality
                print(f"[CRITICAL] Multiple events found with eventId: {eventId}")
                event = Event.objects.filter(eventId=eventId).first()
                return event

        event = await get_event(eventId)
        print(
            f"[DEBUG - get_event_details] Event found: {event.title if event else 'None'}"
        )

        # Create location serializer
        location = LocationSerializer(
            building_name=event.building_name,
            street=event.street,
            apt_suite_unit=event.apt_suite_unit,
            city=event.city,
            state=event.state,
            zip_code=event.zip_code,
            country=event.country,
            hide_address=event.hide_address,
        )

        # Process image URLs
        header_photo_url = event.header_photo.url if event.header_photo else None
        body_photo_one_url = event.body_photo_one.url if event.body_photo_one else None
        body_photo_two_url = event.body_photo_two.url if event.body_photo_two else None
        body_photo_three_url = (
            event.body_photo_three.url if event.body_photo_three else None
        )
        body_photo_four_url = (
            event.body_photo_four.url if event.body_photo_four else None
        )
        body_photo_five_url = (
            event.body_photo_five.url if event.body_photo_five else None
        )

        # Serialize the event data with explicit keyword arguments using EventDetailSerializer
        event_data = EventDetailSerializer(
            eventId=str(event.eventId),
            status=event.status,
            title=event.title,
            event_type=event.event_type,
            date=event.date,
            start_time=event.start_time,
            end_time=event.end_time,
            description=event.description,
            ticketing=event.ticketing,
            location=location,
            header_photo=header_photo_url,
            body_photo_one=body_photo_one_url,
            body_photo_two=body_photo_two_url,
            body_photo_three=body_photo_three_url,
            body_photo_four=body_photo_four_url,
            body_photo_five=body_photo_five_url,
            crew_discount=event.crew_discount,
            minimum_crew_size=event.minimum_crew_size,
            crew_discount_percentage=event.crew_discount_percentage,
            couponsActivated=event.couponsActivated,
            show_guest_list=event.show_guest_list,
            forAllDisplay=event.forAllDisplay,
            forCollegesDisplay=event.forCollegesDisplay,
        )

        print(
            f"[DEBUG - get_event_details] Returning event data for: {event_data.title}"
        )
        return {"event": event_data}

    except HTTPException as http_ex:
        # Handle HTTP exceptions separately if needed
        return JSONResponse(
            content={"error": str(http_ex.detail)},
            status_code=http_ex.status_code,
        )

    except Exception as e:
        traceback_str = traceback.format_exc()
        print(f"Get Event Details error: {str(e)}\n{traceback_str}")
        await notify_by_bot(
            f"**[API: get_event_details]** \n\n Unexpected error: eventId={eventId}, user_id={user_id}, error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )

        # Handle all other exceptions
        return JSONResponse(
            content={"error": f"An unexpected error occurred: {str(e)}"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.post("/event/{eventId}/deleteEvent")
async def delete_event(
    eventId: str,
    request: Request,
    user_id: int = Depends(get_current_user),
    platform: Optional[str] = None,
):
    print(
        f"[DEBUG - delete_event] Function called with eventId: {eventId}, user_id: {user_id}"
    )
    """
    API endpoint for deleting an event
    """
    try:
        user_agent_str = request.headers.get("user-agent", "")
        device_data = get_device_info(user_agent_str)
        device_info = device_data["device_info"]

        @database_sync_to_async
        def delete_event(eventId):
            print(
                f"[DEBUG - delete_event] Attempting to delete event with ID: {eventId}"
            )
            # Get the event object or raise a 404 error if not found
            event = get_object_or_404(Event, eventId=eventId)
            event.delete()
            return {"message": "Event deleted successfully."}

        result = await delete_event(eventId)
        print(f"[DEBUG - delete_event] Event deletion result: {result}")
        return JSONResponse(content=result, status_code=status.HTTP_200_OK)

    except HTTPException as http_ex:
        # Handle HTTP exceptions separately if needed
        return JSONResponse(
            content={"error": str(http_ex.detail)},
            status_code=http_ex.status_code,
        )

    except Exception as e:
        traceback_str = traceback.format_exc()
        print(f"Delete Event error: {str(e)}\n{traceback_str}")
        await notify_by_bot(
            f"**[API: delete_event]** \n\n Unexpected error: eventId={eventId}, user_id={user_id}, error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )

        # Handle all other exceptions
        return JSONResponse(
            content={"error": f"An unexpected error occurred: {str(e)}"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get("/event/fields")
async def event_creation_fields(request: Request):
    print(f"[DEBUG - event_creation_fields] Function called")
    FormClass = EventForm
    fields_info = get_form_fields(FormClass)
    print(
        f"[DEBUG - event_creation_fields] Returning form fields: {list(fields_info.keys())}"
    )
    return JSONResponse(content=fields_info, status_code=status.HTTP_200_OK)


@router.post("/event/free/create")
async def create_free_event(
    request: Request,
    user_id: int = Depends(get_current_user),
    platform: Optional[str] = None,
):
    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:
        form_data = await request.form()

        # Separate normal data and file data from the form
        data = {}
        files = {}
        print(f"[DEBUG - create_free_event] Processing form data")
        print(f"[DEBUG - create_free_event] Form data keys: {list(form_data.keys())}")
        
        for key, value in form_data.multi_items():
            print(f"[DEBUG - create_free_event] Processing key: {key}, value type: {type(value)}, value: {value}")
            if isinstance(value, UploadFile):
                print(f"[DEBUG - create_free_event] File uploaded: {key}")
                # Convert FastAPI UploadFile to Django file object
                django_file = await starlette_to_django(value)
                files[key] = django_file
            else:
                print(f"[DEBUG - create_free_event] Text field: {key} = {value}")
                data[key] = value
        
        print(f"[DEBUG - create_free_event] Final data dict: {data}")
        print(f"[DEBUG - create_free_event] Final files dict: {list(files.keys())}")

        # Clean up data - remove empty strings for optional fields, keep them for required fields
        cleaned_data = {}
        for key, value in data.items():
            if value == "":
                # Check if this is a boolean field that should be False instead of empty string
                if key in ["hide_address", "couponsActivated", "crew_discount", "show_guest_list", "forAllDisplay", "forCollegesDisplay"]:
                    cleaned_data[key] = False
                elif key in ["age_restriction"]:  # Optional select field
                    # Skip empty age_restriction to use the default
                    continue
                else:
                    # Keep empty string for other fields (Django form will handle validation)
                    cleaned_data[key] = value
            else:
                cleaned_data[key] = value
        
        print(f"[DEBUG - create_free_event] Cleaned data dict: {cleaned_data}")

        @database_sync_to_async
        def process_create_event():
            # Get the current user's profile.
            user = CustomUser.objects.get(id=user_id)

            # Handle UserProfile that might not exist yet
            try:
                user_profile = UserProfile.objects.get(user=user)
                print(
                    f"[DEBUG - create_free_event] UserProfile found for user: {user.username}"
                )
            except UserProfile.DoesNotExist:
                print(
                    f"[DEBUG - create_free_event] UserProfile not found for user: {user.username}, creating one..."
                )
                user_profile, created = UserProfile.objects.get_or_create(user=user)
                print(
                    f"[DEBUG - create_free_event] UserProfile {'created' if created else 'retrieved'} for user: {user.username}"
                )

            # Determine whether the user is associated with a college
            is_in_college = (
                user_profile.college is not None
            )  # Instantiate the Django form with submitted data, file uploads, instance and partial flag.
            event_form = EventForm(cleaned_data, files)
            print(f"[DEBUG - create_free_event] Event form: {event_form}")
            print(f"[DEBUG - create_free_event] Event form errors: {event_form.errors}")

            if event_form.is_valid():
                print(f"[DEBUG - create_free_event] Form is valid")
                # Get or create a host profile for the user
                host_profile, created = HostProfile.objects.get_or_create(user=user)
                # Create the new event
                new_event = event_form.save(commit=False)
                new_event.host = user  # Set the host to the current user
                new_event.ticketing = "Free"  # This is a free event
                new_event.status = "live"  # Set status to live
                new_event.save()

                # Create location serializer instance (now in sync context)
                location = LocationSerializer(
                    building_name=new_event.building_name,
                    street=new_event.street,
                    apt_suite_unit=new_event.apt_suite_unit,
                    city=new_event.city,
                    state=new_event.state,
                    zip_code=new_event.zip_code,
                    country=new_event.country,
                    hide_address=new_event.hide_address,
                )

                # Create host serializer instance (now in sync context)
                host = HostSerializer(
                    id=str(host_profile.hostProfileId),
                    name=f"{user.first_name} {user.last_name}",
                )

                # Process image URLs (now in sync context)
                header_photo_url = (
                    new_event.header_photo.url if new_event.header_photo else None
                )
                body_photo_one_url = (
                    new_event.body_photo_one.url if new_event.body_photo_one else None
                )
                body_photo_two_url = (
                    new_event.body_photo_two.url if new_event.body_photo_two else None
                )
                body_photo_three_url = (
                    new_event.body_photo_three.url
                    if new_event.body_photo_three
                    else None
                )
                body_photo_four_url = (
                    new_event.body_photo_four.url if new_event.body_photo_four else None
                )
                body_photo_five_url = (
                    new_event.body_photo_five.url if new_event.body_photo_five else None
                )

                # Create event response serializer instance (now in sync context)
                event_data = EventDetailSerializer(
                    eventId=str(new_event.eventId),
                    status=new_event.status,
                    title=new_event.title,
                    event_type=new_event.event_type,
                    date=new_event.date,
                    start_time=new_event.start_time,
                    end_time=new_event.end_time,
                    description=new_event.description,
                    ticketing=new_event.ticketing,
                    location=location,
                    header_photo=header_photo_url,
                    body_photo_one=body_photo_one_url,
                    body_photo_two=body_photo_two_url,
                    body_photo_three=body_photo_three_url,
                    body_photo_four=body_photo_four_url,
                    body_photo_five=body_photo_five_url,
                    crew_discount=new_event.crew_discount,
                    minimum_crew_size=new_event.minimum_crew_size,
                    crew_discount_percentage=new_event.crew_discount_percentage,
                    couponsActivated=new_event.couponsActivated,
                    show_guest_list=new_event.show_guest_list,
                    forAllDisplay=new_event.forAllDisplay,
                    forCollegesDisplay=new_event.forCollegesDisplay,
                )

                # Properly serialize the event_data to make it JSON serializable (now in sync context)
                serialized_event_data = event_data.model_dump(mode="json")

                # Return both event/user for notifications AND the serialized data
                return new_event, user, serialized_event_data

            else:
                # Here we raise an error with the form errors so that we can return a 400 response.
                raise ValueError(event_form.errors)

        # Execute the create event function
        new_event, user, serialized_event_data = await process_create_event()

        # Send notifications after event creation
        await send_event_creation_notifications(new_event, user)

        # Use the pre-serialized data (no more Django model access in async context)
        result = {
            "message": "Event created successfully.",
            "event": serialized_event_data,
        }
        return JSONResponse(content=result, status_code=status.HTTP_200_OK)

    except ValueError as ve:
        print(f"[DEBUG - create_free_event] ValueError: {str(ve)}")
        # Return any form validation errors
        return JSONResponse(
            content={"errors": str(ve), "message": "Failed to create event."},
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        # Log the exception details and return a server error
        traceback_str = traceback.format_exc()
        print(f"Create Free Event error: {str(e)}\n{traceback_str}")
        await notify_by_bot(
            f"**[API: create_free_event]** \n\n Error creating free event: error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(
            status_code=500, detail=f"Error creating free event: {str(e)}"
        )


@router.post("/event/paid/create")
async def create_paid_event(
    request: Request,
    user_id: int = Depends(get_current_user),
    platform: Optional[str] = None,
):
    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:
        form_data = await request.form()

        # Separate normal data and file data from the form
        data = {}
        files = {}
        print(f"[DEBUG - create_paid_event] Processing form data")
        for key, value in form_data.multi_items():
            if isinstance(value, UploadFile):
                print(f"[DEBUG - create_paid_event] File uploaded: {key}")
                # Convert FastAPI UploadFile to Django file object
                django_file = await starlette_to_django(value)
                files[key] = django_file
            else:
                print(f"[DEBUG - create_paid_event] Text field: {key} = {value}")
                data[key] = value

        @database_sync_to_async
        def process_create_event():
            try:
                # Get the current user's profile
                user = CustomUser.objects.get(id=user_id)

                # Handle UserProfile that might not exist yet
                try:
                    user_profile = UserProfile.objects.get(user=user)
                    print(
                        f"[DEBUG - create_paid_event] UserProfile found for user: {user.username}"
                    )
                except UserProfile.DoesNotExist:
                    print(
                        f"[DEBUG - create_paid_event] UserProfile not found for user: {user.username}, creating one..."
                    )
                    user_profile, created = UserProfile.objects.get_or_create(user=user)
                    print(
                        f"[DEBUG - create_paid_event] UserProfile {'created' if created else 'retrieved'} for user: {user.username}"
                    )

                # Verify the host has a Stripe Connect account set up
                if not hasattr(user, "connectAccountID") or not user.connectAccountID:
                    print(
                        f"[DEBUG - create_paid_event] User {user_id} has no Stripe Connect account set up"
                    )
                    return JSONResponse(
                        content={
                            "error": "You need to set up your Stripe account before creating a paid event.",
                            "redirect": "/host/stripe-setup/",
                        },
                        status_code=status.HTTP_400_BAD_REQUEST,
                    )

                # Verify the Stripe account is complete and ready to accept payments
                try:
                    stripe_account = stripe.Account.retrieve(user.connectAccountID)
                    if not stripe_account.get("payouts_enabled"):
                        # Create an account link for the user to complete their setup
                        account_link = stripe.AccountLink.create(
                            account=user.connectAccountID,
                            refresh_url=f"{settings.SITE_URL}/refresh/{user.connectAccountID}",
                            return_url=f"{settings.SITE_URL}/host/portal/",
                            type="account_onboarding",
                        )
                        print(
                            f"[DEBUG - create_paid_event] Stripe account link created: {account_link.url}"
                        )

                        return JSONResponse(
                            content={
                                "error": "Please complete your Stripe account setup before creating a paid event.",
                                "stripeLink": account_link.url,
                            },
                            status_code=status.HTTP_400_BAD_REQUEST,
                        )
                except stripe.error.StripeError as e:
                    return JSONResponse(
                        content={"error": f"An error occurred with Stripe: {str(e)}"},
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )

                # Determine whether the user is associated with a college
                is_in_college = user_profile.college is not None

                # Instantiate the Django form with submitted data, file uploads, instance and partial flag
                event_form = EventForm(data, files)
                print(f"[DEBUG - create_paid_event] Event form: {event_form}")

                if event_form.is_valid():
                    print(f"[DEBUG - create_paid_event] Form is valid")
                    # Get or create a host profile for the user
                    host_profile, created = HostProfile.objects.get_or_create(user=user)

                    # Create the new event
                    new_event = event_form.save(commit=False)
                    new_event.host = user  # Set the host to the current user
                    new_event.ticketing = "Paid"  # This is a paid event
                    new_event.status = "live"  # Set status to live

                    # Create a Stripe product for this event
                    try:
                        product = stripe.Product.create(
                            name=new_event.title,
                            description=new_event.description[
                                :500
                            ],  # Limit description length
                            metadata={"eventId": str(new_event.eventId)},
                        )
                        new_event.stripeProductId = product.id
                    except stripe.error.StripeError as e:
                        return JSONResponse(
                            content={
                                "error": f"An error occurred with Stripe: {str(e)}"
                            },
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        )

                    new_event.save()
                    print(f"[DEBUG - create_paid_event] Event created: {new_event}")

                    # Get or create a host profile for the user (now in sync context)
                    host_profile, created = HostProfile.objects.get_or_create(user=user)

                    # Create location serializer instance (now in sync context)
                    location = LocationSerializer(
                        building_name=new_event.building_name,
                        street=new_event.street,
                        apt_suite_unit=new_event.apt_suite_unit,
                        city=new_event.city,
                        state=new_event.state,
                        zip_code=new_event.zip_code,
                        country=new_event.country,
                        hide_address=new_event.hide_address,
                    )

                    # Create host serializer instance (now in sync context)
                    host = HostSerializer(
                        id=str(host_profile.hostProfileId),
                        name=f"{user.first_name} {user.last_name}",
                    )

                    # Process image URLs (now in sync context)
                    header_photo_url = (
                        new_event.header_photo.url if new_event.header_photo else None
                    )
                    body_photo_one_url = (
                        new_event.body_photo_one.url
                        if new_event.body_photo_one
                        else None
                    )
                    body_photo_two_url = (
                        new_event.body_photo_two.url
                        if new_event.body_photo_two
                        else None
                    )
                    body_photo_three_url = (
                        new_event.body_photo_three.url
                        if new_event.body_photo_three
                        else None
                    )
                    body_photo_four_url = (
                        new_event.body_photo_four.url
                        if new_event.body_photo_four
                        else None
                    )
                    body_photo_five_url = (
                        new_event.body_photo_five.url
                        if new_event.body_photo_five
                        else None
                    )

                    # Create event response serializer instance (now in sync context)
                    event_data = EventDetailSerializer(
                        eventId=str(new_event.eventId),
                        status=new_event.status,
                        title=new_event.title,
                        event_type=new_event.event_type,
                        date=new_event.date,
                        start_time=new_event.start_time,
                        end_time=new_event.end_time,
                        description=new_event.description,
                        ticketing=new_event.ticketing,
                        location=location,
                        header_photo=header_photo_url,
                        body_photo_one=body_photo_one_url,
                        body_photo_two=body_photo_two_url,
                        body_photo_three=body_photo_three_url,
                        body_photo_four=body_photo_four_url,
                        body_photo_five=body_photo_five_url,
                        crew_discount=new_event.crew_discount,
                        minimum_crew_size=new_event.minimum_crew_size,
                        crew_discount_percentage=new_event.crew_discount_percentage,
                        couponsActivated=new_event.couponsActivated,
                        show_guest_list=new_event.show_guest_list,
                        forAllDisplay=new_event.forAllDisplay,
                        forCollegesDisplay=new_event.forCollegesDisplay,
                        stripeProductId=new_event.stripeProductId,
                    )

                    # Properly serialize the event_data to make it JSON serializable (now in sync context)
                    serialized_event_data = event_data.model_dump(mode="json")
                    print(
                        f"[DEBUG - create_paid_event] Serialized event data: {serialized_event_data}"
                    )

                    # Return event, user, and pre-serialized data
                    return (
                        new_event,
                        user,
                        serialized_event_data,
                    )  # Return event, user and serialized data for notification

                else:
                    # Here we raise an error with the form errors so that we can return a 400 response
                    raise ValueError(event_form.errors)
            except CustomUser.DoesNotExist:
                return JSONResponse(
                    content={"error": "User not found"},
                    status_code=status.HTTP_404_NOT_FOUND,
                )
            except Exception as e:
                traceback_str = traceback.format_exc()
                print(f"Create Paid Event error: {str(e)}\n{traceback_str}")
                return JSONResponse(
                    content={"error": f"An unexpected error occurred: {str(e)}"},
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        # Execute the create event function
        result = await process_create_event()
        if isinstance(result, JSONResponse):
            return result

        # If successful, result is a tuple of (event, user, serialized_event_data)
        new_event, user, serialized_event_data = result

        # Send notifications after event creation
        await send_event_creation_notifications(new_event, user)

        # Use the pre-serialized data (no more Django model access in async context)
        result = {
            "message": "Paid event created successfully.",
            "event": serialized_event_data,
        }
        return JSONResponse(content=result, status_code=status.HTTP_200_OK)

    except ValueError as ve:
        print(f"[DEBUG - create_paid_event] ValueError: {str(ve)}")
        # Return any form validation errors
        return JSONResponse(
            content={"errors": str(ve), "message": "Failed to create event."},
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        # Log the exception details and return a server error
        traceback_str = traceback.format_exc()
        print(f"Create Paid Event error: {str(e)}\n{traceback_str}")
        await notify_by_bot(
            f"**[API: create_paid_event]** \n\n Error creating paid event: error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(
            status_code=500, detail=f"Error creating paid event: {str(e)}"
        )


@router.get("/event/get_host_stripe_account_link")
async def get_host_stripe_account_link(
    request: Request,
    user_id: int = Depends(get_current_user),
    platform: Optional[str] = None,
):
    print(
        f"[DEBUG - get_host_stripe_account_link] Called with user_id={user_id}, platform={platform}"
    )

    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]
    print(
        f"[DEBUG - get_host_stripe_account_link] user_agent='{user_agent_str}', device_info={device_info}"
    )

    @database_sync_to_async
    def process_stripe_account_check():
        try:
            print(
                "[DEBUG - get_host_stripe_account_link] Beginning Stripe account check for user"
            )
            # Get the user account with proper error handling
            user = get_object_or_404(CustomUser, id=user_id)
            print(
                f"[DEBUG - get_host_stripe_account_link] Loaded user id={user.id}, username={getattr(user, 'username', None)}, connectAccountID={getattr(user, 'connectAccountID', None)}"
            )

            # Check if user has a Stripe Connect account ID
            if not user.connectAccountID:
                print(
                    "[DEBUG - get_host_stripe_account_link] Missing connectAccountID; returning setup redirect"
                )
                return JSONResponse(
                    content={
                        "error": "You need to set up your Stripe account first.",
                        "redirect": "/host/stripe-setup/",
                    },
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            # Initialize account status flag
            is_fully_onboarded = False

            # Check the Stripe account status
            try:
                # Retrieve the Stripe account details
                print(
                    f"[DEBUG - get_host_stripe_account_link] Retrieving Stripe account {user.connectAccountID}"
                )
                stripe_account = stripe.Account.retrieve(user.connectAccountID)
                is_fully_onboarded = stripe_account.get("payouts_enabled", False)
                print(
                    f"[DEBUG - get_host_stripe_account_link] Stripe account retrieved: payouts_enabled={is_fully_onboarded}, charges_enabled={stripe_account.get('charges_enabled')}, details_submitted={stripe_account.get('details_submitted')}, capabilities={stripe_account.get('capabilities')}"
                )

                # Create an account link for onboarding or updating account details
                print(
                    "[DEBUG - get_host_stripe_account_link] Creating Stripe AccountLink (account_onboarding)"
                )
                account_link = stripe.AccountLink.create(
                    account=user.connectAccountID,
                    refresh_url=f"{settings.SITE_URL}/refresh/{user.connectAccountID}",
                    return_url=f"{settings.SITE_URL}/host/portal/",
                    type="account_onboarding",
                )
                print(
                    f"[DEBUG - get_host_stripe_account_link] AccountLink created: url={getattr(account_link, 'url', None)}"
                )

                # Return appropriate response based on account status
                if not is_fully_onboarded:
                    print(
                        "[DEBUG - get_host_stripe_account_link] Not fully onboarded; returning onboarding link"
                    )
                    return JSONResponse(
                        content={
                            "error": "Please complete your Stripe account setup.",
                            "stripeLink": account_link.url,  # Include the URL, not the entire object
                        },
                        status_code=status.HTTP_200_OK,  # Using 200 instead of 400 as this is an expected state
                    )
                else:
                    print(
                        "[DEBUG - get_host_stripe_account_link] Fully onboarded; returning update link"
                    )
                    return JSONResponse(
                        content={
                            "success": "Stripe account setup completed.",
                            "updateLink": account_link.url,  # Provide link for updating account details
                        },
                        status_code=status.HTTP_200_OK,
                    )
            except stripe.error.StripeError as e:
                # Log the specific Stripe error for debugging
                print(
                    f"[DEBUG - get_host_stripe_account_link] Stripe error: {str(e)}, user_message={getattr(e, 'user_message', None)}, code={getattr(e, 'code', None)}"
                )
                return JSONResponse(
                    content={"error": f"Stripe error: {str(e)}"},
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
        except CustomUser.DoesNotExist:
            print(
                f"[DEBUG - get_host_stripe_account_link] User not found for id={user_id}"
            )
            return JSONResponse(
                content={"error": "User not found"},
                status_code=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            # Include traceback for unexpected errors
            traceback_str = traceback.format_exc()
            print(
                f"[DEBUG - get_host_stripe_account_link] Unexpected error: {str(e)}\n{traceback_str}\nplatform={platform}, device_info={device_info}"
            )
            return JSONResponse(
                content={"error": f"An unexpected error occurred: {str(e)}"},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # Execute the function and return the result
    result = await process_stripe_account_check()
    print(
        f"[DEBUG - get_host_stripe_account_link] Completed with status_code={getattr(result, 'status_code', None)}"
    )
    return result


@router.get("/event/paid/ticket/fields")
async def paid_ticket_creation_fields(request: Request):
    print(f"[DEBUG - paid_ticket_creation_fields] Function called")
    FormClass = PaidFreeTicketForm
    fields_info = get_form_fields(FormClass)
    print(
        f"[DEBUG - paid_ticket_creation_fields] Returning form fields: {list(fields_info.keys())}"
    )
    return JSONResponse(content=fields_info, status_code=status.HTTP_200_OK)


@router.post("/event/{eventId}/createPaidFreeTicket")
async def create_paid_free_ticket(
    eventId: str,
    request: Request,
    platform: Optional[str] = None,
):
    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:
        form_data = await request.form()
        data = dict(form_data)

        @database_sync_to_async
        def process_create_ticket(eventId, data):
            # Fetch the event object or raise a 404 error if not found
            try:
                event = Event.objects.get(eventId=eventId)
            except Event.DoesNotExist:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
                )

            # Map frontend field names to model field names if needed
            form_data = {}
            field_mapping = {
                "ticket_name": "ticket_name",
                "ticket_price": "ticket_price",
                "ticket_description": "ticket_description",
                "ticket_quantity": "ticket_quantity",
                # Add any other mappings that might be needed
            }

            # Process the data to ensure field names match what the form expects
            for frontend_key, model_key in field_mapping.items():
                # Try different possible keys from the frontend
                if frontend_key in data:
                    form_data[model_key] = data[frontend_key]
                elif model_key in data:
                    form_data[model_key] = data[model_key]

            print(f"[DEBUG - create_paid_free_ticket] Processed form data: {form_data}")

            # Instantiate the Django form with processed data
            ticket_form = PaidFreeTicketForm(form_data)

            if ticket_form.is_valid():
                print(f"[DEBUG - create_paid_free_ticket] Ticket form is valid")
                # Create the new ticket
                new_ticket = ticket_form.save(commit=False)
                new_ticket.event = event  # Associate the ticket with the event
                new_ticket.save()

                return {
                    "message": "Ticket created successfully.",
                    "code": str(new_ticket.ticket_id),  # Use ticket_id instead of code
                    "eventId": str(event.eventId),
                    "ticketPrice": str(
                        new_ticket.ticket_price
                    ),  # Convert to string for JSON serialization
                }
            else:
                print(
                    f"[DEBUG - create_paid_free_ticket] Ticket form is invalid: {ticket_form.errors}"
                )
                # Here we raise an error with the form errors so that we can return a 400 response.
                raise ValueError(ticket_form.errors)

        # Execute the create ticket function
        result = await process_create_ticket(eventId, data)
        print(
            f"[DEBUG - create_paid_free_ticket] Ticket created with ID: {result.get('code', 'unknown')}"
        )
        return JSONResponse(content=result, status_code=status.HTTP_200_OK)

    except ValueError as ve:
        # Return any form validation errors
        return JSONResponse(
            content={"errors": str(ve), "message": "Failed to create ticket."},
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        # Log the exception details and return a server error
        traceback_str = traceback.format_exc()
        print(f"Create Event Tickets error: {str(e)}\n{traceback_str}")
        await notify_by_bot(
            f"**[API: create_paid_free_ticket]** \n\n Error creating ticket: eventId={eventId}, error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(status_code=500, detail=f"Error creating ticket: {str(e)}")


@router.get("/event/paid/coupon/fields")
async def paid_coupon_creation_fields(request: Request):
    print(f"[DEBUG - paid_coupon_creation_fields] Function called")
    FormClass = CouponCodeForm
    fields_info = get_form_fields(FormClass)
    print(
        f"[DEBUG - paid_coupon_creation_fields] Returning form fields: {list(fields_info.keys())}"
    )
    return JSONResponse(content=fields_info, status_code=status.HTTP_200_OK)


@router.get("/event/{eventId}/coupons")
async def get_event_coupons(
    eventId: str,
    request: Request,
    platform: Optional[str] = None,
):
    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def get_event_coupons_sync(event_id):
        print(f"[DEBUG - get_event_coupons] Fetching coupons for event: {event_id}")
        # Fetch the event object or return None if not found
        try:
            event = Event.objects.get(eventId=event_id)
        except Event.DoesNotExist:
            return None

        coupon_codes = CouponCode.objects.filter(event=event).values()
        coupons_list = []
        for coupon in coupon_codes:
            # Convert all UUID fields to strings
            for key, value in coupon.items():
                if isinstance(value, UUID):
                    coupon[key] = str(value)
            # Create a standardized response format with datetime objects converted to ISO format strings
            coupon_data = {
                "couponId": coupon["coupon_id"],
                "code": coupon["code"],
                "discountPercentage": coupon["discount_percentage"],
                "createdAt": (
                    coupon["created_at"].isoformat() if coupon["created_at"] else None
                ),
                "updatedAt": (
                    coupon["updated_at"].isoformat() if coupon["updated_at"] else None
                ),
            }
            coupons_list.append(coupon_data)
        return coupons_list

    try:
        # Execute synchronous function asynchronously
        coupons = await get_event_coupons_sync(eventId)

        if coupons is None:
            await notify_by_bot(
                f"**[API: get_event_coupons]** \n\n Event not found: eventId={eventId} \n\n Platform: {platform}",
                platform or "Unknown",
                "ERROR",
                device_info,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
            )

        print(f"[DEBUG - get_event_coupons] Found {len(coupons)} coupons")
        return JSONResponse(content=coupons, status_code=status.HTTP_200_OK)
    except HTTPException:
        raise
    except Exception as e:
        await notify_by_bot(
            f"**[API: get_event_coupons]** \n\n Error fetching coupons: eventId={eventId}, error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching coupons: {str(e)}",
        )


@router.get("/event/{eventId}/paid/tickets")
async def get_paid_event_tickets(
    eventId: str,
    request: Request,
    platform: Optional[str] = None,
):
    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def get_paid_event_tickets_sync(event_id):
        print(
            f"[DEBUG - get_paid_event_tickets] Fetching tickets for event: {event_id}"
        )
        # Fetch the event object or return None if not found
        try:
            event = Event.objects.get(eventId=event_id)
        except Event.DoesNotExist:
            return None

        tickets = PaidFreeTicket.objects.filter(event=event).values()
        tickets_list = []
        for ticket in tickets:
            # Convert all non-JSON serializable types to strings
            for key, value in ticket.items():
                if isinstance(value, UUID):
                    ticket[key] = str(value)
                elif isinstance(value, datetime):
                    ticket[key] = value.isoformat()
                elif isinstance(value, Decimal):
                    ticket[key] = str(value)
            tickets_list.append(ticket)
        return tickets_list

    try:
        # Execute synchronous function asynchronously
        tickets = await get_paid_event_tickets_sync(eventId)

        if tickets is None:
            await notify_by_bot(
                f"**[API: get_paid_event_tickets]** \n\n Event not found: eventId={eventId} \n\n Platform: {platform}",
                platform or "Unknown",
                "ERROR",
                device_info,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
            )

        print(f"[DEBUG - get_paid_event_tickets] Found {len(tickets)} tickets")
        return JSONResponse(content=tickets, status_code=status.HTTP_200_OK)
    except HTTPException:
        raise
    except Exception as e:
        await notify_by_bot(
            f"**[API: get_paid_event_tickets]** \n\n Error fetching tickets: eventId={eventId}, error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching tickets: {str(e)}",
        )


@router.post("/event/{eventId}/paid/ticket/delete")
async def delete_paid_event_ticket(
    eventId: str,
    request: Request,
    platform: Optional[str] = None,
):
    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:
        form_data = await request.form()
        ticket_id = form_data.get("ticket_id")

        @database_sync_to_async
        def delete_ticket_sync(event_id, ticket_id):
            try:
                event = Event.objects.get(eventId=event_id)
            except Event.DoesNotExist:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
                )

            try:
                ticket = PaidFreeTicket.objects.get(ticket_id=ticket_id, event=event)
            except PaidFreeTicket.DoesNotExist:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found"
                )

            ticket.delete()
            return {"message": "Ticket deleted successfully"}

        # Execute the delete function
        result = await delete_ticket_sync(eventId, ticket_id)
        print(f"[DEBUG - delete_paid_event_ticket] Result: {result}")
        return JSONResponse(content=result, status_code=status.HTTP_200_OK)

    except Event.DoesNotExist:
        return JSONResponse(
            content={"message": "Event not found."},
            status_code=status.HTTP_404_NOT_FOUND,
        )
    except Exception as e:
        traceback_str = traceback.format_exc()
        print(f"Delete Paid Event Ticket error: {str(e)}\n{traceback_str}")
        await notify_by_bot(
            f"**[API: delete_paid_event_ticket]** \n\n Error deleting ticket: eventId={eventId}, error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(status_code=500, detail=f"Error deleting ticket: {str(e)}")


@router.post("/event/{eventId}/createCoupon")
async def create_event_coupon(
    eventId: str,
    payload: dict,
    request: Request,
    platform: Optional[str] = None,
):
    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def create_coupon(eventId, payload):
        try:
            event = Event.objects.get(eventId=eventId)
        except Event.DoesNotExist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
            )

        coupon_form = CouponCodeForm(payload)

        if not coupon_form.is_valid():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=coupon_form.errors.as_json(),
            )

        coupon = coupon_form.save(commit=False)
        coupon.event = event
        coupon.save()

        return {
            "message": "Coupon created successfully",
            "coupon": {
                "code": coupon.code,
                "discount_percentage": coupon.discount_percentage,
            },
        }

    try:
        result = await create_coupon(eventId, payload)
        return JSONResponse(content=result, status_code=status.HTTP_200_OK)
    except Exception as e:
        if not isinstance(e, HTTPException):
            error_trace = traceback.format_exc()
            print(f"Create Event Coupon error: {str(e)}\n{error_trace}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"An unexpected error occurred: {str(e)}",
            )
        raise e


class DeleteCouponRequest(BaseModel):
    coupon_id: str


@router.post("/event/{eventId}/deleteCoupon")
async def delete_coupon(
    eventId: str,
    deleteCouponRequest: DeleteCouponRequest,
    request: Request,
    platform: Optional[str] = None,
):
    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def delete_coupon_sync(event_id, coupon_id):
        try:
            event = Event.objects.get(eventId=event_id)
        except Event.DoesNotExist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
            )

        try:
            coupon = CouponCode.objects.get(coupon_id=coupon_id)
        except CouponCode.DoesNotExist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Coupon not found"
            )

        if coupon.event != event:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Coupon does not belong to this event",
            )
        coupon.delete()
        return {"message": "Coupon deleted successfully"}

    try:
        result = await delete_coupon_sync(eventId, deleteCouponRequest.coupon_id)
        return JSONResponse(content=result, status_code=status.HTTP_200_OK)
    except Exception as e:
        if not isinstance(e, HTTPException):
            error_trace = traceback.format_exc()
            print(f"Delete Event Coupon error: {str(e)}\n{error_trace}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"An unexpected error occurred: {str(e)}",
            )
        raise e


@router.get("/event/{eventId}/rsvp")
async def get_event_rsvp_list(
    eventId: str,
    request: Request,
    platform: Optional[str] = None,
):
    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def get_event_rsvp_list_sync(event_id):
        print(f"[DEBUG - get_event_rsvp_list] Fetching RSVP list for event: {event_id}")
        # Fetch the event object or raise a 404 error if not found
        event = get_object_or_404(Event, eventId=event_id)
        rsvp_list = RSVPTicket.objects.filter(event=event).values()
        rsvp_list_data = []
        for rsvp in rsvp_list:
            # Convert all non-JSON serializable types to strings
            for key, value in rsvp.items():
                if isinstance(value, UUID):
                    rsvp[key] = str(value)
                elif isinstance(value, datetime):
                    rsvp[key] = value.isoformat()
            rsvp_list_data.append(rsvp)
        return rsvp_list_data

    # Execute synchronous function asynchronously
    rsvp_list = await get_event_rsvp_list_sync(eventId)
    print(f"[DEBUG - get_event_rsvp_list] Found {len(rsvp_list)} RSVP entries")
    return JSONResponse(content=rsvp_list, status_code=status.HTTP_200_OK)


@router.api_route("/event/{eventId}/rsvp/delete", methods=["DELETE", "POST"])
async def delete_event_rsvp(
    eventId: str,
    request: Request,
    ticket_id: Optional[str] = None,
    user_id: int = Depends(get_current_user),
    platform: Optional[str] = None,
):
    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:
        # If ticket_id is not provided in the path, try to get it from the request body
        if not ticket_id:
            try:
                form_data = await request.form()
                ticket_id = form_data.get("ticket_id")
            except:
                pass

        if not ticket_id:
            raise HTTPException(status_code=400, detail="ticket_id is required")

        @database_sync_to_async
        def delete_rsvp_ticket():
            # Get the event object or raise a 404 error if not found
            event = get_object_or_404(Event, eventId=eventId)

            # Get the current user
            user = CustomUser.objects.get(id=user_id)

            # Check if the requesting user is the host of the event
            if event.host != user:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have permission to delete RSVP tickets. Only the event host can manage tickets.",
                )

            try:
                # First try to find the RSVP ticket
                rsvp_ticket = RSVPTicket.objects.get(ticket_id=ticket_id, event=event)

                # Also find and delete any associated tickets with QR code
                deleted_count = 0
                try:
                    # Use similar criteria as in the Django view to find associated tickets
                    tickets_to_delete = Ticket.objects.filter(
                        event=event, guestEmail=rsvp_ticket.email
                    )

                    # Delete the tickets and get count
                    deleted_count = tickets_to_delete.count()
                    tickets_to_delete.delete()

                except Exception as e:
                    # Continue even if no associated tickets found
                    print(f"Error while deleting associated tickets: {str(e)}")

                # Delete the RSVP ticket itself
                rsvp_ticket.delete()

                # Return success message with count of associated tickets deleted
                return {
                    "message": f"RSVP deleted successfully with {deleted_count} associated ticket(s)."
                }

            except RSVPTicket.DoesNotExist:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="RSVP ticket not found.",
                )

        # Execute the delete function
        result = await delete_rsvp_ticket()
        print(f"[DEBUG - delete_event_rsvp] Result: {result}")
        return JSONResponse(content=result, status_code=status.HTTP_200_OK)

    except HTTPException as http_ex:
        # Handle HTTP exceptions separately
        return JSONResponse(
            content={"error": str(http_ex.detail)},
            status_code=http_ex.status_code,
        )
    except Exception as e:
        traceback_str = traceback.format_exc()
        print(f"Delete RSVP Ticket error: {str(e)}\n{traceback_str}")

        # Return error response
        return JSONResponse(
            content={"error": f"An unexpected error occurred: {str(e)}"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get("/event/{eventId}/purchasedTickets")
async def get_purchased_tickets_for_event(
    eventId: str,
    request: Request,
    user_id: int = Depends(get_current_user),
    platform: Optional[str] = None,
):
    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def get_purchased_tickets_sync(event_id):
        print(
            f"[DEBUG - get_purchased_tickets_for_event] Fetching purchased tickets for event: {event_id}"
        )
        # Get the event object or raise a 404 error if not found
        event = get_object_or_404(Event, eventId=event_id)

        # Get the current user
        user = CustomUser.objects.get(id=user_id)

        # Check if the requesting user is the host of the event
        if event.host != user:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access these tickets. Only the event host can view ticket information.",
            )
        # Get all purchased tickets for the event
        purchased_tickets = Ticket.objects.filter(event=event)

        # Serialize the tickets for the response
        ticket_data = TicketSerializer(purchased_tickets, many=True).data

        # Convert non-JSON serializable types to strings
        for ticket in ticket_data:
            for key, value in ticket.items():
                if isinstance(value, UUID):
                    ticket[key] = str(value)
                elif isinstance(value, datetime):
                    ticket[key] = value.isoformat()

        return ticket_data

    # Execute synchronous function asynchronously
    purchased_tickets_data = await get_purchased_tickets_sync(eventId)
    print(
        f"[DEBUG - get_purchased_tickets_for_event] Found {len(purchased_tickets_data)} purchased tickets"
    )

    return JSONResponse(
        content={"purchasedTickets": purchased_tickets_data},
        status_code=status.HTTP_200_OK,
    )


@router.post("/event/{eventId}/purchasedTickets/delete")
async def delete_purchased_ticket(
    eventId: str,
    request: Request,
    user_id: int = Depends(get_current_user),
    platform: Optional[str] = None,
):
    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:
        form_data = await request.form()
        ticket_id = form_data.get("ticket_id")

        if not ticket_id:
            raise HTTPException(status_code=400, detail="ticket_id is required")

        @database_sync_to_async
        def delete_purchased_ticket_sync():
            # Get the event object or raise a 404 error if not found
            event = get_object_or_404(Event, eventId=eventId)

            # Get the current user
            user = CustomUser.objects.get(id=user_id)

            # Check if the requesting user is the host of the event
            if event.host != user:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have permission to delete tickets. Only the event host can manage tickets.",
                )

            try:
                # Find the ticket to delete
                ticket = Ticket.objects.get(ticketId=ticket_id, event=event)

                # Delete the ticket
                ticket.delete()

                # Return success message
                return {"message": "Purchased ticket deleted successfully."}

            except Ticket.DoesNotExist:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found."
                )

        # Execute the delete function
        result = await delete_purchased_ticket_sync()
        print(f"[DEBUG - delete_purchased_ticket] Result: {result}")
        return JSONResponse(content=result, status_code=status.HTTP_200_OK)

    except HTTPException as http_ex:
        # Handle HTTP exceptions separately
        return JSONResponse(
            content={"error": str(http_ex.detail)},
            status_code=http_ex.status_code,
        )
    except Exception as e:
        traceback_str = traceback.format_exc()
        print(f"Delete Purchased Ticket error: {str(e)}\n{traceback_str}")

        # Return error response
        return JSONResponse(
            content={"error": f"An unexpected error occurred: {str(e)}"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.post("/event/becomeHost")
async def become_host(
    request: Request,
    user_id: int = Depends(get_current_user),
    platform: Optional[str] = None,
):
    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def process_become_host():
        try:
            # Get the current user
            user = get_object_or_404(CustomUser, id=user_id)

            # Set up common variables for Stripe redirect URLs
            site_domain = "https://wave.buzz"
            redirect_link = f"{site_domain}/host/portal/"

            # Check if the user has a Stripe Connect account
            has_connect_account = bool(user.connectAccountID)
            is_host = user.groups.filter(name="Host").exists()
            is_fully_onboarded = False

            # If user has a Connect account, check if it's fully set up
            if has_connect_account:
                try:
                    stripe_account = stripe.Account.retrieve(user.connectAccountID)
                    is_fully_onboarded = stripe_account.get("payouts_enabled", False)
                except stripe.error.StripeError as e:
                    return JSONResponse(
                        content={"error": f"Stripe error: {str(e)}"},
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )

            # Case 1: User is a host and fully onboarded with Stripe
            if is_host and is_fully_onboarded:
                return JSONResponse(
                    content={
                        "message": "You are already a host with a complete Stripe setup."
                    },
                    status_code=status.HTTP_200_OK,
                )

            # Case 2: User is a host but not fully onboarded with Stripe
            if is_host and has_connect_account and not is_fully_onboarded:
                try:
                    stripe_link_account = ConnectAccount.getStripeOnboardingLink(
                        None, user.connectAccountID, site_domain, redirect_link
                    )
                    return JSONResponse(
                        content={
                            "message": "Please complete your Stripe account setup.",
                            "stripe_onboarding_link": stripe_link_account,
                            "connect_account_id": user.connectAccountID,
                        },
                        status_code=status.HTTP_200_OK,
                    )
                except stripe.error.StripeError as e:
                    return JSONResponse(
                        content={
                            "error": f"Failed to generate onboarding link: {str(e)}"
                        },
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )

            # Case 3: User is a host but has no Stripe account
            if is_host and not has_connect_account:
                return JSONResponse(
                    content={
                        "message": "You are a host but missing Stripe setup. Please contact support."
                    },
                    status_code=status.HTTP_200_OK,
                )

            # Case 4: User is not a host and needs to be set up
            # First check if they have an existing Stripe account by email
            if not has_connect_account:
                try:
                    # Look for existing account with matching email
                    stripe_accounts = stripe.Account.list(limit=10)
                    existing_account = None

                    for account in stripe_accounts.data:
                        if account.get("email") == user.email:
                            existing_account = account
                            break

                    if existing_account:
                        # Delete old account if found to avoid duplicates
                        stripe.Account.delete(existing_account.id)

                    # Create a new Stripe Connect account
                    stripe_connect_account = ConnectAccount.createConnectAccount(
                        None, user
                    )

                    if not stripe_connect_account:
                        return JSONResponse(
                            content={
                                "error": "Failed to create Stripe Connect account"
                            },
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        )

                    # Update user with new account ID
                    user.connectAccountID = stripe_connect_account.id
                    user.connectAccountCreated = True

                except stripe.error.StripeError as e:
                    return JSONResponse(
                        content={"error": f"Stripe error: {str(e)}"},
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )

            # Generate onboarding link
            try:
                stripe_link_account = ConnectAccount.getStripeOnboardingLink(
                    None, user.connectAccountID, site_domain, redirect_link
                )
            except stripe.error.StripeError as e:
                return JSONResponse(
                    content={"error": f"Failed to generate onboarding link: {str(e)}"},
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            # Assign "Host" role if not already assigned
            if not is_host:
                event_host, created = Group.objects.get_or_create(name="Host")
                user.groups.add(event_host)

            # Save the user with updated connectAccountID
            user.save()

            return {
                "message": "Welcome to hosting on WAVE.",
                "stripe_onboarding_link": stripe_link_account,
                "connect_account_id": user.connectAccountID,
            }

        except CustomUser.DoesNotExist:
            return JSONResponse(
                content={"error": "User not found"},
                status_code=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            traceback_str = traceback.format_exc()
            print(f"Become Host error: {str(e)}\n{traceback_str}")
            return JSONResponse(
                content={"error": f"An unexpected error occurred: {str(e)}"},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # Execute the become host function
    result = await process_become_host()
    if isinstance(result, JSONResponse):
        return result
    return JSONResponse(content=result, status_code=status.HTTP_200_OK)


@router.get("/event/{eventId}/analytics")
async def get_event_analytics(
    eventId: str,
    request: Request,
    user_id: int = Depends(get_current_user),
    platform: Optional[str] = None,
):
    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def get_analytics_data(event_id, requesting_user_id):
        try:
            from django.db.models import Q, Count, Sum, Avg
            from django.db.models.functions import TruncHour, TruncDay
            from collections import defaultdict
            from datetime import datetime, timedelta
            from django.utils import timezone

            # Get the event and verify the user is the host
            event = get_object_or_404(Event, eventId=event_id)
            requesting_user = get_object_or_404(CustomUser, id=requesting_user_id)

            # Check if the requesting user is the host of the event
            if event.host != requesting_user:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have permission to access analytics for this event. Only the event host can view analytics.",
                )

            # ===========================================
            # 1. PERFORMANCE METRICS
            # ===========================================

            # Total Views
            total_views = event.views

            # Total Favorites
            total_favorites = UserProfile.objects.filter(favorite_events=event).count()

            # Total Shares
            total_shares = SharedEvent.objects.filter(event=event).count()

            # Total Go With Requests
            total_go_with_requests = GoWithRequest.objects.filter(event=event).count()

            # Unique Visitors from EventView model
            unique_visitors = EventView.objects.filter(event=event).count()

            # Return Visitors (users who have viewed multiple events from the same host)
            return_visitors = 0
            if total_views > 0:
                # Users who have viewed other events by this host
                host_events = Event.objects.filter(host=event.host).exclude(
                    eventId=event.eventId
                )
                viewed_users = EventView.objects.filter(
                    event=event, user__isnull=False
                ).values_list("user_id", flat=True)
                return_visitors = (
                    EventView.objects.filter(
                        event__in=host_events, user_id__in=viewed_users
                    )
                    .values("user_id")
                    .distinct()
                    .count()
                )

            # ===========================================
            # 2. TICKET PERFORMANCE & REVENUE
            # ===========================================

            # Get all tickets for this event
            tickets = Ticket.objects.filter(event=event).select_related("user")
            total_tickets_sold = tickets.count()
            unique_purchasers = tickets.values("user", "guestEmail").distinct().count()

            # Calculate total revenue and average order value
            total_revenue = 0
            average_order_value = 0
            ticket_type_performance = []

            if event.ticketing == "Paid":
                # Get ticket types for this event
                ticket_types = PaidFreeTicket.objects.filter(event=event)

                for ticket_type in ticket_types:
                    tickets_sold = ticket_type.ticket_sold
                    price = (
                        float(ticket_type.ticket_price)
                        if ticket_type.ticket_price
                        else 0
                    )
                    revenue = price * tickets_sold
                    total_revenue += revenue

                    # Ticket type performance breakdown
                    ticket_type_performance.append(
                        {
                            "ticket_name": ticket_type.ticket_name,
                            "ticket_price": price,
                            "tickets_available": ticket_type.ticket_quantity,
                            "tickets_sold": tickets_sold,
                            "revenue": revenue,
                            "sell_through_rate": (
                                round(
                                    (tickets_sold / ticket_type.ticket_quantity) * 100,
                                    1,
                                )
                                if ticket_type.ticket_quantity > 0
                                else 0
                            ),
                        }
                    )

                # Calculate average order value
                if unique_purchasers > 0:
                    average_order_value = round(total_revenue / unique_purchasers, 2)

            # Conversion rate
            conversion_rate = 0
            if total_views > 0:
                conversion_rate = round(
                    min((unique_purchasers / total_views) * 100, 100), 1
                )

            # ===========================================
            # 3. AUDIENCE ANALYTICS
            # ===========================================

            # Login status distribution
            logged_in_users = tickets.filter(user__isnull=False).count()
            guest_users = tickets.filter(user__isnull=True).count()

            # Attendance distribution
            scanned_tickets = tickets.filter(status="Scanned").count()
            not_attended = total_tickets_sold - scanned_tickets

            # Geographic distribution (by user cities)
            geographic_distribution = []
            try:
                # Get cities from ticket holders
                user_cities = (
                    UserProfile.objects.filter(
                        user__in=tickets.filter(user__isnull=False).values("user")
                    )
                    .exclude(city__isnull=True)
                    .exclude(city="")
                    .values("city")
                    .annotate(count=Count("city"))
                    .order_by("-count")[:10]
                )  # Top 10 cities

                for city_data in user_cities:
                    geographic_distribution.append(
                        {"city": city_data["city"], "count": city_data["count"]}
                    )
            except Exception as e:
                print(f"Error calculating geographic distribution: {e}")

            # Demographics (Note: Limited data due to UserProfile changes)
            # Age and Gender distribution would be limited due to removed fields
            age_distribution = {
                "message": "Age data not available due to privacy updates"
            }
            gender_distribution = {
                "message": "Gender data not available due to privacy updates"
            }

            # ===========================================
            # 4. PAGE ANALYTICS
            # ===========================================

            # Calculate average time on page and bounce rate
            event_views = EventView.objects.filter(event=event).order_by("timestamp")

            # For bounce rate, we consider users who only viewed this event page
            # and no other pages (simplified metric)
            bounce_rate = 0
            avg_time_on_page = 0

            try:
                # Calculate basic page metrics
                if event_views.exists():
                    # Simplified bounce rate: users with only one view session
                    single_view_users = (
                        event_views.values("user", "session_key")
                        .annotate(view_count=Count("id"))
                        .filter(view_count=1)
                        .count()
                    )

                    total_view_sessions = (
                        event_views.values("user", "session_key").distinct().count()
                    )
                    if total_view_sessions > 0:
                        bounce_rate = round(
                            (single_view_users / total_view_sessions) * 100, 1
                        )

                # Simplified average time (placeholder - would need session tracking for accuracy)
                avg_time_on_page = (
                    "Not available - requires session tracking implementation"
                )

            except Exception as e:
                print(f"Error calculating page analytics: {e}")

            # ===========================================
            # 5. TEMPORAL ANALYTICS
            # ===========================================

            # Hourly page views (last 24 hours from event views)
            hourly_views = []
            try:
                # Get views from the last 7 days, grouped by hour
                last_week = timezone.now() - timedelta(days=7)
                hourly_data = (
                    event_views.filter(timestamp__gte=last_week)
                    .extra(select={"hour": "EXTRACT(hour FROM timestamp)"})
                    .values("hour")
                    .annotate(view_count=Count("id"))
                    .order_by("hour")
                )

                # Fill in missing hours with 0 views
                hours_dict = {hour["hour"]: hour["view_count"] for hour in hourly_data}
                for hour in range(24):
                    hourly_views.append(
                        {"hour": f"{hour:02d}:00", "views": hours_dict.get(hour, 0)}
                    )

            except Exception as e:
                print(f"Error calculating hourly views: {e}")
                hourly_views = [{"hour": f"{h:02d}:00", "views": 0} for h in range(24)]

            # ===========================================
            # 6. SOCIAL MEDIA & ENGAGEMENT
            # ===========================================

            # Social media shares breakdown (could be expanded with platform-specific data)
            social_media_shares = {
                "total_shares": total_shares,
                "platforms": {
                    "general": total_shares  # Placeholder - could be expanded with platform-specific tracking
                },
            }

            # ===========================================
            # 7. CUSTOMER DATA
            # ===========================================

            # Enhanced customer data
            customers = []
            for ticket in tickets.order_by("-created_at"):
                # Determine ticket type
                ticket_type = "General Admission"  # Default
                try:
                    if event.ticketing == "Paid":
                        # Try to determine ticket type from available ticket types
                        # This is a simplified approach - in practice, you'd want to track this relationship
                        first_ticket_type = PaidFreeTicket.objects.filter(
                            event=event
                        ).first()
                        if first_ticket_type:
                            ticket_type = first_ticket_type.ticket_name
                except Exception:
                    pass

                customer = {
                    "first_name": (
                        ticket.user.first_name if ticket.user else ticket.guestFirstName
                    ),
                    "last_name": (
                        ticket.user.last_name if ticket.user else ticket.guestLastName
                    ),
                    "email": ticket.user.email if ticket.user else ticket.guestEmail,
                    "ticket_type": ticket_type,
                    "purchase_date": (
                        ticket.created_at.isoformat() if ticket.created_at else None
                    ),
                    "status": ticket.status,
                    "user_type": "Registered" if ticket.user else "Guest",
                }
                customers.append(customer)

            # ===========================================
            # 8. COMPREHENSIVE RESPONSE STRUCTURE
            # ===========================================

            analytics_data = {
                "event": {
                    "eventId": str(event.eventId),
                    "title": event.title,
                    "date": event.date.isoformat() if event.date else None,
                    "ticketing_type": event.ticketing,
                    "status": event.status,
                    "header_photo": str(event.header_photo.url),
                },
                "performance_metrics": {
                    "total_views": total_views,
                    "unique_visitors": unique_visitors,
                    "return_visitors": return_visitors,
                    "total_favorites": total_favorites,
                    "total_shares": total_shares,
                    "total_go_with_requests": total_go_with_requests,
                    "conversion_rate": conversion_rate,
                },
                "revenue_analytics": {
                    "total_revenue": round(total_revenue, 2),
                    "average_order_value": average_order_value,
                    "total_tickets_sold": total_tickets_sold,
                    "unique_purchasers": unique_purchasers,
                },
                "ticket_performance": {
                    "ticket_types": ticket_type_performance,
                    "sales_by_category": {
                        "paid_tickets": (
                            total_tickets_sold if event.ticketing == "Paid" else 0
                        ),
                        "free_tickets": (
                            total_tickets_sold if event.ticketing == "Free" else 0
                        ),
                    },
                },
                "audience_analytics": {
                    "login_status_distribution": {
                        "logged_in_users": logged_in_users,
                        "guest_users": guest_users,
                    },
                    "attendance_distribution": {
                        "attended": scanned_tickets,
                        "did_not_attend": not_attended,
                    },
                    "geographic_distribution": geographic_distribution,
                    "age_distribution": age_distribution,
                    "gender_distribution": gender_distribution,
                },
                "page_analytics": {
                    "avg_time_on_page": avg_time_on_page,
                    "bounce_rate": bounce_rate,
                    "unique_visitors": unique_visitors,
                    "return_visitors": return_visitors,
                },
                "temporal_analytics": {
                    "hourly_page_views": hourly_views,
                },
                "social_engagement": {
                    "social_media_shares": social_media_shares,
                    "total_engagement": total_favorites
                    + total_shares
                    + total_go_with_requests,
                },
                "customers": customers,
                # Legacy fields for backward compatibility
                "engagement": {
                    "event_shares": total_shares,
                    "event_favorites": total_favorites,
                    "event_go_with": total_go_with_requests,
                },
                "conversion": {
                    "ticket_conversion_rate": conversion_rate,
                    "total_unique_purchasers": unique_purchasers,
                },
                "distribution": {
                    "login_status": {
                        "Logged-in Users": logged_in_users,
                        "Guest Users": guest_users,
                    },
                    "attendance": {
                        "Attended": scanned_tickets,
                        "Did Not Attend": not_attended,
                    },
                },
                "tickets": {
                    "total_tickets_count": total_tickets_sold,
                    "scanned_tickets_count": scanned_tickets,
                },
            }

            print(
                f"[get_analytics_data] Successfully retrieved comprehensive analytics for event: {event.title}"
            )
            return analytics_data

        except Event.DoesNotExist:
            print(f"[get_analytics_data] Event not found with ID: {event_id}")
            raise HTTPException(status_code=404, detail="Event not found")
        except CustomUser.DoesNotExist:
            print(f"[get_analytics_data] User not found with ID: {requesting_user_id}")
            raise HTTPException(status_code=404, detail="User not found")
        except Exception as e:
            print(f"[get_analytics_data] Error retrieving analytics: {str(e)}")
            import traceback

            print(traceback.format_exc())
            raise HTTPException(
                status_code=500, detail=f"Error retrieving analytics: {str(e)}"
            )

    try:
        analytics_data = await get_analytics_data(eventId, user_id)
        print(
            f"[get_event_analytics] Returning comprehensive analytics for event: {analytics_data['event']['title']}"
        )
        return analytics_data

    except HTTPException as http_ex:
        print(f"[get_event_analytics] HTTPException: {http_ex.detail}")
        raise http_ex
    except Exception as e:
        print(f"[get_event_analytics] Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred: {str(e)}"
        )


@router.get("/analytics")
async def get_host_recent_events_analytics(
    request: Request,
    user_id: int = Depends(get_current_user),
    platform: Optional[str] = None,
):
    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def get_recent_events_analytics_data(requesting_user_id):
        try:
            # Get the user and verify they exist
            requesting_user = get_object_or_404(CustomUser, id=requesting_user_id)

            # Check if the user is a host
            is_host = requesting_user.groups.filter(name="Host").exists()
            if not is_host:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have permission to access host analytics. Only hosts can view this data.",
                )  # Get the most recent 30 events hosted by this user, sorted by scheduled time
            # (upcoming events first, then most recent past events)
            all_events = Event.objects.filter(host=requesting_user).order_by("-date")[
                :30
            ]

            if not all_events.exists():
                return {
                    "summary": {
                        "total_events": 0,
                        "total_views": 0,
                        "total_tickets_sold": 0,
                        "total_revenue": 0,
                        "average_conversion_rate": 0,
                        "total_shares": 0,
                        "total_favorites": 0,
                        "total_go_with_requests": 0,
                    },
                    "events": [],
                    "trends": {
                        "monthly_events": {},
                        "monthly_tickets": {},
                        "monthly_revenue": {},
                    },
                }

            # Initialize aggregated data
            total_views = 0
            total_tickets_sold = 0
            total_revenue = 0
            total_shares = 0
            total_favorites = 0
            total_go_with_requests = 0
            conversion_rates = []
            events_analytics = []
            monthly_data = {}

            # Process each event
            for event in all_events:
                # Calculate analytics for this event
                event_shares = SharedEvent.objects.filter(event=event).count()
                event_favorites = UserProfile.objects.filter(
                    favorite_events=event
                ).count()
                event_go_with = GoWithRequest.objects.filter(event=event).count()

                # Get tickets for this event
                event_tickets = Ticket.objects.filter(event=event)
                event_ticket_count = event_tickets.count()
                unique_purchasers = (
                    event_tickets.values("user", "guestEmail").distinct().count()
                )

                # Calculate conversion rate for this event
                event_conversion_rate = 0
                if event.views > 0:
                    event_conversion_rate = round(
                        min((unique_purchasers / event.views) * 100, 100), 1
                    )

                # Calculate revenue for this event (assuming ticket price is stored)
                event_revenue = 0
                for ticket in event_tickets:
                    # If ticket has a price field, add it to revenue
                    if hasattr(ticket, "price") and ticket.price:
                        event_revenue += float(ticket.price)

                # Calculate attendance data
                scanned_tickets = event_tickets.filter(status="Scanned").count()
                attendance_rate = (
                    round((scanned_tickets / event_ticket_count * 100), 1)
                    if event_ticket_count > 0
                    else 0
                )

                # Prepare event-specific analytics
                event_analytics = {
                    "eventId": str(event.eventId),
                    "title": event.title,
                    "date": event.date.isoformat() if event.date else None,
                    "created_at": (
                        event.created_at.isoformat() if event.created_at else None
                    ),
                    "views": event.views,
                    "tickets_sold": event_ticket_count,
                    "unique_purchasers": unique_purchasers,
                    "revenue": event_revenue,
                    "conversion_rate": event_conversion_rate,
                    "attendance_rate": attendance_rate,
                    "engagement": {
                        "shares": event_shares,
                        "favorites": event_favorites,
                        "go_with_requests": event_go_with,
                    },
                    "distribution": {
                        "attended": scanned_tickets,
                        "did_not_attend": event_ticket_count - scanned_tickets,
                        "logged_in_users": event_tickets.filter(
                            user__isnull=False
                        ).count(),
                        "guest_users": event_tickets.filter(user__isnull=True).count(),
                    },
                }
                events_analytics.append(event_analytics)

                # Add to totals
                total_views += event.views
                total_tickets_sold += event_ticket_count
                total_revenue += event_revenue
                total_shares += event_shares
                total_favorites += event_favorites
                total_go_with_requests += event_go_with

                if event_conversion_rate > 0:
                    conversion_rates.append(event_conversion_rate)

                # Track monthly data for trends
                if event.date:
                    month_key = event.date.strftime("%Y-%m")
                    if month_key not in monthly_data:
                        monthly_data[month_key] = {
                            "events": 0,
                            "tickets": 0,
                            "revenue": 0,
                        }
                    monthly_data[month_key]["events"] += 1
                    monthly_data[month_key]["tickets"] += event_ticket_count
                    monthly_data[month_key]["revenue"] += event_revenue

            # Calculate averages
            total_events = all_events.count()
            average_conversion_rate = (
                round(sum(conversion_rates) / len(conversion_rates), 1)
                if conversion_rates
                else 0
            )
            average_views_per_event = (
                round(total_views / total_events, 1) if total_events > 0 else 0
            )
            average_tickets_per_event = (
                round(total_tickets_sold / total_events, 1) if total_events > 0 else 0
            )
            average_revenue_per_event = (
                round(total_revenue / total_events, 2) if total_events > 0 else 0
            )

            # Prepare comprehensive analytics response
            analytics_data = {
                "summary": {
                    "total_events": total_events,
                    "total_views": total_views,
                    "total_tickets_sold": total_tickets_sold,
                    "total_unique_purchasers": unique_purchasers,
                    "total_revenue": round(total_revenue, 2),
                    "average_conversion_rate": average_conversion_rate,
                    "average_views_per_event": average_views_per_event,
                    "average_tickets_per_event": average_tickets_per_event,
                    "average_revenue_per_event": average_revenue_per_event,
                    "total_shares": total_shares,
                    "total_favorites": total_favorites,
                    "total_go_with_requests": total_go_with_requests,
                },
                "events": events_analytics,
                "trends": {
                    "monthly_events": {
                        month: data["events"] for month, data in monthly_data.items()
                    },
                    "monthly_tickets": {
                        month: data["tickets"] for month, data in monthly_data.items()
                    },
                    "monthly_revenue": {
                        month: round(data["revenue"], 2)
                        for month, data in monthly_data.items()
                    },
                },
                "host_info": {
                    "host_id": str(requesting_user.id),
                    "username": requesting_user.username,
                    "first_name": requesting_user.first_name,
                    "last_name": requesting_user.last_name,
                    "total_events_hosted": total_events,
                },
            }

            print(
                f"[get_recent_events_analytics_data] Successfully retrieved analytics for {total_events} recent events for host: {requesting_user.username}"
            )
            return analytics_data

        except CustomUser.DoesNotExist:
            print(
                f"[get_recent_events_analytics_data] User not found with ID: {requesting_user_id}"
            )
            raise HTTPException(status_code=404, detail="User not found")
        except Exception as e:
            print(
                f"[get_recent_events_analytics_data] Error retrieving analytics: {str(e)}"
            )
            raise HTTPException(
                status_code=500, detail=f"Error retrieving analytics: {str(e)}"
            )

    try:
        analytics_data = await get_recent_events_analytics_data(user_id)
        print(
            f"[get_host_recent_events_analytics] Returning analytics for {analytics_data['summary']['total_events']} events"
        )
        return analytics_data
    except HTTPException as http_ex:
        print(f"[get_host_recent_events_analytics] HTTPException: {http_ex.detail}")
        raise http_ex
    except Exception as e:
        print(f"[get_host_recent_events_analytics] Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred: {str(e)}"
        )


# ===========================================
# EVENT STATUS AND DISPLAY TOGGLE ENDPOINTS
# ===========================================


@router.post("/event/{eventId}/toggleStatus")
async def toggle_event_status(
    eventId: str,
    request: Request,
    user_id: int = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    Toggle event status between 'live' and 'inactive'
    """
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def toggle_status():
        try:
            event = Event.objects.get(eventId=eventId)

            # Check if user is the host of this event
            if event.host.id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have permission to modify this event. Only the event host can toggle status.",
                )

            # Toggle status
            if event.status == "live":
                event.status = "inactive"
                message = "Event status changed to inactive"
            else:
                event.status = "live"
                message = "Event status changed to live"

            event.save()

            return {
                "message": message,
                "eventId": str(event.eventId),
                "new_status": event.status,
            }

        except Event.DoesNotExist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
            )

    try:
        result = await toggle_status()
        return JSONResponse(content=result, status_code=status.HTTP_200_OK)
    except HTTPException as http_ex:
        return JSONResponse(
            content={"error": str(http_ex.detail)},
            status_code=http_ex.status_code,
        )
    except Exception as e:
        await notify_by_bot(
            f"**[API: toggle_event_status]** \n\n Error toggling event status: eventId={eventId}, error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        return JSONResponse(
            content={"error": f"An unexpected error occurred: {str(e)}"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get("/event/{eventId}/headerPhoto")
async def get_event_header_photo(
    eventId: str,
    request: Request,
    user_id: int = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    Get the header photo URL of an event
    """
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def get_header_photo():
        try:
            event = Event.objects.get(eventId=eventId)

            # Check if user is the host of this event
            if event.host.id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have permission to view this event data. Only the event host can access this information.",
                )

            # Get header photo URL
            header_photo_url = event.header_photo.url if event.header_photo else None

            return {
                "eventId": str(event.eventId),
                "title": event.title,
                "header_photo_url": header_photo_url,
            }

        except Event.DoesNotExist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
            )

    try:
        result = await get_header_photo()
        return JSONResponse(content=result, status_code=status.HTTP_200_OK)
    except HTTPException as http_ex:
        return JSONResponse(
            content={"error": str(http_ex.detail)},
            status_code=http_ex.status_code,
        )
    except Exception as e:
        await notify_by_bot(
            f"**[API: get_event_header_photo]** \n\n Error getting event header photo: eventId={eventId}, error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        return JSONResponse(
            content={"error": f"An unexpected error occurred: {str(e)}"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get("/event/{eventId}/basic")
async def get_event_basic_info(
    eventId: str,
    request: Request,
    user_id: int = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    Get basic event information including title, type, date, times, description, location, images, and crew info
    """
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def get_basic_event_info():
        try:
            event = Event.objects.get(eventId=eventId)

            # Check if user is the host of this event
            if event.host.id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have permission to view this event data. Only the event host can access this information.",
                )

            # Get crew information
            crew_info = None
            if event.crew_discount:
                crew_info = {
                    "crew_discount_enabled": event.crew_discount,
                    "minimum_crew_size": event.minimum_crew_size,
                    "crew_discount_percentage": event.crew_discount_percentage,
                }

            # Process image URLs
            images = {
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
            }

            # Create location data
            location = {
                "building_name": event.building_name,
                "street": event.street,
                "apt_suite_unit": event.apt_suite_unit,
                "city": event.city,
                "state": event.state,
                "zip_code": event.zip_code,
                "country": event.country,
                "hide_address": event.hide_address,
            }

            return {
                "eventId": str(event.eventId),
                "title": event.title,
                "event_type": event.event_type,
                "date": event.date.isoformat() if event.date else None,
                "start_time": (
                    event.start_time.isoformat() if event.start_time else None
                ),
                "end_time": event.end_time.isoformat() if event.end_time else None,
                "description": event.description,
                "location": location,
                "images": images,
                "crew_info": crew_info,
            }

        except Event.DoesNotExist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
            )

    try:
        result = await get_basic_event_info()
        return JSONResponse(content=result, status_code=status.HTTP_200_OK)
    except HTTPException as http_ex:
        return JSONResponse(
            content={"error": str(http_ex.detail)},
            status_code=http_ex.status_code,
        )
    except Exception as e:
        await notify_by_bot(
            f"**[API: get_event_basic_info]** \n\n Error getting event basic info: eventId={eventId}, error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        return JSONResponse(
            content={"error": f"An unexpected error occurred: {str(e)}"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.post("/event/{eventId}/toggleShowGuestList")
async def toggle_show_guest_list(
    eventId: str,
    request: Request,
    user_id: int = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    Toggle show_guest_list boolean field
    """
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def toggle_guest_list():
        try:
            event = Event.objects.get(eventId=eventId)

            # Check if user is the host of this event
            if event.host.id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have permission to modify this event. Only the event host can toggle guest list visibility.",
                )

            # Toggle show_guest_list
            event.show_guest_list = not event.show_guest_list
            event.save()

            return {
                "message": f"Guest list visibility {'enabled' if event.show_guest_list else 'disabled'}",
                "eventId": str(event.eventId),
                "show_guest_list": event.show_guest_list,
            }

        except Event.DoesNotExist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
            )

    try:
        result = await toggle_guest_list()
        return JSONResponse(content=result, status_code=status.HTTP_200_OK)
    except HTTPException as http_ex:
        return JSONResponse(
            content={"error": str(http_ex.detail)},
            status_code=http_ex.status_code,
        )
    except Exception as e:
        await notify_by_bot(
            f"**[API: toggle_show_guest_list]** \n\n Error toggling guest list: eventId={eventId}, error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        return JSONResponse(
            content={"error": f"An unexpected error occurred: {str(e)}"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.post("/event/{eventId}/toggleCouponsActivated")
async def toggle_coupons_activated(
    eventId: str,
    request: Request,
    user_id: int = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    Toggle couponsActivated boolean field
    """
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def toggle_coupons():
        try:
            event = Event.objects.get(eventId=eventId)

            # Check if user is the host of this event
            if event.host.id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have permission to modify this event. Only the event host can toggle coupons.",
                )

            # Toggle couponsActivated
            event.couponsActivated = not event.couponsActivated
            event.save()

            return {
                "message": f"Coupons {'activated' if event.couponsActivated else 'deactivated'}",
                "eventId": str(event.eventId),
                "couponsActivated": event.couponsActivated,
            }

        except Event.DoesNotExist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
            )

    try:
        result = await toggle_coupons()
        return JSONResponse(content=result, status_code=status.HTTP_200_OK)
    except HTTPException as http_ex:
        return JSONResponse(
            content={"error": str(http_ex.detail)},
            status_code=http_ex.status_code,
        )
    except Exception as e:
        await notify_by_bot(
            f"**[API: toggle_coupons_activated]** \n\n Error toggling coupons: eventId={eventId}, error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        return JSONResponse(
            content={"error": f"An unexpected error occurred: {str(e)}"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.post("/event/{eventId}/toggleForAllDisplay")
async def toggle_for_all_display(
    eventId: str,
    request: Request,
    user_id: int = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    Toggle forAllDisplay boolean field
    """
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def toggle_all_display():
        try:
            event = Event.objects.get(eventId=eventId)

            # Check if user is the host of this event
            if event.host.id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have permission to modify this event. Only the event host can toggle display settings.",
                )

            # Toggle forAllDisplay
            event.forAllDisplay = not event.forAllDisplay
            event.save()

            return {
                "message": f"Event {'shown' if event.forAllDisplay else 'hidden'} from all users",
                "eventId": str(event.eventId),
                "forAllDisplay": event.forAllDisplay,
            }

        except Event.DoesNotExist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
            )

    try:
        result = await toggle_all_display()
        return JSONResponse(content=result, status_code=status.HTTP_200_OK)
    except HTTPException as http_ex:
        return JSONResponse(
            content={"error": str(http_ex.detail)},
            status_code=http_ex.status_code,
        )
    except Exception as e:
        await notify_by_bot(
            f"**[API: toggle_for_all_display]** \n\n Error toggling for all display: eventId={eventId}, error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        return JSONResponse(
            content={"error": f"An unexpected error occurred: {str(e)}"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.post("/event/{eventId}/toggleForCollegesDisplay")
async def toggle_for_colleges_display(
    eventId: str,
    request: Request,
    user_id: int = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    Toggle forCollegesDisplay boolean field
    """
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def toggle_colleges_display():
        try:
            event = Event.objects.get(eventId=eventId)

            # Check if user is the host of this event
            if event.host.id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have permission to modify this event. Only the event host can toggle display settings.",
                )

            # Toggle forCollegesDisplay
            event.forCollegesDisplay = not event.forCollegesDisplay
            event.save()

            return {
                "message": f"Event {'shown' if event.forCollegesDisplay else 'hidden'} from college users",
                "eventId": str(event.eventId),
                "forCollegesDisplay": event.forCollegesDisplay,
            }

        except Event.DoesNotExist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
            )

    try:
        result = await toggle_colleges_display()
        return JSONResponse(content=result, status_code=status.HTTP_200_OK)
    except HTTPException as http_ex:
        return JSONResponse(
            content={"error": str(http_ex.detail)},
            status_code=http_ex.status_code,
        )
    except Exception as e:
        await notify_by_bot(
            f"**[API: toggle_for_colleges_display]** \n\n Error toggling for colleges display: eventId={eventId}, error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        return JSONResponse(
            content={"error": f"An unexpected error occurred: {str(e)}"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.patch("/event/{eventId}/editTitle")
async def edit_event_title(
    eventId: str,
    request: Request,
    user_id: int = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    Edit the title of an event
    """
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:
        form_data = await request.form()
        new_title = form_data.get("title")

        if not new_title:
            return JSONResponse(
                content={"error": "Title is required"},
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        @database_sync_to_async
        def update_title():
            try:
                event = Event.objects.get(eventId=eventId)

                # Check if user is the host of this event
                if event.host.id != user_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="You don't have permission to modify this event. Only the event host can edit the title.",
                    )

                event.title = new_title
                event.save()

                return {
                    "message": "Event title updated successfully",
                    "eventId": str(event.eventId),
                    "title": event.title,
                }

            except Event.DoesNotExist:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
                )

        result = await update_title()
        return JSONResponse(content=result, status_code=status.HTTP_200_OK)
    except HTTPException as http_ex:
        return JSONResponse(
            content={"error": str(http_ex.detail)},
            status_code=http_ex.status_code,
        )
    except Exception as e:
        await notify_by_bot(
            f"**[API: edit_event_title]** \n\n Error editing event title: eventId={eventId}, error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        return JSONResponse(
            content={"error": f"An unexpected error occurred: {str(e)}"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.patch("/event/{eventId}/editDescription")
async def edit_event_description(
    eventId: str,
    request: Request,
    user_id: int = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    Edit the description of an event
    """
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:
        form_data = await request.form()
        new_description = form_data.get("description")

        if not new_description:
            return JSONResponse(
                content={"error": "Description is required"},
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        @database_sync_to_async
        def update_description():
            try:
                event = Event.objects.get(eventId=eventId)

                # Check if user is the host of this event
                if event.host.id != user_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="You don't have permission to modify this event. Only the event host can edit the description.",
                    )

                event.description = new_description
                event.save()

                return {
                    "message": "Event description updated successfully",
                    "eventId": str(event.eventId),
                    "description": event.description,
                }

            except Event.DoesNotExist:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
                )

        result = await update_description()
        return JSONResponse(content=result, status_code=status.HTTP_200_OK)
    except HTTPException as http_ex:
        return JSONResponse(
            content={"error": str(http_ex.detail)},
            status_code=http_ex.status_code,
        )
    except Exception as e:
        await notify_by_bot(
            f"**[API: edit_event_description]** \n\n Error editing event description: eventId={eventId}, error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        return JSONResponse(
            content={"error": f"An unexpected error occurred: {str(e)}"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.patch("/event/{eventId}/editDate")
async def edit_event_date(
    eventId: str,
    request: Request,
    user_id: int = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    Edit the date of an event
    """
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:
        form_data = await request.form()
        new_date_str = form_data.get("date")

        if not new_date_str:
            return JSONResponse(
                content={"error": "Date is required"},
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        @database_sync_to_async
        def update_date():
            try:
                event = Event.objects.get(eventId=eventId)

                # Check if user is the host of this event
                if event.host.id != user_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="You don't have permission to modify this event. Only the event host can edit the date.",
                    )

                # Parse the date string
                try:
                    from datetime import datetime

                    new_date = datetime.strptime(new_date_str, "%Y-%m-%d").date()
                except ValueError:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid date format. Use YYYY-MM-DD format.",
                    )

                event.date = new_date
                event.save()

                return {
                    "message": "Event date updated successfully",
                    "eventId": str(event.eventId),
                    "date": event.date.isoformat(),
                }

            except Event.DoesNotExist:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
                )

        result = await update_date()
        return JSONResponse(content=result, status_code=status.HTTP_200_OK)
    except HTTPException as http_ex:
        return JSONResponse(
            content={"error": str(http_ex.detail)},
            status_code=http_ex.status_code,
        )
    except Exception as e:
        await notify_by_bot(
            f"**[API: edit_event_date]** \n\n Error editing event date: eventId={eventId}, error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        return JSONResponse(
            content={"error": f"An unexpected error occurred: {str(e)}"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.patch("/event/{eventId}/editStartTime")
async def edit_event_start_time(
    eventId: str,
    request: Request,
    user_id: int = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    Edit the start time of an event
    """
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:
        form_data = await request.form()
        new_start_time_str = form_data.get("start_time")

        if not new_start_time_str:
            return JSONResponse(
                content={"error": "Start time is required"},
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        @database_sync_to_async
        def update_start_time():
            try:
                event = Event.objects.get(eventId=eventId)

                # Check if user is the host of this event
                if event.host.id != user_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="You don't have permission to modify this event. Only the event host can edit the start time.",
                    )

                # Parse the time string
                try:
                    from datetime import datetime

                    new_start_time = datetime.strptime(
                        new_start_time_str, "%H:%M"
                    ).time()
                except ValueError:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid time format. Use HH:MM format.",
                    )

                event.start_time = new_start_time
                event.save()

                return {
                    "message": "Event start time updated successfully",
                    "eventId": str(event.eventId),
                    "start_time": event.start_time.isoformat(),
                }

            except Event.DoesNotExist:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
                )

        result = await update_start_time()
        return JSONResponse(content=result, status_code=status.HTTP_200_OK)
    except HTTPException as http_ex:
        return JSONResponse(
            content={"error": str(http_ex.detail)},
            status_code=http_ex.status_code,
        )
    except Exception as e:
        await notify_by_bot(
            f"**[API: edit_event_start_time]** \n\n Error editing event start time: eventId={eventId}, error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        return JSONResponse(
            content={"error": f"An unexpected error occurred: {str(e)}"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.patch("/event/{eventId}/editEndTime")
async def edit_event_end_time(
    eventId: str,
    request: Request,
    user_id: int = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    Edit the end time of an event
    """
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:
        form_data = await request.form()
        new_end_time_str = form_data.get("end_time")

        if not new_end_time_str:
            return JSONResponse(
                content={"error": "End time is required"},
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        @database_sync_to_async
        def update_end_time():
            try:
                event = Event.objects.get(eventId=eventId)

                # Check if user is the host of this event
                if event.host.id != user_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="You don't have permission to modify this event. Only the event host can edit the end time.",
                    )

                # Parse the time string
                try:
                    from datetime import datetime

                    new_end_time = datetime.strptime(new_end_time_str, "%H:%M").time()
                except ValueError:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid time format. Use HH:MM format.",
                    )

                event.end_time = new_end_time
                event.save()

                return {
                    "message": "Event end time updated successfully",
                    "eventId": str(event.eventId),
                    "end_time": event.end_time.isoformat(),
                }

            except Event.DoesNotExist:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
                )

        result = await update_end_time()
        return JSONResponse(content=result, status_code=status.HTTP_200_OK)
    except HTTPException as http_ex:
        return JSONResponse(
            content={"error": str(http_ex.detail)},
            status_code=http_ex.status_code,
        )
    except Exception as e:
        await notify_by_bot(
            f"**[API: edit_event_end_time]** \n\n Error editing event end time: eventId={eventId}, error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        return JSONResponse(
            content={"error": f"An unexpected error occurred: {str(e)}"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.patch("/event/{eventId}/editEventType")
async def edit_event_type(
    eventId: str,
    request: Request,
    user_id: int = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    Edit the event type of an event
    """
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:
        form_data = await request.form()
        new_event_type = form_data.get("event_type")

        if not new_event_type:
            return JSONResponse(
                content={"error": "Event type is required"},
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        @database_sync_to_async
        def update_event_type():
            try:
                event = Event.objects.get(eventId=eventId)

                # Check if user is the host of this event
                if event.host.id != user_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="You don't have permission to modify this event. Only the event host can edit the event type.",
                    )

                event.event_type = new_event_type
                event.save()

                return {
                    "message": "Event type updated successfully",
                    "eventId": str(event.eventId),
                    "event_type": event.event_type,
                }

            except Event.DoesNotExist:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
                )

        result = await update_event_type()
        return JSONResponse(content=result, status_code=status.HTTP_200_OK)
    except HTTPException as http_ex:
        return JSONResponse(
            content={"error": str(http_ex.detail)},
            status_code=http_ex.status_code,
        )
    except Exception as e:
        await notify_by_bot(
            f"**[API: edit_event_type]** \n\n Error editing event type: eventId={eventId}, error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        return JSONResponse(
            content={"error": f"An unexpected error occurred: {str(e)}"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.patch("/event/{eventId}/editLocation")
async def edit_event_location(
    eventId: str,
    request: Request,
    user_id: int = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    Edit the location fields of an event
    """
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:
        form_data = await request.form()

        # Get location fields from form data
        building_name = form_data.get("building_name")
        street = form_data.get("street")
        apt_suite_unit = form_data.get("apt_suite_unit")
        city = form_data.get("city")
        state = form_data.get("state")
        zip_code = form_data.get("zip_code")
        country = form_data.get("country")
        hide_address = form_data.get("hide_address", "false").lower() == "true"

        @database_sync_to_async
        def update_location():
            try:
                event = Event.objects.get(eventId=eventId)

                # Check if user is the host of this event
                if event.host.id != user_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="You don't have permission to modify this event. Only the event host can edit the location.",
                    )

                # Update location fields if provided
                if building_name is not None:
                    event.building_name = building_name
                if street is not None:
                    event.street = street
                if apt_suite_unit is not None:
                    event.apt_suite_unit = apt_suite_unit
                if city is not None:
                    event.city = city
                if state is not None:
                    event.state = state
                if zip_code is not None:
                    event.zip_code = zip_code
                if country is not None:
                    event.country = country

                event.hide_address = hide_address
                event.save()

                return {
                    "message": "Event location updated successfully",
                    "eventId": str(event.eventId),
                    "location": {
                        "building_name": event.building_name,
                        "street": event.street,
                        "apt_suite_unit": event.apt_suite_unit,
                        "city": event.city,
                        "state": event.state,
                        "zip_code": event.zip_code,
                        "country": event.country,
                        "hide_address": event.hide_address,
                    },
                }

            except Event.DoesNotExist:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
                )

        result = await update_location()
        return JSONResponse(content=result, status_code=status.HTTP_200_OK)
    except HTTPException as http_ex:
        return JSONResponse(
            content={"error": str(http_ex.detail)},
            status_code=http_ex.status_code,
        )
    except Exception as e:
        await notify_by_bot(
            f"**[API: edit_event_location]** \n\n Error editing event location: eventId={eventId}, error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        return JSONResponse(
            content={"error": f"An unexpected error occurred: {str(e)}"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.patch("/event/{eventId}/editCrewInfo")
async def edit_event_crew_info(
    eventId: str,
    request: Request,
    user_id: int = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    Edit the crew discount information of an event
    """
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:
        form_data = await request.form()

        crew_discount = form_data.get("crew_discount", "false").lower() == "true"
        minimum_crew_size = form_data.get("minimum_crew_size")
        crew_discount_percentage = form_data.get("crew_discount_percentage")

        @database_sync_to_async
        def update_crew_info():
            try:
                event = Event.objects.get(eventId=eventId)

                # Check if user is the host of this event
                if event.host.id != user_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="You don't have permission to modify this event. Only the event host can edit crew information.",
                    )

                event.crew_discount = crew_discount

                if minimum_crew_size is not None:
                    try:
                        event.minimum_crew_size = int(minimum_crew_size)
                    except ValueError:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Minimum crew size must be a valid integer.",
                        )

                if crew_discount_percentage is not None:
                    try:
                        event.crew_discount_percentage = int(crew_discount_percentage)
                    except ValueError:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Crew discount percentage must be a valid integer.",
                        )

                event.save()

                return {
                    "message": "Event crew information updated successfully",
                    "eventId": str(event.eventId),
                    "crew_info": {
                        "crew_discount_enabled": event.crew_discount,
                        "minimum_crew_size": event.minimum_crew_size,
                        "crew_discount_percentage": event.crew_discount_percentage,
                    },
                }

            except Event.DoesNotExist:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
                )

        result = await update_crew_info()
        return JSONResponse(content=result, status_code=status.HTTP_200_OK)
    except HTTPException as http_ex:
        return JSONResponse(
            content={"error": str(http_ex.detail)},
            status_code=http_ex.status_code,
        )
    except Exception as e:
        await notify_by_bot(
            f"**[API: edit_event_crew_info]** \n\n Error editing event crew info: eventId={eventId}, error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        return JSONResponse(
            content={"error": f"An unexpected error occurred: {str(e)}"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get("/event-types")
async def get_event_types(
    request: Request,
    platform: Optional[str] = None,
):
    """
    Get all possible event types
    """
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:

        @database_sync_to_async
        def get_event_types():
            """Get all possible event types from the Event model."""
            from eventManagementApp.models import Event

            # Get the event type choices from the Event model
            event_types = Event.EVENT_TYPE_CHOICES

            # Format the response as a list of dictionaries with value and label
            formatted_types = [
                {"value": choice[0], "label": choice[1]} for choice in event_types
            ]

            return {
                "message": "Event types retrieved successfully",
                "event_types": formatted_types,
                "total_count": len(formatted_types),
            }

        result = await get_event_types()
        return JSONResponse(content=result, status_code=status.HTTP_200_OK)

    except Exception as e:
        await notify_by_bot(
            f"**[API: get_event_types]** \n\n Error retrieving event types: error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        return JSONResponse(
            content={"error": f"An unexpected error occurred: {str(e)}"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.patch("/event/{eventId}/editHeaderPhoto")
async def edit_event_header_photo(
    eventId: str,
    request: Request,
    user_id: int = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    Edit the header photo of an event
    """
    print(f"[DEBUG - edit_event_header_photo] Function called with eventId: {eventId}, user_id: {user_id}, platform: {platform}")
    
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]
    print(f"[DEBUG - edit_event_header_photo] Device info extracted: {device_info}")

    try:
        print(f"[DEBUG - edit_event_header_photo] Starting to process form data...")
        form_data = await request.form()
        print(f"[DEBUG - edit_event_header_photo] Form data received with keys: {list(form_data.keys())}")
        
        header_photo = form_data.get("header_photo")
        print(f"[DEBUG - edit_event_header_photo] Header photo field: {header_photo}")
        print(f"[DEBUG - edit_event_header_photo] Header photo type: {type(header_photo)}")
        
        if header_photo:
            print(f"[DEBUG - edit_event_header_photo] Header photo filename: {getattr(header_photo, 'filename', 'N/A')}")
            print(f"[DEBUG - edit_event_header_photo] Header photo content_type: {getattr(header_photo, 'content_type', 'N/A')}")
            print(f"[DEBUG - edit_event_header_photo] Header photo size: {getattr(header_photo, 'size', 'N/A')}")

        if not header_photo:
            print(f"[DEBUG - edit_event_header_photo] No header photo provided in form data")
            return JSONResponse(
                content={"error": "Header photo is required"},
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        print(f"[DEBUG - edit_event_header_photo] Converting Starlette UploadFile to Django SimpleUploadedFile...")
        # Convert Starlette UploadFile to Django SimpleUploadedFile before database operation
        header_photo_file = await starlette_to_django(header_photo)
        print(f"[DEBUG - edit_event_header_photo] File conversion completed successfully")
        print(f"[DEBUG - edit_event_header_photo] Django file name: {header_photo_file.name}")
        print(f"[DEBUG - edit_event_header_photo] Django file size: {header_photo_file.size}")
        print(f"[DEBUG - edit_event_header_photo] Django file content_type: {header_photo_file.content_type}")

        @database_sync_to_async
        def update_header_photo():
            print(f"[DEBUG - edit_event_header_photo - update_header_photo] Starting database operation...")
            try:
                print(f"[DEBUG - edit_event_header_photo - update_header_photo] Fetching event with eventId: {eventId}")
                event = Event.objects.get(eventId=eventId)
                print(f"[DEBUG - edit_event_header_photo - update_header_photo] Event found: {event.title}")
                print(f"[DEBUG - edit_event_header_photo - update_header_photo] Event host: {event.host.id}")
                print(f"[DEBUG - edit_event_header_photo - update_header_photo] Requesting user: {user_id}")

                # Check if user is the host of this event
                if event.host.id != user_id:
                    print(f"[DEBUG - edit_event_header_photo - update_header_photo] Permission denied - user {user_id} is not the host {event.host.id}")
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="You don't have permission to modify this event. Only the event host can edit the header photo.",
                    )

                print(f"[DEBUG - edit_event_header_photo - update_header_photo] Permission check passed")
                print(f"[DEBUG - edit_event_header_photo - update_header_photo] Current header photo: {event.header_photo}")
                
                # Update the header photo
                print(f"[DEBUG - edit_event_header_photo - update_header_photo] Updating header photo...")
                event.header_photo = header_photo_file
                print(f"[DEBUG - edit_event_header_photo - update_header_photo] Header photo field updated, saving event...")
                event.save()
                print(f"[DEBUG - edit_event_header_photo - update_header_photo] Event saved successfully")
                
                print(f"[DEBUG - edit_event_header_photo - update_header_photo] New header photo: {event.header_photo}")
                header_photo_url = event.header_photo.url if event.header_photo else None
                print(f"[DEBUG - edit_event_header_photo - update_header_photo] New header photo URL: {header_photo_url}")

                response_data = {
                    "message": "Event header photo updated successfully",
                    "eventId": str(event.eventId),
                    "header_photo_url": header_photo_url,
                }
                print(f"[DEBUG - edit_event_header_photo - update_header_photo] Response data prepared: {response_data}")
                return response_data

            except Event.DoesNotExist:
                print(f"[DEBUG - edit_event_header_photo - update_header_photo] Event not found with eventId: {eventId}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
                )
            except Exception as e:
                print(f"[DEBUG - edit_event_header_photo - update_header_photo] Unexpected error in database operation: {str(e)}")
                print(f"[DEBUG - edit_event_header_photo - update_header_photo] Error type: {type(e)}")
                raise

        print(f"[DEBUG - edit_event_header_photo] Calling database update function...")
        result = await update_header_photo()
        print(f"[DEBUG - edit_event_header_photo] Database update completed successfully")
        print(f"[DEBUG - edit_event_header_photo] Final result: {result}")
        return JSONResponse(content=result, status_code=status.HTTP_200_OK)
        
    except HTTPException as http_ex:
        print(f"[DEBUG - edit_event_header_photo] HTTPException caught: {http_ex.detail}")
        print(f"[DEBUG - edit_event_header_photo] HTTPException status code: {http_ex.status_code}")
        return JSONResponse(
            content={"error": str(http_ex.detail)},
            status_code=http_ex.status_code,
        )
    except Exception as e:
        print(f"[DEBUG - edit_event_header_photo] Unexpected exception caught: {str(e)}")
        print(f"[DEBUG - edit_event_header_photo] Exception type: {type(e)}")
        import traceback
        traceback_str = traceback.format_exc()
        print(f"[DEBUG - edit_event_header_photo] Full traceback: {traceback_str}")
        
        await notify_by_bot(
            f"**[API: edit_event_header_photo]** \n\n Error editing event header photo: eventId={eventId}, error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        return JSONResponse(
            content={"error": f"An unexpected error occurred: {str(e)}"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.patch("/event/{eventId}/addBodyPhotos")
async def add_event_body_photos(
    eventId: str,
    request: Request,
    user_id: int = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    Add body photos to an event
    """
    print(f"[DEBUG - add_event_body_photos] Function called with eventId: {eventId}, user_id: {user_id}, platform: {platform}")
    
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]
    print(f"[DEBUG - add_event_body_photos] Device info extracted: {device_info}")

    try:
        print(f"[DEBUG - add_event_body_photos] Starting to process form data...")
        form_data = await request.form()
        print(f"[DEBUG - add_event_body_photos] Form data received with keys: {list(form_data.keys())}")

        # Get body photos from form data
        body_photo_one = form_data.get("body_photo_one")
        body_photo_two = form_data.get("body_photo_two")
        body_photo_three = form_data.get("body_photo_three")
        body_photo_four = form_data.get("body_photo_four")
        body_photo_five = form_data.get("body_photo_five")

        print(f"[DEBUG - add_event_body_photos] Body photo one: {body_photo_one} (type: {type(body_photo_one)})")
        print(f"[DEBUG - add_event_body_photos] Body photo two: {body_photo_two} (type: {type(body_photo_two)})")
        print(f"[DEBUG - add_event_body_photos] Body photo three: {body_photo_three} (type: {type(body_photo_three)})")
        print(f"[DEBUG - add_event_body_photos] Body photo four: {body_photo_four} (type: {type(body_photo_four)})")
        print(f"[DEBUG - add_event_body_photos] Body photo five: {body_photo_five} (type: {type(body_photo_five)})")

        # Log details of each provided photo
        photos_info = {
            "body_photo_one": body_photo_one,
            "body_photo_two": body_photo_two,
            "body_photo_three": body_photo_three,
            "body_photo_four": body_photo_four,
            "body_photo_five": body_photo_five,
        }
        
        for photo_name, photo in photos_info.items():
            if photo:
                print(f"[DEBUG - add_event_body_photos] {photo_name} filename: {getattr(photo, 'filename', 'N/A')}")
                print(f"[DEBUG - add_event_body_photos] {photo_name} content_type: {getattr(photo, 'content_type', 'N/A')}")
                print(f"[DEBUG - add_event_body_photos] {photo_name} size: {getattr(photo, 'size', 'N/A')}")

        # Check if at least one photo is provided
        provided_photos = [photo for photo in photos_info.values() if photo]
        print(f"[DEBUG - add_event_body_photos] Number of photos provided: {len(provided_photos)}")
        
        if not any([body_photo_one, body_photo_two, body_photo_three, body_photo_four, body_photo_five]):
            print(f"[DEBUG - add_event_body_photos] No body photos provided in form data")
            return JSONResponse(
                content={"error": "At least one body photo is required"},
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        print(f"[DEBUG - add_event_body_photos] Converting Starlette UploadFiles to Django SimpleUploadedFiles...")
        
        # Convert Starlette UploadFiles to Django SimpleUploadedFiles before database operation
        django_files = {}
        
        if body_photo_one:
            print(f"[DEBUG - add_event_body_photos] Converting body_photo_one...")
            django_files["body_photo_one"] = await starlette_to_django(body_photo_one)
            print(f"[DEBUG - add_event_body_photos] body_photo_one converted successfully")
            
        if body_photo_two:
            print(f"[DEBUG - add_event_body_photos] Converting body_photo_two...")
            django_files["body_photo_two"] = await starlette_to_django(body_photo_two)
            print(f"[DEBUG - add_event_body_photos] body_photo_two converted successfully")
            
        if body_photo_three:
            print(f"[DEBUG - add_event_body_photos] Converting body_photo_three...")
            django_files["body_photo_three"] = await starlette_to_django(body_photo_three)
            print(f"[DEBUG - add_event_body_photos] body_photo_three converted successfully")
            
        if body_photo_four:
            print(f"[DEBUG - add_event_body_photos] Converting body_photo_four...")
            django_files["body_photo_four"] = await starlette_to_django(body_photo_four)
            print(f"[DEBUG - add_event_body_photos] body_photo_four converted successfully")
            
        if body_photo_five:
            print(f"[DEBUG - add_event_body_photos] Converting body_photo_five...")
            django_files["body_photo_five"] = await starlette_to_django(body_photo_five)
            print(f"[DEBUG - add_event_body_photos] body_photo_five converted successfully")

        print(f"[DEBUG - add_event_body_photos] File conversions completed. Django files keys: {list(django_files.keys())}")
        
        # Log details of converted Django files
        for file_key, django_file in django_files.items():
            print(f"[DEBUG - add_event_body_photos] {file_key} Django file name: {django_file.name}")
            print(f"[DEBUG - add_event_body_photos] {file_key} Django file size: {django_file.size}")
            print(f"[DEBUG - add_event_body_photos] {file_key} Django file content_type: {django_file.content_type}")

        @database_sync_to_async
        def update_body_photos():
            print(f"[DEBUG - add_event_body_photos - update_body_photos] Starting database operation...")
            try:
                print(f"[DEBUG - add_event_body_photos - update_body_photos] Fetching event with eventId: {eventId}")
                event = Event.objects.get(eventId=eventId)
                print(f"[DEBUG - add_event_body_photos - update_body_photos] Event found: {event.title}")
                print(f"[DEBUG - add_event_body_photos - update_body_photos] Event host: {event.host.id}")
                print(f"[DEBUG - add_event_body_photos - update_body_photos] Requesting user: {user_id}")

                # Check if user is the host of this event
                if event.host.id != user_id:
                    print(f"[DEBUG - add_event_body_photos - update_body_photos] Permission denied - user {user_id} is not the host {event.host.id}")
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="You don't have permission to modify this event. Only the event host can add body photos.",
                    )

                print(f"[DEBUG - add_event_body_photos - update_body_photos] Permission check passed")
                print(f"[DEBUG - add_event_body_photos - update_body_photos] Current body photos:")
                print(f"[DEBUG - add_event_body_photos - update_body_photos] - body_photo_one: {event.body_photo_one}")
                print(f"[DEBUG - add_event_body_photos - update_body_photos] - body_photo_two: {event.body_photo_two}")
                print(f"[DEBUG - add_event_body_photos - update_body_photos] - body_photo_three: {event.body_photo_three}")
                print(f"[DEBUG - add_event_body_photos - update_body_photos] - body_photo_four: {event.body_photo_four}")
                print(f"[DEBUG - add_event_body_photos - update_body_photos] - body_photo_five: {event.body_photo_five}")

                updated_photos = {}

                # Update body photos if provided
                if "body_photo_one" in django_files:
                    print(f"[DEBUG - add_event_body_photos - update_body_photos] Updating body_photo_one...")
                    event.body_photo_one = django_files["body_photo_one"]
                    updated_photos["body_photo_one"] = True
                    print(f"[DEBUG - add_event_body_photos - update_body_photos] body_photo_one updated")

                if "body_photo_two" in django_files:
                    print(f"[DEBUG - add_event_body_photos - update_body_photos] Updating body_photo_two...")
                    event.body_photo_two = django_files["body_photo_two"]
                    updated_photos["body_photo_two"] = True
                    print(f"[DEBUG - add_event_body_photos - update_body_photos] body_photo_two updated")

                if "body_photo_three" in django_files:
                    print(f"[DEBUG - add_event_body_photos - update_body_photos] Updating body_photo_three...")
                    event.body_photo_three = django_files["body_photo_three"]
                    updated_photos["body_photo_three"] = True
                    print(f"[DEBUG - add_event_body_photos - update_body_photos] body_photo_three updated")

                if "body_photo_four" in django_files:
                    print(f"[DEBUG - add_event_body_photos - update_body_photos] Updating body_photo_four...")
                    event.body_photo_four = django_files["body_photo_four"]
                    updated_photos["body_photo_four"] = True
                    print(f"[DEBUG - add_event_body_photos - update_body_photos] body_photo_four updated")

                if "body_photo_five" in django_files:
                    print(f"[DEBUG - add_event_body_photos - update_body_photos] Updating body_photo_five...")
                    event.body_photo_five = django_files["body_photo_five"]
                    updated_photos["body_photo_five"] = True
                    print(f"[DEBUG - add_event_body_photos - update_body_photos] body_photo_five updated")

                print(f"[DEBUG - add_event_body_photos - update_body_photos] Updated photos: {updated_photos}")
                print(f"[DEBUG - add_event_body_photos - update_body_photos] Saving event...")
                event.save()
                print(f"[DEBUG - add_event_body_photos - update_body_photos] Event saved successfully")

                print(f"[DEBUG - add_event_body_photos - update_body_photos] Getting photo URLs...")
                # Get URLs for updated photos
                photo_urls = {}
                if event.body_photo_one:
                    photo_urls["body_photo_one_url"] = event.body_photo_one.url
                    print(f"[DEBUG - add_event_body_photos - update_body_photos] body_photo_one_url: {photo_urls['body_photo_one_url']}")
                if event.body_photo_two:
                    photo_urls["body_photo_two_url"] = event.body_photo_two.url
                    print(f"[DEBUG - add_event_body_photos - update_body_photos] body_photo_two_url: {photo_urls['body_photo_two_url']}")
                if event.body_photo_three:
                    photo_urls["body_photo_three_url"] = event.body_photo_three.url
                    print(f"[DEBUG - add_event_body_photos - update_body_photos] body_photo_three_url: {photo_urls['body_photo_three_url']}")
                if event.body_photo_four:
                    photo_urls["body_photo_four_url"] = event.body_photo_four.url
                    print(f"[DEBUG - add_event_body_photos - update_body_photos] body_photo_four_url: {photo_urls['body_photo_four_url']}")
                if event.body_photo_five:
                    photo_urls["body_photo_five_url"] = event.body_photo_five.url
                    print(f"[DEBUG - add_event_body_photos - update_body_photos] body_photo_five_url: {photo_urls['body_photo_five_url']}")

                response_data = {
                    "message": "Event body photos updated successfully",
                    "eventId": str(event.eventId),
                    "updated_photos": updated_photos,
                    "photo_urls": photo_urls,
                }
                print(f"[DEBUG - add_event_body_photos - update_body_photos] Response data prepared: {response_data}")
                return response_data

            except Event.DoesNotExist:
                print(f"[DEBUG - add_event_body_photos - update_body_photos] Event not found with eventId: {eventId}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
                )
            except Exception as e:
                print(f"[DEBUG - add_event_body_photos - update_body_photos] Unexpected error in database operation: {str(e)}")
                print(f"[DEBUG - add_event_body_photos - update_body_photos] Error type: {type(e)}")
                raise

        print(f"[DEBUG - add_event_body_photos] Calling database update function...")
        result = await update_body_photos()
        print(f"[DEBUG - add_event_body_photos] Database update completed successfully")
        print(f"[DEBUG - add_event_body_photos] Final result: {result}")
        return JSONResponse(content=result, status_code=status.HTTP_200_OK)
        
    except HTTPException as http_ex:
        print(f"[DEBUG - add_event_body_photos] HTTPException caught: {http_ex.detail}")
        print(f"[DEBUG - add_event_body_photos] HTTPException status code: {http_ex.status_code}")
        return JSONResponse(
            content={"error": str(http_ex.detail)},
            status_code=http_ex.status_code,
        )
    except Exception as e:
        print(f"[DEBUG - add_event_body_photos] Unexpected exception caught: {str(e)}")
        print(f"[DEBUG - add_event_body_photos] Exception type: {type(e)}")
        import traceback
        traceback_str = traceback.format_exc()
        print(f"[DEBUG - add_event_body_photos] Full traceback: {traceback_str}")
        
        await notify_by_bot(
            f"**[API: add_event_body_photos]** \n\n Error adding event body photos: eventId={eventId}, error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        return JSONResponse(
            content={"error": f"An unexpected error occurred: {str(e)}"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

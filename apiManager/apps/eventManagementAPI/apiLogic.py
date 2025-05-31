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
from asgiref.sync import sync_to_async
import traceback

from apiManager.dependencies import get_current_user
from apiManager.apps.authenticationAPI.utilities import get_form_fields
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
    content = await u.read()           # get bytes from Starlette file
    return SimpleUploadedFile(         # Django-friendly object
        name=u.filename,
        content=content,
        content_type=u.content_type or 'application/octet-stream'
    )

router = APIRouter()

@router.api_route("/event/{eventId}/editEvent", methods=["POST", "PATCH"])
async def edit_event_endpoint(
    request: Request, eventId: str, user_id=Depends(get_current_user)
):
    print(f"[DEBUG - edit_event_endpoint] Function called with eventId: {eventId}")
    """
    Edit an event, supporting both full updates (POST) and partial updates (PATCH).
    """
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
        @sync_to_async
        def process_edit_event():
            # Retrieve the event or raise a 404
            event = get_object_or_404(Event, eventId=eventId)
            print(f"[DEBUG - process_edit_event] Event fields: {event.__dict__}")
            print(f"[DEBUG - process_edit_event] Incoming data: {data}")
            print(f"[DEBUG - process_edit_event] Incoming files: {files}")

            # Get the current user's profile
            user = CustomUser.objects.get(id=user_id)
            user_profile = UserProfile.objects.get(user=user)

            # Get the host profile for the event host
            host_profile = HostProfile.objects.get(user=event.host)

            # Determine whether the user is associated with a college
            is_in_college = user_profile.college is not None

            # Merge data and files for the serializer
            combined_data = {**data}
            combined_data.update(files)

            # Use DRF ModelSerializer for proper partial update support
            serializer = EditEventModelSerializer(
                instance=event,
                data=combined_data,
                partial=partial
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
        print(f"[DEBUG - edit_event_endpoint] Success response: {result.get('message', 'No message')}")
        return JSONResponse(content=result, status_code=status.HTTP_200_OK)
    except ValueError as ve:
        # Return validation errors in a structured format
        error_content = {"message": "Failed to update event."}
        
        # Check if this is our structured validation error
        if str(ve).startswith('{"validation_errors"'):
            try:
                import json
                error_dict = json.loads(str(ve).replace("'", "\""))
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
        return JSONResponse(
            content={"error": f"An unexpected error occurred: {str(e)}"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get("/getEvents")
async def get_events(user_id: int = Depends(get_current_user)):
    print(f"[DEBUG - get_events] Function called with user_id: {user_id}")
    """
    API endpoint for getting events
    """
    try:

        @sync_to_async
        def validate_user(user_id):
            try:
                user = CustomUser.objects.get(id=user_id)
                # Check if user is None
                if not user or user is None:
                    return None
                return user
            except CustomUser.DoesNotExist:
                return None

        @sync_to_async
        def get_events(user_id):
            try:
                events_list = []
                user_obj = CustomUser.objects.get(id=user_id)
                # First, get the host profile for this user
                try:
                    # Then get the events where host is this host profile
                    host_events = Event.objects.filter(host=user_obj)
                    if not host_events:
                        # Return an empty list if no events found instead of JSONResponse
                        return []
                    for event in host_events:
                        header_photo_url = (
                            event.header_photo.url if event.header_photo else None
                        )

                        event_data = {
                            "eventId": str(event.eventId),
                            "title": event.title,
                            "description": event.description,
                            "date": event.date,
                            "city": event.city,
                            "state": event.state,
                            "header_photo": header_photo_url,
                            "ticketing": event.ticketing,
                        }
                        events_list.append(event_data)
                except HostProfile.DoesNotExist:
                    # User doesn't have a host profile
                    return []
                return events_list
            except Exception as e:
                print(f"Error in get_events: {str(e)}")
                return []

        # Validate user asynchronously
        user = await validate_user(user_id)
        print(f"[DEBUG - get_events] User validated: {user is not None}")
        if not user:
            return JSONResponse(
                content={"error": "Authentication required"},
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

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
async def get_event_details(eventId: str, user_id: int = Depends(get_current_user)):
    print(f"[DEBUG - get_event_details] Function called with eventId: {eventId}, user_id: {user_id}")
    """
    API endpoint for getting event details
    """
    try:

        @sync_to_async
        def get_event(eventId):
            event = Event.objects.filter(eventId=eventId).first()
            if not event:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Event not found."
                )
            return event  # Get the event details asynchronously

        event = await get_event(eventId)
        print(f"[DEBUG - get_event_details] Event found: {event.title if event else 'None'}")

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

        print(f"[DEBUG - get_event_details] Returning event data for: {event_data.title}")
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

        # Handle all other exceptions
        return JSONResponse(
            content={"error": f"An unexpected error occurred: {str(e)}"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.post("/event/{eventId}/deleteEvent")
async def delete_event(eventId: str, user_id: int = Depends(get_current_user)):
    print(f"[DEBUG - delete_event] Function called with eventId: {eventId}, user_id: {user_id}")
    """
    API endpoint for deleting an event
    """
    try:

        @sync_to_async
        def delete_event(eventId):
            print(f"[DEBUG - delete_event] Attempting to delete event with ID: {eventId}")
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
    print(f"[DEBUG - event_creation_fields] Returning form fields: {list(fields_info.keys())}")
    return JSONResponse(content=fields_info, status_code=status.HTTP_200_OK)


@router.post("/event/free/create")
async def create_free_event(request: Request, user_id: int = Depends(get_current_user)):
    print(f"[DEBUG - create_free_event] Function called with user_id: {user_id}")
    """
    API endpoint for creating a free event
    """
    try:
        # Get form data (includes both text fields and files)
        form_data = await request.form()

        # Separate normal data and file data from the form
        data = {}
        files = {}
        print(f"[DEBUG - create_free_event] Processing form data")
        for key, value in form_data.multi_items():
            if isinstance(value, UploadFile):
                files[key] = await starlette_to_django(value)   # 👈 wrap here
                print(f"[DEBUG - create_free_event] File uploaded: {key}")
            else:
                data[key] = value
                print(f"[DEBUG - create_free_event] Text field: {key} = {value}")
        # Wrap Django ORM calls and form processing in a synchronous function
        @sync_to_async
        def process_create_event():
            # Get the current user's profile.
            user = CustomUser.objects.get(id=user_id)
            user_profile = UserProfile.objects.get(user=user)

            # Determine whether the user is associated with a college
            is_in_college = (
                user_profile.college is not None
            )  # Instantiate the Django form with submitted data, file uploads, instance and partial flag.
            event_form = EventForm(data, files)
            print(f"[DEBUG - create_free_event] Event form: {event_form}")
            
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

                # Create location serializer instance
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

                # Create host serializer instance
                host = HostSerializer(
                    id=str(host_profile.hostProfileId),
                    name=f"{user.first_name} {user.last_name}",
                )

                # Process image URLs
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

                # Create event response serializer instance
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

                # Properly serialize the event_data to make it JSON serializable
                serialized_event_data = event_data.model_dump(mode="json")
                return {"message": "Event created successfully.", "event": serialized_event_data}
            else:
                # Here we raise an error with the form errors so that we can return a 400 response.
                raise ValueError(event_form.errors)

        # Execute the create event function
        result = await process_create_event()
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
        return JSONResponse(
            content={"error": f"An unexpected error occurred: {str(e)}"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.post("/event/paid/create")
async def create_paid_event(request: Request, user_id: int = Depends(get_current_user)):
    print(f"[DEBUG - create_paid_event] Function called with user_id: {user_id}")
    """
    API endpoint for creating a paid event
    """
    try:
        # Get form data (includes both text fields and files)
        form_data = await request.form()

        # Separate normal data and file data from the form
        data = {}
        files = {}
        print(f"[DEBUG - create_paid_event] Processing form data")
        for key, value in form_data.multi_items():
            if isinstance(value, UploadFile):
                files[key] = await starlette_to_django(value)
                print(f"[DEBUG - create_paid_event] File uploaded: {key}")
            else:
                data[key] = value
                print(f"[DEBUG - create_paid_event] Text field: {key} = {value}")

        # Wrap Django ORM calls and form processing in a synchronous function
        @sync_to_async
        def process_create_event():
            try:
                # Get the current user's profile
                user = CustomUser.objects.get(id=user_id)
                user_profile = UserProfile.objects.get(user=user)

                # Verify the host has a Stripe Connect account set up
                if not hasattr(user, 'connectAccountID') or not user.connectAccountID:
                    print(f"[DEBUG - create_paid_event] User {user_id} has no Stripe Connect account set up")
                    return JSONResponse(
                        content={
                            "error": "You need to set up your Stripe account before creating a paid event.",
                            "redirect": "/host/stripe-setup/"
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
                            refresh_url=f'{settings.SITE_URL}/refresh/{user.connectAccountID}',
                            return_url=f"{settings.SITE_URL}/host/portal/",
                            type="account_onboarding",
                        )
                        print(f"[DEBUG - create_paid_event] Stripe account link created: {account_link.url}")
                        
                        return JSONResponse(
                            content={
                                "error": "Please complete your Stripe account setup before creating a paid event.",
                                "stripeLink": account_link.url
                            },
                            status_code=status.HTTP_400_BAD_REQUEST,
                        )
                except stripe.error.StripeError as e:
                    return JSONResponse(
                        content={"error": f"An error occurred with Stripe: {str(e)}"},
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )

                # Determine whether the user is associated with a college
                is_in_college = (user_profile.college is not None)
                
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
                            description=new_event.description[:500],  # Limit description length
                            metadata={
                                "eventId": str(new_event.eventId)
                            }
                        )
                        new_event.stripeProductId = product.id
                    except stripe.error.StripeError as e:
                        return JSONResponse(
                            content={"error": f"An error occurred with Stripe: {str(e)}"},
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        )
                    
                    new_event.save()
                    print(f"[DEBUG - create_paid_event] Event created: {new_event}")

                    # Create location serializer instance
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

                    # Create host serializer instance
                    host = HostSerializer(
                        id=str(host_profile.hostProfileId),
                        name=f"{user.first_name} {user.last_name}",
                    )

                    # Process image URLs
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

                    # Create event response serializer instance
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

                    # Properly serialize the event_data to make it JSON serializable
                    serialized_event_data = event_data.model_dump(mode="json")
                    print(f"[DEBUG - create_paid_event] Serialized event data: {serialized_event_data}")
                    return {"message": "Paid event created successfully.", "event": serialized_event_data}
                else:
                    # Here we raise an error with the form errors so that we can return a 400 response
                    raise ValueError(event_form.errors)
            except CustomUser.DoesNotExist:
                return JSONResponse(
                    content={"error": "User not found"},
                    status_code=status.HTTP_404_NOT_FOUND
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
        return JSONResponse(
            content={"error": f"An unexpected error occurred: {str(e)}"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get("/event/get_host_stripe_account_link")
async def get_host_stripe_account_link(user_id: int = Depends(get_current_user)):
    """
    API endpoint to check a host's Stripe account status and provide an onboarding link if needed.
    Returns either a success message if the account is fully set up, or an onboarding link if setup is incomplete.
    """
    # Use the same domain as in become_host for consistency
    site_domain = "https://waveoncampus.com"
    
    @sync_to_async
    def process_stripe_account_check():
        try:
            # Get the user account with proper error handling
            user = get_object_or_404(CustomUser, id=user_id)
            
            # Check if user has a Stripe Connect account ID
            if not user.connectAccountID:
                return JSONResponse(
                    content={
                        "error": "You need to set up your Stripe account first.",
                        "redirect": "/host/stripe-setup/"
                    },
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            # Initialize account status flag
            is_fully_onboarded = False
            
            # Check the Stripe account status
            try:
                # Retrieve the Stripe account details
                stripe_account = stripe.Account.retrieve(user.connectAccountID)
                is_fully_onboarded = stripe_account.get("payouts_enabled", False)
                
                # Create an account link for onboarding or updating account details
                account_link = stripe.AccountLink.create(
                    account=user.connectAccountID,
                    refresh_url=f'{site_domain}/refresh/{user.connectAccountID}',
                    return_url=f"{site_domain}/host/portal/",
                    type="account_onboarding",
                )
                
                # Return appropriate response based on account status
                if not is_fully_onboarded:
                    return JSONResponse(
                        content={
                            "error": "Please complete your Stripe account setup.",
                            "stripeLink": account_link.url  # Include the URL, not the entire object
                        },
                        status_code=status.HTTP_200_OK  # Using 200 instead of 400 as this is an expected state
                    )
                else:
                    return JSONResponse(
                        content={
                            "success": "Stripe account setup completed.",
                            "updateLink": account_link.url  # Provide link for updating account details
                        },
                        status_code=status.HTTP_200_OK
                    )
            except stripe.error.StripeError as e:
                # Log the specific Stripe error for debugging
                print(f"Stripe error in get_host_stripe_account_link: {str(e)}")
                return JSONResponse(
                    content={"error": f"Stripe error: {str(e)}"},
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        except CustomUser.DoesNotExist:
            return JSONResponse(
                content={"error": "User not found"},
                status_code=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            # Include traceback for unexpected errors
            traceback_str = traceback.format_exc()
            print(f"Error in get_host_stripe_account_link: {str(e)}\n{traceback_str}")
            return JSONResponse(
                content={"error": f"An unexpected error occurred: {str(e)}"},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    # Execute the function and return the result
    return await process_stripe_account_check()
    
@router.get("/event/paid/ticket/fields")
async def paid_ticket_creation_fields(request: Request):
    print(f"[DEBUG - paid_ticket_creation_fields] Function called")
    FormClass = PaidFreeTicketForm
    fields_info = get_form_fields(FormClass)
    print(f"[DEBUG - paid_ticket_creation_fields] Returning form fields: {list(fields_info.keys())}")
    return JSONResponse(content=fields_info, status_code=status.HTTP_200_OK)


@router.post("/event/{eventId}/createPaidFreeTicket")
async def create_paid_free_ticket(eventId: str, request: Request):
    print(f"[DEBUG - create_paid_free_ticket] Function called with eventId: {eventId}")
    try:
        # Get request data - could be form data or JSON
        content_type = request.headers.get('content-type', '')
        
        if 'application/json' in content_type:
            # Handle JSON data
            data = await request.json()
            print(f"[DEBUG - create_paid_free_ticket] Processing JSON data: {data}")
        else:
            # Handle form data
            form_data = await request.form()
            data = {}
            files = {}
            print(f"[DEBUG - create_paid_free_ticket] Processing form data")
            for key, value in form_data.multi_items():
                if isinstance(value, UploadFile):
                    files[key] = value
                else:
                    data[key] = value
        
        print(f"[DEBUG - create_paid_free_ticket] Received data: {data}")
        
        # Wrap Django ORM calls and form processing in a synchronous function
        @sync_to_async
        def process_create_ticket(eventId, data):
            # Fetch the event object or raise a 404 error if not found
            event = get_object_or_404(Event, eventId=eventId)
            
            # Map frontend field names to model field names if needed
            form_data = {}
            field_mapping = {
                'ticket_name': 'ticket_name',
                'ticket_price': 'ticket_price',
                'ticket_description': 'ticket_description',
                'ticket_quantity': 'ticket_quantity',
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
                    "ticketPrice": str(new_ticket.ticket_price),  # Convert to string for JSON serialization
                }
            else:
                print(f"[DEBUG - create_paid_free_ticket] Ticket form is invalid: {ticket_form.errors}")
                # Here we raise an error with the form errors so that we can return a 400 response.
                raise ValueError(ticket_form.errors)
        
        # Execute the create ticket function
        result = await process_create_ticket(eventId, data)
        print(f"[DEBUG - create_paid_free_ticket] Ticket created with ID: {result.get('code', 'unknown')}")
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
        return JSONResponse(
            content={"error": f"An unexpected error occurred: {str(e)}"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get("/event/paid/coupon/fields")
async def paid_coupon_creation_fields(request: Request):
    print(f"[DEBUG - paid_coupon_creation_fields] Function called")
    FormClass = CouponCodeForm
    fields_info = get_form_fields(FormClass)
    print(f"[DEBUG - paid_coupon_creation_fields] Returning form fields: {list(fields_info.keys())}")
    return JSONResponse(content=fields_info, status_code=status.HTTP_200_OK)


@router.get("/event/{eventId}/coupons")
async def get_event_coupons(eventId: str, request: Request):
    print(f"[DEBUG - get_event_coupons] Function called with eventId: {eventId}")
    try:
        # Wrap Django ORM calls in a synchronous function
        @sync_to_async
        def get_event_coupons_sync(event_id):
            print(f"[DEBUG - get_event_coupons] Fetching coupons for event: {event_id}")
            # Fetch the event object or raise a 404 error if not found
            event = get_object_or_404(Event, eventId=event_id)
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
                    "createdAt": coupon["created_at"].isoformat() if coupon["created_at"] else None,
                    "updatedAt": coupon["updated_at"].isoformat() if coupon["updated_at"] else None
                }
                coupons_list.append(coupon_data)
            return coupons_list

        # Execute synchronous function asynchronously
        coupons = await get_event_coupons_sync(eventId)
        print(f"[DEBUG - get_event_coupons] Found {len(coupons)} coupons")
    except Event.DoesNotExist:
        return JSONResponse(
            content={"message": "Event not found."},
            status_code=status.HTTP_404_NOT_FOUND,
        )
    except Exception as e:
        traceback_str = traceback.format_exc()
        print(f"Get Event Coupons error: {str(e)}\n{traceback_str}")
        return JSONResponse(
            content={"error": f"An unexpected error occurred: {str(e)}"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return JSONResponse(content=coupons, status_code=status.HTTP_200_OK)


@router.get("/event/{eventId}/paid/tickets")
async def get_paid_event_tickets(eventId: str, request: Request):
    print(f"[DEBUG - get_paid_event_tickets] Function called with eventId: {eventId}")
    try:
        # Wrap Django ORM calls in a synchronous function
        @sync_to_async
        def get_paid_event_tickets_sync(event_id):
            print(f"[DEBUG - get_paid_event_tickets] Fetching tickets for event: {event_id}")
            # Fetch the event object or raise a 404 error if not found
            event = get_object_or_404(Event, eventId=event_id)
            tickets = PaidFreeTicket.objects.filter(event=event).values()
            tickets_list = []
            for ticket in tickets:
                # Convert all non-JSON serializable types to strings
                for key, value in ticket.items():
                    if isinstance(value, UUID):
                        ticket[key] = str(value)
                    elif isinstance(value, datetime):
                        ticket[key] = value.isoformat()
                tickets_list.append(ticket)
            return tickets_list

        # Execute synchronous function asynchronously
        tickets = await get_paid_event_tickets_sync(eventId)
        print(f"[DEBUG - get_paid_event_tickets] Found {len(tickets)} tickets")
    except Event.DoesNotExist:
        return JSONResponse(
            content={"message": "Event not found."},
            status_code=status.HTTP_404_NOT_FOUND,
        )
    except Exception as e:
        traceback_str = traceback.format_exc()
        print(f"Get Paid Event Tickets error: {str(e)}\n{traceback_str}")
        return JSONResponse(
            content={"error": f"An unexpected error occurred: {str(e)}"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return JSONResponse(content=tickets, status_code=status.HTTP_200_OK)


@router.post("/event/{eventId}/paid/ticket/delete")
async def delete_paid_event_ticket(eventId: str, request: Request):
    print(f"[DEBUG - delete_paid_event_ticket] Function called with eventId: {eventId}")
    try:
        # Get the request data
        data = await request.json()
        print(f"[DEBUG - delete_paid_event_ticket] Request data: {data}")
        
        # Check if ticket_id is provided
        ticket_id = data.get("ticket_id")
        if not ticket_id:
            return JSONResponse(
                content={"error": "Missing ticket ID."}, 
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        # Wrap Django ORM calls in a synchronous function
        @sync_to_async
        def delete_ticket_sync(event_id, ticket_id):
            event = get_object_or_404(Event, eventId=event_id)
            ticket = get_object_or_404(PaidFreeTicket, ticket_id=ticket_id, event=event)
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
        return JSONResponse(
            content={"error": f"An unexpected error occurred: {str(e)}"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.post("/event/{eventId}/createCoupon")
async def create_event_coupon(eventId: str, payload: dict):
    """
    Create a coupon for the given event. Body is JSON.
    """
    @sync_to_async
    def create_coupon(eventId, payload):
        event = get_object_or_404(Event, eventId=eventId)

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
                detail=f"An unexpected error occurred: {str(e)}"
            )
        raise e
    
class DeleteCouponRequest(BaseModel):
    coupon_id: str

@router.post("/event/{eventId}/deleteCoupon")
async def delete_coupon(eventId: str, deleteCouponRequest: DeleteCouponRequest):
    @sync_to_async
    def delete_coupon_sync(event_id, coupon_id):
        event = get_object_or_404(Event, eventId=event_id)
        coupon = get_object_or_404(CouponCode, coupon_id=coupon_id)
        if coupon.event != event:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Coupon does not belong to this event"
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
                detail=f"An unexpected error occurred: {str(e)}"
            )
        raise e

@router.get("/event/{eventId}/rsvp")
async def get_event_rsvp_list(eventId: str, request: Request):
    print(f"[DEBUG - get_event_rsvp_list] Function called with eventId: {eventId}")
    try:
        # Wrap Django ORM calls in a synchronous function         
        @sync_to_async
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
    except Event.DoesNotExist:
        return JSONResponse(
            content={"message": "Event not found."},
            status_code=status.HTTP_404_NOT_FOUND,
        )
    except Exception as e:
        traceback_str = traceback.format_exc()
        print(f"Get Event RSVP List error: {str(e)}\n{traceback_str}")
        return JSONResponse(
            content={"error": f"An unexpected error occurred: {str(e)}"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return JSONResponse(content=rsvp_list, status_code=status.HTTP_200_OK)


@router.api_route("/event/{eventId}/rsvp/delete", methods=["DELETE", "POST"])
async def delete_event_rsvp(eventId: str, request: Request, ticket_id: Optional[str] = None, user_id: int = Depends(get_current_user)):
    print(f"[DEBUG - delete_event_rsvp] Function called with eventId: {eventId}, user_id: {user_id}")
    """
    API endpoint for a host to delete a user's RSVP ticket
    """
    try:
        # Try to get ticket_id from multiple sources
        # 1. Check if it was passed as a query parameter
        if ticket_id is None:
            ticket_id = request.query_params.get("ticket_id")
            
        # 2. Check if it was passed in form data
        if ticket_id is None:
            try:
                form_data = await request.form()
                ticket_id = form_data.get("ticket_id")
            except Exception:
                pass
                
        # 3. Check if it was passed as JSON in request body
        if ticket_id is None:
            try:
                data = await request.json()
                print(f"[DEBUG - delete_event_rsvp] Request data from JSON: {data}")
                ticket_id = data.get("ticket_id")
            except json.JSONDecodeError:
                # No valid JSON in the request body
                pass
        
        print(f"[DEBUG - delete_event_rsvp] Ticket ID: {ticket_id}")
        
        # Check if ticket_id was found in any of the sources
        if not ticket_id:
            return JSONResponse(
                content={"error": "Missing ticket ID. Please provide it as a query parameter, form field, or in JSON body."}, 
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        # Wrap Django ORM calls in a synchronous function
        @sync_to_async
        def delete_rsvp_ticket():
            # Get the event object or raise a 404 error if not found
            event = get_object_or_404(Event, eventId=eventId)
            
            # Get the current user
            user = CustomUser.objects.get(id=user_id)
            
            # Check if the requesting user is the host of the event
            if event.host != user:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have permission to delete RSVP tickets. Only the event host can manage tickets."
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
                    detail="RSVP ticket not found."
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
        # Log the exception details and return a server error
        traceback_str = traceback.format_exc()
        print(f"Delete RSVP Ticket error: {str(e)}\n{traceback_str}")
        
        # Return error response
        return JSONResponse(
            content={"error": f"An unexpected error occurred: {str(e)}"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get("/event/{eventId}/purchasedTickets")
async def get_purchased_tickets_for_event(eventId: str, user_id: int = Depends(get_current_user)):
    print(f"[DEBUG - get_purchased_tickets_for_event] Function called with eventId: {eventId}, user_id: {user_id}")
    """
    API endpoint for getting purchased tickets for an event
    Only the host of the event can access this endpoint
    """
    try:
        # Wrap Django ORM calls in a synchronous function
        @sync_to_async
        def get_purchased_tickets_sync(event_id):
            print(f"[DEBUG - get_purchased_tickets_for_event] Fetching purchased tickets for event: {event_id}")
            # Get the event object or raise a 404 error if not found
            event = get_object_or_404(Event, eventId=event_id)
            
            # Get the current user
            user = CustomUser.objects.get(id=user_id)
            
            # Check if the requesting user is the host of the event
            if event.host != user:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have permission to access these tickets. Only the event host can view ticket information."
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
        print(f"[DEBUG - get_purchased_tickets_for_event] Found {len(purchased_tickets_data)} purchased tickets")
        
        return JSONResponse(content={"purchasedTickets": purchased_tickets_data}, status_code=status.HTTP_200_OK)
        
    except HTTPException as http_ex:
        # Handle HTTP exceptions separately
        return JSONResponse(
            content={"error": str(http_ex.detail)},
            status_code=http_ex.status_code,
        )
    except Exception as e:
        # Log the exception details and return a server error
        traceback_str = traceback.format_exc()
        print(f"Get Purchased Tickets error: {str(e)}\n{traceback_str}")
        
        # Return error response
        return JSONResponse(
            content={"error": f"An unexpected error occurred: {str(e)}"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )



@router.post("/event/{eventId}/purchasedTickets/delete")
async def delete_purchased_ticket(eventId: str, request: Request, user_id: int = Depends(get_current_user)):
    print(f"[DEBUG - delete_purchased_ticket] Function called with eventId: {eventId}, user_id: {user_id}")
    """
    API endpoint for deleting a purchased ticket
    Only the host of the event can delete tickets
    """
    try:
        # Get the request data
        data = await request.json()
        print(f"[DEBUG - delete_purchased_ticket] Request data: {data}")
        
        # Check if ticket_id is provided
        ticket_id = data.get("ticket_id")
        if not ticket_id:
            return JSONResponse(
                content={"error": "Missing ticket ID."}, 
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        # Wrap Django ORM calls in a synchronous function
        @sync_to_async
        def delete_purchased_ticket_sync():
            # Get the event object or raise a 404 error if not found
            event = get_object_or_404(Event, eventId=eventId)
            
            # Get the current user
            user = CustomUser.objects.get(id=user_id)
            
            # Check if the requesting user is the host of the event
            if event.host != user:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have permission to delete tickets. Only the event host can manage tickets."
                )
            
            try:
                # Find the ticket to delete
                ticket = Ticket.objects.get(ticketId=ticket_id, event=event)
                
                # Delete the ticket
                ticket.delete()
                
                # Return success message
                return {
                    "message": "Purchased ticket deleted successfully."
                }
                
            except Ticket.DoesNotExist:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Ticket not found."
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
        # Log the exception details and return a server error
        traceback_str = traceback.format_exc()
        print(f"Delete Purchased Ticket error: {str(e)}\n{traceback_str}")
        
        # Return error response
        return JSONResponse(
            content={"error": f"An unexpected error occurred: {str(e)}"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.post("/event/becomeHost")
async def become_host(request: Request, user_id: int = Depends(get_current_user)):
    print(f"[DEBUG - become_host] Function called with user_id: {user_id}")
    """
    API endpoint for becoming a host on the platform and ensuring Stripe onboarding is complete
    """
    try:
        # Wrap Django ORM calls in a synchronous function
        @sync_to_async
        def process_become_host():
            try:
                # Get the current user
                user = get_object_or_404(CustomUser, id=user_id)
                
                # Set up common variables for Stripe redirect URLs
                site_domain = "https://waveoncampus.com"
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
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
                        )
                
                # Case 1: User is a host and fully onboarded with Stripe
                if is_host and is_fully_onboarded:
                    return JSONResponse(
                        content={"message": "You are already a host with a complete Stripe setup."},
                        status_code=status.HTTP_200_OK
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
                                "connect_account_id": user.connectAccountID
                            },
                            status_code=status.HTTP_200_OK
                        )
                    except stripe.error.StripeError as e:
                        return JSONResponse(
                            content={"error": f"Failed to generate onboarding link: {str(e)}"},
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
                        )
                
                # Case 3: User is a host but has no Stripe account
                if is_host and not has_connect_account:
                    return JSONResponse(
                        content={"message": "You are a host but missing Stripe setup. Please contact support."},
                        status_code=status.HTTP_200_OK
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
                        stripe_connect_account = ConnectAccount.createConnectAccount(None, user)
                        
                        if not stripe_connect_account:
                            return JSONResponse(
                                content={"error": "Failed to create Stripe Connect account"},
                                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
                            )
                            
                        # Update user with new account ID
                        user.connectAccountID = stripe_connect_account.id
                        user.connectAccountCreated = True
                        
                    except stripe.error.StripeError as e:
                        return JSONResponse(
                            content={"error": f"Stripe error: {str(e)}"},
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
                        )
                
                # Generate onboarding link
                try:
                    stripe_link_account = ConnectAccount.getStripeOnboardingLink(
                        None, user.connectAccountID, site_domain, redirect_link
                    )
                except stripe.error.StripeError as e:
                    return JSONResponse(
                        content={"error": f"Failed to generate onboarding link: {str(e)}"},
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
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
                    "connect_account_id": user.connectAccountID
                }
                
            except CustomUser.DoesNotExist:
                return JSONResponse(
                    content={"error": "User not found"},
                    status_code=status.HTTP_404_NOT_FOUND
                )
            except Exception as e:
                traceback_str = traceback.format_exc()
                print(f"Become Host error: {str(e)}\n{traceback_str}")
                return JSONResponse(
                    content={"error": f"An unexpected error occurred: {str(e)}"},
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        # Execute the become host function
        result = await process_become_host()
        if isinstance(result, JSONResponse):
            return result
        return JSONResponse(content=result, status_code=status.HTTP_200_OK)
    
    except Exception as e:
        # Log the exception details and return a server error
        traceback_str = traceback.format_exc()
        print(f"Become Host error: {str(e)}\n{traceback_str}")
        return JSONResponse(
            content={"error": f"An unexpected error occurred: {str(e)}"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.get("/event/{eventId}/analytics")
async def get_event_analytics(eventId: str, user_id: int = Depends(get_current_user)):
    """
    API endpoint for retrieving comprehensive event analytics data.
    Returns detailed analytics including performance metrics, audience insights, revenue data, and more.
    """
    print(f"[get_event_analytics] API called with eventId: {eventId}, user_id: {user_id}")

    @sync_to_async
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
                    detail="You don't have permission to access analytics for this event. Only the event host can view analytics."
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
                host_events = Event.objects.filter(host=event.host).exclude(eventId=event.eventId)
                viewed_users = EventView.objects.filter(event=event, user__isnull=False).values_list('user_id', flat=True)
                return_visitors = EventView.objects.filter(
                    event__in=host_events, 
                    user_id__in=viewed_users
                ).values('user_id').distinct().count()

            # ===========================================
            # 2. TICKET PERFORMANCE & REVENUE
            # ===========================================
            
            # Get all tickets for this event
            tickets = Ticket.objects.filter(event=event).select_related('user')
            total_tickets_sold = tickets.count()
            unique_purchasers = tickets.values('user', 'guestEmail').distinct().count()
            
            # Calculate total revenue and average order value
            total_revenue = 0
            average_order_value = 0
            ticket_type_performance = []
            
            if event.ticketing == "Paid":
                # Get ticket types for this event
                ticket_types = PaidFreeTicket.objects.filter(event=event)
                
                for ticket_type in ticket_types:
                    tickets_sold = ticket_type.ticket_sold
                    price = float(ticket_type.ticket_price) if ticket_type.ticket_price else 0
                    revenue = price * tickets_sold
                    total_revenue += revenue
                    
                    # Ticket type performance breakdown
                    ticket_type_performance.append({
                        'ticket_name': ticket_type.ticket_name,
                        'ticket_price': price,
                        'tickets_available': ticket_type.ticket_quantity,
                        'tickets_sold': tickets_sold,
                        'revenue': revenue,
                        'sell_through_rate': round((tickets_sold / ticket_type.ticket_quantity) * 100, 1) if ticket_type.ticket_quantity > 0 else 0
                    })
                
                # Calculate average order value
                if unique_purchasers > 0:
                    average_order_value = round(total_revenue / unique_purchasers, 2)
            
            # Conversion rate
            conversion_rate = 0
            if total_views > 0:
                conversion_rate = round(min((unique_purchasers / total_views) * 100, 100), 1)

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
                user_cities = UserProfile.objects.filter(
                    user__in=tickets.filter(user__isnull=False).values('user')
                ).exclude(city__isnull=True).exclude(city='').values('city').annotate(
                    count=Count('city')
                ).order_by('-count')[:10]  # Top 10 cities
                
                for city_data in user_cities:
                    geographic_distribution.append({
                        'city': city_data['city'],
                        'count': city_data['count']
                    })
            except Exception as e:
                print(f"Error calculating geographic distribution: {e}")

            # Demographics (Note: Limited data due to UserProfile changes)
            # Age and Gender distribution would be limited due to removed fields
            age_distribution = {
                'message': 'Age data not available due to privacy updates'
            }
            gender_distribution = {
                'message': 'Gender data not available due to privacy updates'
            }

            # ===========================================
            # 4. PAGE ANALYTICS
            # ===========================================
            
            # Calculate average time on page and bounce rate
            event_views = EventView.objects.filter(event=event).order_by('timestamp')
            
            # For bounce rate, we consider users who only viewed this event page
            # and no other pages (simplified metric)
            bounce_rate = 0
            avg_time_on_page = 0
            
            try:
                # Calculate basic page metrics
                if event_views.exists():
                    # Simplified bounce rate: users with only one view session
                    single_view_users = event_views.values('user', 'session_key').annotate(
                        view_count=Count('id')
                    ).filter(view_count=1).count()
                    
                    total_view_sessions = event_views.values('user', 'session_key').distinct().count()
                    if total_view_sessions > 0:
                        bounce_rate = round((single_view_users / total_view_sessions) * 100, 1)
                
                # Simplified average time (placeholder - would need session tracking for accuracy)
                avg_time_on_page = "Not available - requires session tracking implementation"
                
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
                hourly_data = event_views.filter(
                    timestamp__gte=last_week
                ).extra(
                    select={'hour': 'EXTRACT(hour FROM timestamp)'}
                ).values('hour').annotate(
                    view_count=Count('id')
                ).order_by('hour')
                
                # Fill in missing hours with 0 views
                hours_dict = {hour['hour']: hour['view_count'] for hour in hourly_data}
                for hour in range(24):
                    hourly_views.append({
                        'hour': f"{hour:02d}:00",
                        'views': hours_dict.get(hour, 0)
                    })
                    
            except Exception as e:
                print(f"Error calculating hourly views: {e}")
                hourly_views = [{'hour': f"{h:02d}:00", 'views': 0} for h in range(24)]

            # ===========================================
            # 6. SOCIAL MEDIA & ENGAGEMENT
            # ===========================================
            
            # Social media shares breakdown (could be expanded with platform-specific data)
            social_media_shares = {
                'total_shares': total_shares,
                'platforms': {
                    'general': total_shares  # Placeholder - could be expanded with platform-specific tracking
                }
            }

            # ===========================================
            # 7. CUSTOMER DATA
            # ===========================================
            
            # Enhanced customer data
            customers = []
            for ticket in tickets.order_by('-created_at'):
                # Determine ticket type
                ticket_type = "General Admission"  # Default
                try:
                    if event.ticketing == "Paid":
                        # Try to determine ticket type from available ticket types
                        # This is a simplified approach - in practice, you'd want to track this relationship
                        first_ticket_type = PaidFreeTicket.objects.filter(event=event).first()
                        if first_ticket_type:
                            ticket_type = first_ticket_type.ticket_name
                except Exception:
                    pass

                customer = {
                    'first_name': ticket.user.first_name if ticket.user else ticket.guestFirstName,
                    'last_name': ticket.user.last_name if ticket.user else ticket.guestLastName,
                    'email': ticket.user.email if ticket.user else ticket.guestEmail,
                    'ticket_type': ticket_type,
                    'purchase_date': ticket.created_at.isoformat() if ticket.created_at else None,
                    'status': ticket.status,
                    'user_type': 'Registered' if ticket.user else 'Guest'
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
                        "paid_tickets": total_tickets_sold if event.ticketing == "Paid" else 0,
                        "free_tickets": total_tickets_sold if event.ticketing == "Free" else 0,
                    }
                },
                "audience_analytics": {
                    "login_status_distribution": {
                        "logged_in_users": logged_in_users,
                        "guest_users": guest_users
                    },
                    "attendance_distribution": {
                        "attended": scanned_tickets,
                        "did_not_attend": not_attended
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
                    "total_engagement": total_favorites + total_shares + total_go_with_requests,
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
                        'Logged-in Users': logged_in_users,
                        'Guest Users': guest_users
                    },
                    "attendance": {
                        'Attended': scanned_tickets,
                        'Did Not Attend': not_attended
                    },
                },
                "tickets": {
                    "total_tickets_count": total_tickets_sold,
                    "scanned_tickets_count": scanned_tickets,
                },
            }

            print(f"[get_analytics_data] Successfully retrieved comprehensive analytics for event: {event.title}")
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
            raise HTTPException(status_code=500, detail=f"Error retrieving analytics: {str(e)}")

    try:
        analytics_data = await get_analytics_data(eventId, user_id)
        print(f"[get_event_analytics] Returning comprehensive analytics for event: {analytics_data['event']['title']}")
        return analytics_data

    except HTTPException as http_ex:
        print(f"[get_event_analytics] HTTPException: {http_ex.detail}")
        raise http_ex
    except Exception as e:
        print(f"[get_event_analytics] Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


@router.get("/analytics")
async def get_host_recent_events_analytics(user_id: int = Depends(get_current_user)):
    """
    API endpoint for retrieving comprehensive analytics data for the most recent 30 events hosted by a user.
    Returns aggregated analytics across the user's most recent events including totals, averages, and event-specific data.
    Events are sorted by scheduled date (upcoming events first, then most recent past events).
    Limited to 30 events for optimal performance.
    """
    print(f"[get_host_recent_events_analytics] API called with user_id: {user_id}")

    @sync_to_async
    def get_recent_events_analytics_data(requesting_user_id):
        try:
            # Get the user and verify they exist
            requesting_user = get_object_or_404(CustomUser, id=requesting_user_id)
            
            # Check if the user is a host
            is_host = requesting_user.groups.filter(name="Host").exists()
            if not is_host:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have permission to access host analytics. Only hosts can view this data."
                )            # Get the most recent 30 events hosted by this user, sorted by scheduled time
            # (upcoming events first, then most recent past events)
            all_events = Event.objects.filter(host=requesting_user).order_by('-date')[:30]
            
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
                    }
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
                event_favorites = UserProfile.objects.filter(favorite_events=event).count()
                event_go_with = GoWithRequest.objects.filter(event=event).count()
                
                # Get tickets for this event
                event_tickets = Ticket.objects.filter(event=event)
                event_ticket_count = event_tickets.count()
                unique_purchasers = event_tickets.values('user', 'guestEmail').distinct().count()
                
                # Calculate conversion rate for this event
                event_conversion_rate = 0
                if event.views > 0:
                    event_conversion_rate = round(min((unique_purchasers / event.views) * 100, 100), 1)
                
                # Calculate revenue for this event (assuming ticket price is stored)
                event_revenue = 0
                for ticket in event_tickets:
                    # If ticket has a price field, add it to revenue
                    if hasattr(ticket, 'price') and ticket.price:
                        event_revenue += float(ticket.price)
                
                # Calculate attendance data
                scanned_tickets = event_tickets.filter(status="Scanned").count()
                attendance_rate = round((scanned_tickets / event_ticket_count * 100), 1) if event_ticket_count > 0 else 0
                
                # Prepare event-specific analytics
                event_analytics = {
                    "eventId": str(event.eventId),
                    "title": event.title,
                    "date": event.date.isoformat() if event.date else None,
                    "created_at": event.created_at.isoformat() if event.created_at else None,
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
                        "logged_in_users": event_tickets.filter(user__isnull=False).count(),
                        "guest_users": event_tickets.filter(user__isnull=True).count(),
                    }
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
                        monthly_data[month_key] = {"events": 0, "tickets": 0, "revenue": 0}
                    monthly_data[month_key]["events"] += 1
                    monthly_data[month_key]["tickets"] += event_ticket_count
                    monthly_data[month_key]["revenue"] += event_revenue

            # Calculate averages
            total_events = all_events.count()
            average_conversion_rate = round(sum(conversion_rates) / len(conversion_rates), 1) if conversion_rates else 0
            average_views_per_event = round(total_views / total_events, 1) if total_events > 0 else 0
            average_tickets_per_event = round(total_tickets_sold / total_events, 1) if total_events > 0 else 0
            average_revenue_per_event = round(total_revenue / total_events, 2) if total_events > 0 else 0

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
                    "monthly_events": {month: data["events"] for month, data in monthly_data.items()},
                    "monthly_tickets": {month: data["tickets"] for month, data in monthly_data.items()},
                    "monthly_revenue": {month: round(data["revenue"], 2) for month, data in monthly_data.items()},
                },
                "host_info": {
                    "host_id": str(requesting_user.id),
                    "username": requesting_user.username,
                    "first_name": requesting_user.first_name,
                    "last_name": requesting_user.last_name,                    "total_events_hosted": total_events,
                }
            }

            print(f"[get_recent_events_analytics_data] Successfully retrieved analytics for {total_events} recent events for host: {requesting_user.username}")
            return analytics_data

        except CustomUser.DoesNotExist:
            print(f"[get_recent_events_analytics_data] User not found with ID: {requesting_user_id}")
            raise HTTPException(status_code=404, detail="User not found")
        except Exception as e:
            print(f"[get_recent_events_analytics_data] Error retrieving analytics: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error retrieving analytics: {str(e)}")

    try:
        analytics_data = await get_recent_events_analytics_data(user_id)
        print(f"[get_host_recent_events_analytics] Returning analytics for {analytics_data['summary']['total_events']} events")
        return analytics_data
    except HTTPException as http_ex:
        print(f"[get_host_recent_events_analytics] HTTPException: {http_ex.detail}")
        raise http_ex
    except Exception as e:
        print(f"[get_host_recent_events_analytics] Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


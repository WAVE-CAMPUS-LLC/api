from uuid import UUID
import time
import stripe
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
from eventManagementApp.models import Event, HostProfile, CouponCode
from accountManagementApp.models import UserProfile
from eventTicketsApp.models import RSVPTicket, PaidFreeTicket, Ticket
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
                # Convert UUID to string if present
                if isinstance(coupon.get("coupon_id"), UUID):
                    coupon["coupon_id"] = str(coupon["coupon_id"])
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
                if isinstance(ticket["ticket_id"], UUID):
                    ticket["ticket_id"] = str(ticket["ticket_id"])
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
                if isinstance(rsvp["ticketId"], UUID):
                    rsvp["ticketId"] = str(rsvp["ticketId"])
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


@router.post("/event/{eventId}/rsvp/delete")
async def delete_event_rsvp(eventId: str, request: Request, user_id: int = Depends(get_current_user)):
    print(f"[DEBUG - delete_event_rsvp] Function called with eventId: {eventId}, user_id: {user_id}")
    """
    API endpoint for a host to delete a user's RSVP ticket
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
            return TicketSerializer(purchased_tickets, many=True).data
        
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
        
        
from uuid import UUID
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
from eventTicketsApp.models import RSVPTicket, PaidFreeTicket
from eventManagementApp.forms import EditEventForm, EventForm
from dotenv import load_dotenv
import os

router = APIRouter()


@router.api_route("/event/{eventId}/editEvent", methods=["POST", "PATCH"])
async def edit_event_endpoint(
    request: Request, eventId: str, user_id=Depends(get_current_user)
):
    """
    Edit an event, supporting both full updates (POST) and partial updates (PATCH).
    """
    try:
        # Get form data (includes both text fields and files)
        form_data = await request.form()

        # Separate normal data and file data from the form
        data = {}
        files = {}
        for key, value in form_data.multi_items():
            if isinstance(value, UploadFile):
                files[key] = value
            else:
                data[key] = value

        # Determine if this is a partial update (PATCH)
        partial = request.method.upper() == "PATCH"

        # Wrap Django ORM calls and form processing in a synchronous function
        @sync_to_async
        def process_edit_event():
            # Retrieve the event or raise a 404
            event = get_object_or_404(Event, eventId=eventId)

            # Get the current user's profile.
            # Depending on your get_current_user, `user` might be a user instance.
            user = CustomUser.objects.get(id=user_id)
            user_profile = UserProfile.objects.get(user=user)

            # Get the host profile for the event host
            host_profile = HostProfile.objects.get(user=event.host)

            # Determine whether the user is associated with a college
            is_in_college = user_profile.college is not None

            # Instantiate the Django form with submitted data, file uploads, instance and partial flag.
            edit_event_form = EditEventForm(
                data, files, instance=event, partial=partial
            )

            if edit_event_form.is_valid():
                updated_event = edit_event_form.save()

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
                # Use model_dump_json=True to handle datetime serialization
                return response.model_dump(mode="json")
            else:
                # Here we raise an error with the form errors so that we can return a 400 response.
                raise ValueError(edit_event_form.errors)

        # Await the synchronous process
        result = await process_edit_event()
        return JSONResponse(content=result, status_code=status.HTTP_200_OK)

    except ValueError as ve:
        # Return any form validation errors
        return JSONResponse(
            content={"errors": str(ve), "message": "Failed to update event."},
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
                    host_profile = HostProfile.objects.get(user=user_obj)
                    # Then get the events where host is this host profile
                    host_events = Event.objects.filter(host=host_profile)
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
        if not user:
            return JSONResponse(
                content={"error": "Authentication required"},
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        events_before_serializing = await get_events(user_id)
        events = [HostEventExplore(**event) for event in events_before_serializing]

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
    """
    API endpoint for deleting an event
    """
    try:

        @sync_to_async
        def delete_event(eventId):
            # Get the event object or raise a 404 error if not found
            event = get_object_or_404(Event, eventId=eventId)
            event.delete()
            return {"message": "Event deleted successfully."}

        result = await delete_event(eventId)
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
    FormClass = EventForm
    fields_info = get_form_fields(FormClass)
    return JSONResponse(content=fields_info, status_code=status.HTTP_200_OK)


@router.post("/event/free/create")
async def create_free_event(request: Request, user_id: int = Depends(get_current_user)):
    """
    API endpoint for creating a free event
    """
    try:
        # Get form data (includes both text fields and files)
        form_data = await request.form()

        # Separate normal data and file data from the form
        data = {}
        files = {}
        for key, value in form_data.multi_items():
            if isinstance(value, UploadFile):
                files[key] = value
            else:
                data[key] = value

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

            if event_form.is_valid():
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

                return {"message": "Event created successfully.", "event": event_data}
            else:
                # Here we raise an error with the form errors so that we can return a 400 response.
                raise ValueError(event_form.errors)

        # Execute the create event function
        result = await process_create_event()
        return JSONResponse(content=result, status_code=status.HTTP_200_OK)

    except ValueError as ve:
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


@router.get("/event/paid/ticket/fields")
async def paid_ticket_creation_fields(request: Request):
    FormClass = PaidFreeTicketForm
    fields_info = get_form_fields(FormClass)
    return JSONResponse(content=fields_info, status_code=status.HTTP_200_OK)


@router.get("/event/paid/coupon/fields")
async def paid_coupon_creation_fields(request: Request):
    FormClass = CouponCodeForm
    fields_info = get_form_fields(FormClass)
    return JSONResponse(content=fields_info, status_code=status.HTTP_200_OK)


@router.get("/event/{eventId}/coupons")
async def get_event_coupons(eventId: str, request: Request):
    try:
        # Wrap Django ORM calls in a synchronous function
        @sync_to_async
        def get_event_coupons_sync(event_id):
            # Fetch the event object or raise a 404 error if not found
            event = get_object_or_404(Event, eventId=event_id)
            coupon_codes = CouponCode.objects.filter(event=event).values()
            coupons_list = []
            for coupon in coupon_codes:
                if isinstance(coupon["couponCode"], UUID):
                    coupon["couponCode"] = str(coupon["couponCode"])
                coupons_list.append(coupon)
            return coupons_list

        # Execute synchronous function asynchronously
        coupons = await get_event_coupons_sync(eventId)
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


@router.post("/event/{eventId}/createCoupon")
async def create_event_coupons(eventId: str, request: Request):
    try:
        # Get form data (includes both text fields and files)
        form_data = await request.form()

        # Separate normal data and file data from the form
        data = {}
        files = {}
        for key, value in form_data.multi_items():
            if isinstance(value, UploadFile):
                files[key] = value
            else:
                data[key] = value

        # Wrap Django ORM calls and form processing in a synchronous function
        @sync_to_async
        def process_create_coupon(eventId, data):
            # Fetch the event object or raise a 404 error if not found
            event = get_object_or_404(Event, eventId=eventId)

            # Instantiate the Django form with submitted data, file uploads, instance and partial flag.
            coupon_form = CouponCodeForm(data)

            if coupon_form.is_valid():
                # Create the new coupon code
                new_coupon = coupon_form.save(commit=False)
                new_coupon.event = event  # Associate the coupon with the event
                new_coupon.save()

                return {
                    "message": "Coupon created successfully.",
                    "code": str(new_coupon.code),
                    "eventId": str(event.eventId),
                    "discountPercentage": new_coupon.discountPercentage,
                }
            else:
                # Here we raise an error with the form errors so that we can return a 400 response.
                raise ValueError(coupon_form.errors)

        # Execute the create coupon function
        result = await process_create_coupon(eventId, data)
        return JSONResponse(content=result, status_code=status.HTTP_200_OK)

    except ValueError as ve:
        # Return any form validation errors
        return JSONResponse(
            content={"errors": str(ve), "message": "Failed to create coupon."},
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        # Log the exception details and return a server error
        traceback_str = traceback.format_exc()
        print(f"Create Event Coupons error: {str(e)}\n{traceback_str}")
        return JSONResponse(
            content={"error": f"An unexpected error occurred: {str(e)}"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

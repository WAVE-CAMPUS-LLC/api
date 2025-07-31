import os
import json
import traceback
from datetime import datetime
from pydantic import BaseModel
from typing import Optional, Dict, Any
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
    File,
)
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm

from channels.db import database_sync_to_async

from django.core.files.base import ContentFile
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse

from authenticationApp.models import CustomUser
from authenticationApp.serializers import CustomUserSerializer
from authenticationApp.forms import EmailPasswordResetForm
from django.contrib.auth import authenticate
from stripeManagementApp.customerSetup import CustomerAccount, ConnectAccount
from rest_framework_simplejwt.tokens import RefreshToken
from adminDashboardApp.models import LoginHistoryModel
from eventManagementApp.models import Event
from eventTicketsApp.models import Ticket
from accountManagementApp.models import UserProfile, UserPreferences
from accountManagementApp.serializers import UserProfileSerializer
from accountManagementApp.forms import (
    UpdateProfilePhotoForm,
    UpdatePersonalInfo,
    UpdateContactInfo,
    UserPreferencesForm,
)
from apiManager.utilities.form_fields import get_form_fields
from apiManager.dependencies import get_current_user
from apiManager.utilities.device_info import get_device_info
from apiManager.utilities.notify_by_bot import notify_by_bot
from .serializers import (
    ProfileOverview,
    TicketSerializer,
    UniversalQRResponse,
    UserTicketsResponse,
)


# Safe notification wrapper to prevent notification failures from breaking APIs
async def safe_notify_by_bot(
    message: str, platform: str, level: str = "ERROR", device_info: str = None
) -> None:
    """
    Safely send notification via bot with error handling to prevent API failures.
    If notification fails, it logs the error but doesn't throw an exception.
    """
    try:
        await notify_by_bot(message, platform, level, device_info)
    except Exception as notification_error:
        print(f"[safe_notify_by_bot] Failed to send notification: {notification_error}")
        # Don't re-raise the exception - just log and continue


router = APIRouter()


@router.get("/profileOverview")
async def profileOverview(
    request: Request,
    user_id: int = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    API endpoint to retrieve user profile overview
    """
    print(f"[profileOverview] Function called with user_id: {user_id}")

    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def get_profile_overview(user_id):
        try:
            print(
                f"[get_profile_overview] Attempting to retrieve user with id: {user_id}"
            )
            user = CustomUser.objects.get(id=user_id)
            print(f"[get_profile_overview] User found: {user.username}")

            try:
                user_profile = UserProfile.objects.get(user=user)
                print(
                    f"[get_profile_overview] UserProfile found for user: {user.username}"
                )
            except UserProfile.DoesNotExist:
                print(
                    f"[get_profile_overview] UserProfile not found for user: {user.username}, creating one..."
                )
                user_profile = UserProfile.objects.create(user=user)
                print(
                    f"[get_profile_overview] UserProfile created for user: {user.username}"
                )

            # Build the response with detailed logging
            profile_data = {
                "user_id": str(user.user_id),
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "profile_photo": (
                    user_profile.profile_photo.url
                    if user_profile.profile_photo
                    else None
                ),
                "college": (
                    user_profile.college.name if user_profile.college else None
                ),
                "is_campus_manager": user_profile.is_campus_manager,
                "was_host": user_profile.was_host,
                "date_joined": user.date_joined,
                "is_active": user.is_active,
            }

            # Log what we're returning for debugging
            print(f"[get_profile_overview] Profile data being returned:")
            for key, value in profile_data.items():
                print(f"  {key}: {value} (type: {type(value)})")

            return profile_data

        except CustomUser.DoesNotExist:
            print(
                f"[get_profile_overview] Error: User with id {user_id} does not exist"
            )
            return None
        except Exception as e:
            error_trace = traceback.format_exc()
            print(
                f"[get_profile_overview] Unexpected error retrieving profile for user_id {user_id}: {str(e)}\n{error_trace}"
            )
            return None

    try:
        profile_data = await get_profile_overview(user_id)
        if profile_data is None:
            await safe_notify_by_bot(
                f"**[API: profileOverview]** \n\n User not found: user_id={user_id} \n\n Platform: {platform}",
                platform or "Unknown",
                "ERROR",
                device_info,
            )
            raise HTTPException(status_code=404, detail="User not found")

        print(f"[profileOverview] Returning profile data: {profile_data}")
        return profile_data
    except Exception as e:
        if not isinstance(e, HTTPException):
            error_trace = traceback.format_exc()
            print(f"[profileOverview] Unhandled exception: {str(e)}\n{error_trace}")
            await safe_notify_by_bot(
                f"**[API: profileOverview]** \n\n Unhandled exception: user_id={user_id}, error={str(e)} \n\n Platform: {platform}",
                platform or "Unknown",
                "ERROR",
                device_info,
            )
            raise HTTPException(status_code=500, detail="Internal server error")
        raise e


@router.get("/profile/detailed")
async def profile_detailed(
    request: Request,
    user_id: int = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    API endpoint to retrieve detailed user profile information
    """
    print(f"[profile_detailed] Function called with user_id: {user_id}")

    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def get_profile_detailed(user_id):
        try:
            print(
                f"[get_profile_detailed] Attempting to retrieve user with id: {user_id}"
            )
            user = CustomUser.objects.get(id=user_id)
            print(f"[get_profile_detailed] User found: {user.username}")

            try:
                user_profile = UserProfile.objects.get(user=user)
                print(
                    f"[get_profile_detailed] UserProfile found for user: {user.username}"
                )
            except UserProfile.DoesNotExist:
                print(
                    f"[get_profile_detailed] UserProfile not found for user: {user.username}, creating one..."
                )
                user_profile = UserProfile.objects.create(user=user)
                print(
                    f"[get_profile_detailed] UserProfile created for user: {user.username}"
                )

            # Build the response with detailed logging
            profile_data = {
                "user_id": str(user.user_id),
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "profile_photo": (
                    user_profile.profile_photo.url
                    if user_profile.profile_photo
                    else None
                ),
                "college": (
                    user_profile.college.name if user_profile.college else None
                ),
                "is_campus_manager": user_profile.is_campus_manager,
                "was_host": user_profile.was_host,
                "date_joined": user.date_joined,
                "is_active": user.is_active,
            }

            # Log what we're returning for debugging
            print(f"[get_profile_detailed] Profile data being returned:")
            for key, value in profile_data.items():
                print(f"  {key}: {value} (type: {type(value)})")

            return profile_data

        except CustomUser.DoesNotExist:
            print(
                f"[get_profile_detailed] Error: User with id {user_id} does not exist"
            )
            return None
        except Exception as e:
            error_trace = traceback.format_exc()
            print(
                f"[get_profile_detailed] Unexpected error retrieving profile for user_id {user_id}: {str(e)}\n{error_trace}"
            )
            return None

    try:
        profile_data = await get_profile_detailed(user_id)
        if profile_data is None:
            await safe_notify_by_bot(
                f"**[API: profile_detailed]** \n\n User not found: user_id={user_id} \n\n Platform: {platform}",
                platform or "Unknown",
                "ERROR",
                device_info,
            )
            raise HTTPException(status_code=404, detail="User not found")
        print(f"[profile_detailed] Returning profile data: {profile_data}")
        return profile_data
    except Exception as e:
        if not isinstance(e, HTTPException):
            error_trace = traceback.format_exc()
            print(f"[profile_detailed] Unhandled exception: {str(e)}\n{error_trace}")
            await safe_notify_by_bot(
                f"**[API: profile_detailed]** \n\n Unhandled exception: user_id={user_id}, error={str(e)} \n\n Platform: {platform}",
                platform or "Unknown",
                "ERROR",
                device_info,
            )
            raise HTTPException(status_code=500, detail="Internal server error")
        raise e


@router.post("/profile/detailed")
async def update_profile_detailed(
    request: Request,
    user_id: int = Depends(get_current_user),
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    profile_photo: Optional[UploadFile] = File(None),
    platform: Optional[str] = None,
):
    """
    API endpoint to update user profile information
    """
    print(f"[update_profile_detailed] Function called with user_id: {user_id}")

    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def update_profile_detailed(user_id, first_name, last_name, email, profile_photo):
        try:
            user = CustomUser.objects.get(id=user_id)
            user_profile = UserProfile.objects.get(user=user)

            # Update user fields
            user.first_name = first_name
            user.last_name = last_name
            user.email = email
            user.save()

            # Update profile photo if provided
            if profile_photo:
                user_profile.profile_photo.save(
                    profile_photo.filename, ContentFile(profile_photo.file.read())
                )

            user_profile.save()
            return True
        except CustomUser.DoesNotExist:
            print(
                f"[update_profile_detailed] Error: User with id {user_id} does not exist"
            )
            return False
        except Exception as e:
            error_trace = traceback.format_exc()
            print(
                f"[update_profile_detailed] Unexpected error updating profile for user_id {user_id}: {str(e)}\n{error_trace}"
            )
            return False

    success = await update_profile_detailed(
        user_id, first_name, last_name, email, profile_photo
    )
    if not success:
        await safe_notify_by_bot(
            f"**[API: update_profile_detailed]** \n\n User not found: user_id={user_id} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(status_code=404, detail="User not found")

    print(
        f"[update_profile_detailed] Profile updated successfully for user_id: {user_id}"
    )
    return {"message": "Profile updated successfully"}


@router.get("/getUserTickets")
async def get_user_tickets(
    request: Request,
    user_id: int = Depends(get_current_user),
    platform: Optional[str] = None,
):
    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    print(f"[get_user_tickets] API called with user_id: {user_id}")

    try:

        @database_sync_to_async
        def get_user_tickets_async(user_id):
            print(f"[get_user_tickets_async] Retrieving tickets for user_id: {user_id}")
            user = CustomUser.objects.get(id=user_id)

            # Optimize query with select_related for event data
            tickets = (
                Ticket.objects.select_related("event")
                .filter(user=user)
                .order_by("-created_at")
            )
            print(f"[get_user_tickets_async] Found {tickets.count()} tickets")

            ticket_list = []
            for ticket in tickets:
                # Default location dictionary with all required fields
                default_location = {
                    "address": "",
                    "city": "",
                    "state": "",
                    "zip_code": "",
                    "country": "",
                }

                # Get event location if available, otherwise use default
                location_data = default_location
                if hasattr(ticket.event, "location") and ticket.event.location:
                    # If location is a dictionary, update default values with available ones
                    if isinstance(ticket.event.location, dict):
                        location_data = {**default_location, **ticket.event.location}
                    # If location is a string or other object, put it in the address field
                    elif ticket.event.location:
                        location_data["address"] = str(ticket.event.location)

                # Create serializable event object
                event_obj = {
                    "eventId": str(ticket.event.eventId),
                    "title": ticket.event.title,
                    "date": ticket.event.date,
                    "start_time": ticket.event.start_time,
                    "end_time": ticket.event.end_time,
                    "header_photo": (
                        ticket.event.header_photo.url
                        if ticket.event.header_photo
                        else None
                    ),
                    "description": (getattr(ticket.event, "description", None)),
                    "location": location_data,
                }

                # Get individual ticket QR code information
                qr_code_image_url = None
                qr_code_data = None
                if ticket.qrCodeImage:
                    qr_code_image_url = ticket.qrCodeImage.url
                if ticket.qrCodeData:
                    qr_code_data = ticket.qrCodeData

                ticket_list.append(
                    {
                        "ticketId": str(ticket.ticketId),
                        "guestFirstName": ticket.guestFirstName,
                        "guestLastName": ticket.guestLastName,
                        "event": event_obj,  # Include the complete event object
                        "guestEmail": ticket.guestEmail,
                        "eventId": str(ticket.event.eventId),
                        "eventTitle": ticket.event.title,
                        "date": ticket.event.date,
                        "header_photo": (
                            ticket.event.header_photo.url
                            if ticket.event.header_photo
                            else None
                        ),
                        # Individual ticket QR code fields (separate ticket system)
                        "qrCodeImage": qr_code_image_url,
                        "qrCodeData": qr_code_data,
                        "status": ticket.status,
                        "eventDate": ticket.event.date,
                        "eventStartTime": ticket.event.start_time,
                        "eventEndTime": ticket.event.end_time,
                        "created_at": ticket.created_at,
                        "stripe_session_id": ticket.stripe_session_id,
                    }
                )

            return ticket_list

        ticket_data = await get_user_tickets_async(user_id)

        # Serialize tickets with better error handling
        try:
            tickets = [TicketSerializer(**ticket) for ticket in ticket_data]
            print(f"[get_user_tickets] Successfully serialized {len(tickets)} tickets")
        except Exception as serialization_error:
            print(f"[get_user_tickets] Serialization error: {serialization_error}")
            print(
                f"[get_user_tickets] Sample ticket data: {ticket_data[0] if ticket_data else 'No tickets'}"
            )
            raise Exception(f"Ticket serialization failed: {serialization_error}")

        print(f"[get_user_tickets] Returning {len(tickets)} serialized tickets")
        return {"tickets": tickets}
    except Exception as e:
        await safe_notify_by_bot(
            f"**[API: get_user_tickets]** \n\n Error fetching user tickets: user_id={user_id}, error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(
            status_code=500, detail=f"Error fetching user tickets: {str(e)}"
        )


@router.get("/getUserTickets/{ticketId}/details")
async def get_user_ticket_details(
    ticketId: str,
    request: Request,
    user_id: int = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    API endpoint for getting user ticket details.
    Returns details of a specific ticket belonging to the authenticated user.
    Uses individual ticket QR code system.
    """
    print(
        f"[get_user_ticket_details] API called with ticketId: {ticketId}, user_id: {user_id}"
    )

    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:

        @database_sync_to_async
        def get_user_ticket_details_async(ticketId, user_id):
            print(
                f"[get_user_ticket_details_async] Retrieving ticket details for ticketId: {ticketId}, user_id: {user_id}"
            )
            user = CustomUser.objects.get(id=user_id)
            try:
                # Optimize query with select_related for event data
                ticket = Ticket.objects.select_related("event").get(
                    ticketId=ticketId, user=user
                )
                print(
                    f"[get_user_ticket_details_async] Found ticket with ID: {ticketId}"
                )

                # Get individual ticket QR code information (separate ticket system)
                qr_code_image_url = None
                qr_code_data = None
                if ticket.qrCodeImage:
                    qr_code_image_url = ticket.qrCodeImage.url
                if ticket.qrCodeData:
                    qr_code_data = ticket.qrCodeData

                # Default location dictionary with all required fields
                default_location = {
                    "address": "",
                    "city": "",
                    "state": "",
                    "zip_code": "",
                    "country": "",
                }

                # Get event location if available, otherwise use default
                location_data = default_location
                if hasattr(ticket.event, "location") and ticket.event.location:
                    # If location is a dictionary, update default values with available ones
                    if isinstance(ticket.event.location, dict):
                        location_data = {**default_location, **ticket.event.location}
                    # If location is a string or other object, put it in the address field
                    elif ticket.event.location:
                        location_data["address"] = str(ticket.event.location)

                return {
                    "ticketId": str(ticket.ticketId),
                    "guestFirstName": ticket.guestFirstName,
                    "guestLastName": ticket.guestLastName,
                    "guestEmail": ticket.guestEmail,
                    "eventId": str(ticket.event.eventId),
                    "eventTitle": ticket.event.title,
                    "date": ticket.event.date,
                    "header_photo": (
                        ticket.event.header_photo.url
                        if ticket.event.header_photo
                        else None
                    ),
                    "description": getattr(ticket.event, "description", None),
                    "location": location_data,
                    "start_time": ticket.event.start_time,
                    "end_time": ticket.event.end_time,
                    # Individual ticket QR code fields (separate ticket system)
                    "qrCodeImage": qr_code_image_url,
                    "qrCodeData": qr_code_data,
                    "status": ticket.status,
                    "created_at": ticket.created_at,
                    "stripe_session_id": ticket.stripe_session_id,
                    "mainId": str(ticket.mainId),
                }

            except Ticket.DoesNotExist:
                return None

        ticket_data = await get_user_ticket_details_async(ticketId, user_id)
        if ticket_data is None:
            print(
                f"[get_user_ticket_details] Error: Ticket not found for ticketId: {ticketId}, user_id: {user_id}"
            )
            raise HTTPException(status_code=404, detail="Ticket not found")

        print(
            f"[get_user_ticket_details] Returning ticket data for ticketId: {ticketId}"
        )
        return ticket_data
    except Exception as e:
        await safe_notify_by_bot(
            f"**[API: get_user_ticket_details]** \n\n Error fetching ticket details: ticketId={ticketId}, user_id={user_id}, error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(
            status_code=500, detail=f"Error fetching ticket details: {str(e)}"
        )


@router.get("/profile/favoriteEvents")
async def favoriteEvents(
    request: Request,
    user_id: int = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    API endpoint for getting profile overview.
    Returns user profile data.
    """
    print(f"[favoriteEvents] API called with user_id: {user_id}")

    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:

        @database_sync_to_async
        def get_fav_events(user_id):
            try:
                print(
                    f"[get_fav_events] Retrieving favorite events for user_id: {user_id}"
                )
                user = CustomUser.objects.get(id=user_id)
                user_profile = UserProfile.objects.get(user=user)
                events = user_profile.favorite_events.all()
                print(f"[get_fav_events] Found {events.count()} favorite events")
                event_data = [
                    {
                        "eventId": event.eventId,
                        "title": event.title,
                        "date": event.date,
                        "header_photo": (
                            event.header_photo.url if event.header_photo else None
                        ),
                    }
                    for event in events
                ]
                return event_data
            except CustomUser.DoesNotExist or UserProfile.DoesNotExist:
                return None

        events_data = await get_fav_events(user_id)
        if events_data is None:
            print(f"[favoriteEvents] Error: User not found for user_id: {user_id}")
            raise HTTPException(status_code=404, detail="Event not found")
        print(
            f"[favoriteEvents] Returning {len(events_data)} favorite events for user_id: {user_id}"
        )
        return events_data
    except Exception as e:
        await safe_notify_by_bot(
            f"**[API: favoriteEvents]** \n\n Error fetching favorite events: user_id={user_id}, error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(
            status_code=500, detail=f"Error fetching favorite events: {str(e)}"
        )


@router.post("/profile/delete")
async def delete_profile(
    request: Request,
    user_id: int = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    API endpoint for deleting a user profile.
    Deletes the user profile and associated data.
    """
    print(f"[delete_profile] API called with user_id: {user_id}")

    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:

        @database_sync_to_async
        def delete_profile(user_id):
            try:
                print(f"[delete_profile] Deleting user with user_id: {user_id}")
                user = CustomUser.objects.get(id=user_id)
                user.delete()
                print(f"[delete_profile] User deleted successfully")
                return True
            except CustomUser.DoesNotExist:
                return False

        success = await delete_profile(user_id)
        if not success:
            print(f"[delete_profile] Error: User not found for user_id: {user_id}")
            raise HTTPException(status_code=404, detail="User not found")

        print(f"[delete_profile] Profile deleted successfully for user_id: {user_id}")
        return {"message": "Profile deleted successfully"}
    except Exception as e:
        await safe_notify_by_bot(
            f"**[API: delete_profile]** \n\n Error deleting profile: user_id={user_id}, error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(status_code=500, detail=f"Error deleting profile: {str(e)}")


@router.post("/profile/delete-with-reason")
async def delete_account_with_reason(
    request: Request,
    user_id: int = Depends(get_current_user),
    reason: str = Form(...),
    platform: Optional[str] = None,
):
    """
    API endpoint for deleting a user account with a reason.
    Saves the deletion reason and then deletes the user account.
    """
    print(f"[delete_account_with_reason] API called with user_id: {user_id}")

    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:

        @database_sync_to_async
        def delete_account_with_reason_sync(user_id, reason, platform, user_agent_str):
            try:
                print(
                    f"[delete_account_with_reason_sync] Processing deletion for user_id: {user_id}"
                )

                # Get user details before deletion
                user = CustomUser.objects.get(id=user_id)
                user_email = user.email
                username = user.username
                str_user_id = str(user.user_id)

                print(
                    f"[delete_account_with_reason_sync] User found: {username} ({user_email})"
                )

                # Import the AccountDeletionReason model
                from accountManagementApp.models import AccountDeletionReason

                # Save the deletion reason before deleting the user
                deletion_record = AccountDeletionReason.objects.create(
                    user_email=user_email,
                    username=username,
                    user_id=str_user_id,
                    reason=reason,
                    platform=platform or "Unknown",
                    user_agent=user_agent_str,
                )

                print(
                    f"[delete_account_with_reason_sync] Deletion reason saved with ID: {deletion_record.id}"
                )

                # Delete the user account
                user.delete()

                print(
                    f"[delete_account_with_reason_sync] User account deleted successfully"
                )

                return {
                    "success": True,
                    "deletion_record_id": deletion_record.id,
                    "message": "Account deleted successfully",
                }

            except CustomUser.DoesNotExist:
                print(
                    f"[delete_account_with_reason_sync] Error: User with id {user_id} does not exist"
                )
                return {"success": False, "error": "User not found"}
            except Exception as e:
                import traceback

                error_trace = traceback.format_exc()
                print(
                    f"[delete_account_with_reason_sync] Unexpected error: {str(e)}\n{error_trace}"
                )
                return {"success": False, "error": f"Unexpected error: {str(e)}"}

        # Validate reason input
        if not reason or len(reason.strip()) == 0:
            raise HTTPException(status_code=400, detail="Deletion reason is required")

        if len(reason) > 1000:  # Reasonable limit for reason length
            raise HTTPException(
                status_code=400,
                detail="Deletion reason is too long (max 1000 characters)",
            )

        result = await delete_account_with_reason_sync(
            user_id, reason.strip(), platform, user_agent_str
        )

        if not result["success"]:
            if "User not found" in result.get("error", ""):
                raise HTTPException(status_code=404, detail="User not found")
            else:
                await safe_notify_by_bot(
                    f"**[API: delete_account_with_reason]** \n\n Error deleting account: user_id={user_id}, error={result.get('error')} \n\n Platform: {platform}",
                    platform or "Unknown",
                    "ERROR",
                    device_info,
                )
                raise HTTPException(
                    status_code=500,
                    detail=f"Error deleting account: {result.get('error')}",
                )

        print(
            f"[delete_account_with_reason] Account deleted successfully for user_id: {user_id}"
        )

        # Notify about account deletion (optional - you may want to track this)
        await safe_notify_by_bot(
            f"**[Account Deletion]** \n\n User account deleted: user_id={user_id}, reason: {reason[:100]}{'...' if len(reason) > 100 else ''} \n\n Platform: {platform}",
            platform or "Unknown",
            "INFO",
            device_info,
        )

        return {
            "message": "Account deleted successfully",
            "deletion_record_id": result["deletion_record_id"],
        }

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        import traceback

        error_trace = traceback.format_exc()
        print(
            f"[delete_account_with_reason] Unhandled exception: {str(e)}\n{error_trace}"
        )
        await safe_notify_by_bot(
            f"**[API: delete_account_with_reason]** \n\n Unhandled exception: user_id={user_id}, error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/getUserTransactions")
async def get_user_transactions(
    request: Request,
    user_id: int = Depends(get_current_user),
    platform: Optional[str] = None,
):
    print(f"[get_user_transactions] API called with user_id: {user_id}")

    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:

        @database_sync_to_async
        def get_user_transactions(user_id):
            try:
                user = CustomUser.objects.get(id=user_id)
                if not user.customer_id:
                    existing_customer = CustomerAccount.searchCustomerAccount(
                        user.email
                    )
                    if existing_customer:
                        user.customer_id = existing_customer.id
                        user.save()
                        print(
                            f"[get_user_transactions] Customer ID updated for user_id: {user_id}"
                        )
                    else:
                        # Pass None for request if needed
                        new_customer = CustomerAccount.createCustomerAccount(
                            None, user.email, user.first_name, user.last_name
                        )
                        if new_customer:
                            user.customer_id = new_customer.id
                            user.save()
                            print(
                                f"[get_user_transactions] New customer created for user_id: {user_id}"
                            )
                        else:
                            print(
                                f"[get_user_transactions] Error: Unable to create customer account for user_id: {user_id}"
                            )
                            return None
                # Use the same logic as in customerSetup.py: getCustomerTransactions
                # Since we don't have a Django request object, pass None
                transactions = CustomerAccount.getCustomerTransactions(
                    None, user.customer_id
                )
                print(
                    f"[get_user_transactions] Found {len(transactions)} transactions for user_id: {user_id}"
                )
                transaction_list = []
                for transaction in transactions:
                    # transaction is a dict, not an object
                    transaction_list.append(
                        {
                            "transactionId": transaction.get("id"),
                            "amount": transaction.get("amount"),
                            "currency": transaction.get("currency"),
                            "description": transaction.get("description"),
                            "created_at": transaction.get("created"),
                            "receipt_url": transaction.get("receipt_url"),
                            "status": transaction.get("status"),
                        }
                    )
                return transaction_list
            except CustomUser.DoesNotExist:
                return None

        transactions_data = await get_user_transactions(user_id)
        if transactions_data is None:
            print(
                f"[get_user_transactions] Error: User not found for user_id: {user_id}"
            )
            raise HTTPException(status_code=404, detail="User not found")
        print(
            f"[get_user_transactions] Returning {len(transactions_data)} transactions for user_id: {user_id}"
        )
        return transactions_data
    except Exception as e:
        await safe_notify_by_bot(
            f"**[API: get_user_transactions]** \n\n Error fetching user transactions: user_id={user_id}, error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(
            status_code=500, detail=f"Error fetching user transactions: {str(e)}"
        )


@router.get("/getUserPaymentMethods")
async def get_user_payment_methods(
    request: Request,
    user_id: int = Depends(get_current_user),
    platform: Optional[str] = None,
):
    print(f"[get_user_payment_methods] API called with user_id: {user_id}")

    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:

        @database_sync_to_async
        def get_user_payment_methods_sync(user_id):
            try:
                user = CustomUser.objects.get(id=user_id)
                # Stripe customer setup logic (from profileView)
                if not user.customer_id:
                    existing_customer = CustomerAccount.searchCustomerAccount(
                        user.email
                    )
                    if existing_customer:
                        user.customer_id = existing_customer.id
                        user.save()
                        print(
                            f"[get_user_payment_methods] Found existing Stripe customer: {existing_customer.id}"
                        )
                    else:
                        new_customer = CustomerAccount.createCustomerAccount(
                            None, user.email, user.first_name, user.last_name
                        )
                        if new_customer:
                            user.customer_id = new_customer.id
                            user.save()
                            print(
                                f"[get_user_payment_methods] Created new Stripe customer: {new_customer.id}"
                            )
                        else:
                            print(
                                "[get_user_payment_methods] Failed to create Stripe customer"
                            )
                            return None

                payment_methods = CustomerAccount.listPaymentMethods(user.customer_id)
                if payment_methods:
                    for method in payment_methods:
                        # Convert exp_month to month name (e.g., 5 -> May)
                        try:
                            method["exp_month"] = datetime.strptime(
                                str(method["exp_month"]), "%m"
                            ).strftime("%B")
                        except Exception:
                            pass
                    return payment_methods
                else:
                    return []
            except CustomUser.DoesNotExist:
                print(
                    f"[get_user_payment_methods] Error: User with id {user_id} does not exist"
                )
                return None
            except Exception as e:
                print(f"[get_user_payment_methods] Unexpected error: {str(e)}")
                return None

        payment_methods_data = await get_user_payment_methods_sync(user_id)
        if payment_methods_data is None:
            print(
                f"[get_user_payment_methods] Error: User not found for user_id: {user_id}"
            )
            raise HTTPException(status_code=404, detail="User not found")
        print(
            f"[get_user_payment_methods] Returning {len(payment_methods_data)} payment methods for user_id: {user_id}"
        )
        return payment_methods_data
    except Exception as e:
        await safe_notify_by_bot(
            f"**[API: get_user_payment_methods]** \n\n Error fetching payment methods: user_id={user_id}, error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(
            status_code=500, detail=f"Error fetching payment methods: {str(e)}"
        )


@router.post("/payment/deletePaymentMethod")
async def delete_payment_method(
    request: Request,
    user_id: int = Depends(get_current_user),
    paymentMethodId: str = Body(..., embed=True),
    platform: Optional[str] = None,
):
    """Delete a payment method for the current user."""

    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:

        @database_sync_to_async
        def get_user(user_id):
            return CustomUser.objects.get(id=user_id)

        user = await get_user(user_id)
        if paymentMethodId:
            CustomerAccount.removePaymentMethod(None, paymentMethodId)
            return {"success": True, "message": "Payment method deleted successfully."}
        else:
            raise HTTPException(status_code=400, detail="Invalid payment method ID.")
    except Exception as e:
        await safe_notify_by_bot(
            f"**[API: delete_payment_method]** \n\n Error deleting payment method: user_id={user_id}, paymentMethodId={paymentMethodId}, error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(
            status_code=500, detail=f"Error deleting payment method: {str(e)}"
        )


@router.post("/payment/setDefaultPaymentMethod")
async def set_default_payment_method(
    request: Request,
    user_id: int = Depends(get_current_user),
    paymentMethodId: str = Body(..., embed=True),
    platform: Optional[str] = None,
):
    """Set a default payment method for the current user."""

    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:

        @database_sync_to_async
        def get_user(user_id):
            return CustomUser.objects.get(id=user_id)

        user = await get_user(user_id)
        if paymentMethodId:
            success = CustomerAccount.setDefaultPaymentMethod(
                user.customer_id, paymentMethodId
            )
            if success:
                return {
                    "success": True,
                    "message": "Default payment method set successfully.",
                }
            else:
                raise HTTPException(
                    status_code=400, detail="Failed to set default payment method."
                )
        else:
            raise HTTPException(status_code=400, detail="Invalid payment method ID.")
    except Exception as e:
        await safe_notify_by_bot(
            f"**[API: set_default_payment_method]** \n\n Error setting default payment method: user_id={user_id}, paymentMethodId={paymentMethodId}, error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(
            status_code=500, detail=f"Error setting default payment method: {str(e)}"
        )


@router.post("/payment/addPayoutMethodToProfile")
async def add_payout_method_to_profile(
    request: Request,
    user_id: int = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """Add a payout (bank) method to the user's profile."""

    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:

        @database_sync_to_async
        def get_user(user_id):
            return CustomUser.objects.get(id=user_id)

        user = await get_user(user_id)
        bank = CustomerAccount.setupBankAccount(None, user.customer_id)
        if bank:
            return {"success": True, "message": "Bank account added successfully."}
        else:
            raise HTTPException(status_code=400, detail="Failed to add bank account.")
    except Exception as e:
        await safe_notify_by_bot(
            f"**[API: add_payout_method_to_profile]** \n\n Error adding payout method: user_id={user_id}, error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(
            status_code=500, detail=f"Error adding payout method: {str(e)}"
        )


@router.post("/payment/requestInstantPayout")
async def request_instant_payout(
    request: Request,
    user_id: int = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """Request an instant payout for the user if eligible."""

    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:

        @database_sync_to_async
        def get_user(user_id):
            return CustomUser.objects.get(id=user_id)

        user = await get_user(user_id)
        from stripeManagementApp.getEarnings import GetEarnings

        accountBalance = GetEarnings.getStripeAccountBalance(user.connectAccountID)
        if not accountBalance:
            raise HTTPException(
                status_code=400, detail="Could not retrieve account balance."
            )
        available_balance = accountBalance.get("available", 0)
        if available_balance < 1:
            raise HTTPException(
                status_code=400, detail="Insufficient balance for a payout."
            )
        payout = GetEarnings.requestPayout(
            user.connectAccountID, int(available_balance * 100)
        )
        if payout:
            return {"success": True, "message": "Payout requested successfully."}
        else:
            raise HTTPException(status_code=400, detail="Failed to process payout.")
    except Exception as e:
        await safe_notify_by_bot(
            f"**[API: request_instant_payout]** \n\n Error requesting instant payout: user_id={user_id}, error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(
            status_code=500, detail=f"Error requesting instant payout: {str(e)}"
        )


@router.get("/checkHost")
async def check_host(
    request: Request,
    user_id: int = Depends(get_current_user),
    platform: Optional[str] = None,
):
    print(f"[check_host] API called with user_id: {user_id}")

    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:

        @database_sync_to_async
        def check_user_is_host(user_id):
            try:
                print(f"[check_user_is_host] Checking if user_id: {user_id} is a host")
                user = CustomUser.objects.get(id=user_id)
                is_host = user.groups.filter(name="Host").exists()
                print(f"[check_user_is_host] User is host: {is_host}")
                return {"is_host": is_host}
            except CustomUser.DoesNotExist:
                return None

        result = await check_user_is_host(user_id)
        if result is None:
            print(f"[check_host] Error: User not found for user_id: {user_id}")
            raise HTTPException(status_code=404, detail="User not found")
        print(f"[check_host] Returning host status for user_id: {user_id}: {result}")
        return result
    except Exception as e:
        await safe_notify_by_bot(
            f"**[API: check_host]** \n\n Error checking host status: user_id={user_id}, error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(
            status_code=500, detail=f"Error checking host status: {str(e)}"
        )


@router.get("/getHostDashboardLink")
async def get_host_dashboard_link(
    request: Request,
    user_id: int = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    API endpoint for getting Stripe dashboard link for hosts.
    Returns a link to the Stripe dashboard for the user's connected account.
    """
    print(f"[get_host_dashboard_link] API called with user_id: {user_id}")

    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:

        @database_sync_to_async
        def get_host_stripe_link(user_id):
            try:
                print(
                    f"[get_host_stripe_link] Retrieving Stripe dashboard link for user_id: {user_id}"
                )
                user = CustomUser.objects.get(id=user_id)

                # Check if stripe account ID exists
                if not user.connectAccountID:
                    print(
                        f"[get_host_stripe_link] No connectAccountID found for user_id: {user_id}"
                    )
                    return {
                        "error": "You aren't a host yet. Host your first event to get started."
                    }, 400

                # Import stripe here to avoid loading it unnecessarily
                import stripe
                from django.conf import settings

                stripe.api_key = settings.STRIPE_SECRET_KEY

                # Create the stripe login link
                try:
                    stripe_login_link = stripe.Account.create_login_link(
                        user.connectAccountID
                    )
                    return {"url": stripe_login_link.url}, 200
                except Exception as e:
                    print(f"Stripe error: {str(e)}")
                    return {
                        "error": f"Failed to get Stripe account link: {str(e)}"
                    }, 400

            except CustomUser.DoesNotExist:
                return None

        result, status_code = await get_host_stripe_link(user_id)
        if result is None:
            print(
                f"[get_host_dashboard_link] Error: User not found for user_id: {user_id}"
            )
            raise HTTPException(status_code=404, detail="User not found")

        if status_code != 200:
            print(
                f"[get_host_dashboard_link] Error: {result.get('error')} for user_id: {user_id}"
            )
            raise HTTPException(status_code=status_code, detail=result.get("error"))

        print(
            f"[get_host_dashboard_link] Returning dashboard link for user_id: {user_id}"
        )
        return result
    except Exception as e:
        await safe_notify_by_bot(
            f"**[API: get_host_dashboard_link]** \n\n Error getting host dashboard link: user_id={user_id}, error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(
            status_code=500, detail=f"Error getting host dashboard link: {str(e)}"
        )


@router.get("/getUserCollege")
async def get_user_college(
    request: Request,
    user_id: int = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    API endpoint for getting user's college information.
    Returns the college name and ID associated with the user.
    """
    print(f"[get_user_college] API called with user_id: {user_id}")

    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:

        @database_sync_to_async
        def get_user_college(user_id):
            try:
                print(
                    f"[get_user_college] Retrieving college info for user_id: {user_id}"
                )
                user = CustomUser.objects.get(id=user_id)
                college = user.user_profile.college
                print(f"[get_user_college] College found: {college is not None}")
                if college:
                    return {
                        "collegeId": str(college.collegeId),
                        "collegeName": college.name,
                    }
                else:
                    return None
            except CustomUser.DoesNotExist:
                return None

        college_data = await get_user_college(user_id)
        if college_data is None:
            print(
                f"[get_user_college] Error: User or college not found for user_id: {user_id}"
            )
            raise HTTPException(status_code=404, detail="User not found")

        print(
            f"[get_user_college] Returning college data for user_id: {user_id}: {college_data}"
        )
        return college_data
    except Exception as e:
        await safe_notify_by_bot(
            f"**[API: get_user_college]** \n\n Error fetching user college: user_id={user_id}, error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(
            status_code=500, detail=f"Error fetching user college: {str(e)}"
        )


@router.get("/editProfile")
async def get_edit_fields(
    request: Request,
    user_id: int = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    API endpoint for retrieving editable profile fields.
    Returns user profile data that can be edited.
    """
    print(f"[get_edit_fields] API called with user_id: {user_id}")

    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def get_edit_profile_data(user_id):
        try:
            print(
                f"[get_edit_profile_data] Retrieving editable profile data for user_id: {user_id}"
            )
            user = CustomUser.objects.get(id=user_id)

            try:
                user_profile = UserProfile.objects.get(user=user)
                print(
                    f"[get_edit_profile_data] UserProfile found for user: {user.username}"
                )
            except UserProfile.DoesNotExist:
                print(
                    f"[get_edit_profile_data] UserProfile not found for user: {user.username}, creating one..."
                )
                user_profile = UserProfile.objects.create(user=user)
                print(
                    f"[get_edit_profile_data] UserProfile created for user: {user.username}"
                )

            # Build editable profile data
            profile_data = {
                "user_id": str(user.user_id),
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "profile_photo": (
                    user_profile.profile_photo.url
                    if user_profile.profile_photo
                    else None
                ),
            }

            print(f"[get_edit_profile_data] Profile data prepared successfully")
            return profile_data

        except CustomUser.DoesNotExist:
            print(
                f"[get_edit_profile_data] Error: User with id {user_id} does not exist"
            )
            return None
        except Exception as e:
            error_trace = traceback.format_exc()
            print(
                f"[get_edit_profile_data] Unexpected error retrieving editable profile for user_id {user_id}: {str(e)}\n{error_trace}"
            )
            return None

    try:
        profile_data = await get_edit_profile_data(user_id)
        if profile_data is None:
            await safe_notify_by_bot(
                f"**[API: get_edit_fields]** \n\n User not found: user_id={user_id} \n\n Platform: {platform}",
                platform or "Unknown",
                "ERROR",
                device_info,
            )
            raise HTTPException(status_code=404, detail="User not found")

        print(f"[get_edit_fields] Returning editable profile data: {profile_data}")
        return profile_data
    except Exception as e:
        if not isinstance(e, HTTPException):
            error_trace = traceback.format_exc()
            print(f"[get_edit_fields] Unhandled exception: {str(e)}\n{error_trace}")
            await safe_notify_by_bot(
                f"**[API: get_edit_fields]** \n\n Unhandled exception: user_id={user_id}, error={str(e)} \n\n Platform: {platform}",
                platform or "Unknown",
                "ERROR",
                device_info,
            )
            raise HTTPException(status_code=500, detail="Internal server error")
        raise e


@router.post("/editProfile")
async def update_edit_fields(
    request: Request,
    user_id: int = Depends(get_current_user),
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    profile_photo: Optional[UploadFile] = File(None),
    platform: Optional[str] = None,
):
    """
    API endpoint for updating editable profile fields.
    Updates user profile data with the provided information.
    """
    print(f"[update_edit_fields] API called with user_id: {user_id}")

    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def update_profile_data(user_id, first_name, last_name, email, profile_photo):
        try:
            print(f"[update_profile_data] Updating profile for user_id: {user_id}")
            user = CustomUser.objects.get(id=user_id)

            try:
                user_profile = UserProfile.objects.get(user=user)
                print(
                    f"[update_profile_data] UserProfile found for user: {user.username}"
                )
            except UserProfile.DoesNotExist:
                print(
                    f"[update_profile_data] UserProfile not found for user: {user.username}, creating one..."
                )
                user_profile = UserProfile.objects.create(user=user)
                print(
                    f"[update_profile_data] UserProfile created for user: {user.username}"
                )

            # Update user fields
            user.first_name = first_name
            user.last_name = last_name
            user.email = email
            user.save()
            print(f"[update_profile_data] User basic info updated successfully")

            # Update profile photo if provided
            if profile_photo:
                user_profile.profile_photo.save(
                    profile_photo.filename, ContentFile(profile_photo.file.read())
                )
                print(f"[update_profile_data] Profile photo updated successfully")

            user_profile.save()

            # Return updated profile data
            updated_profile_data = {
                "user_id": str(user.user_id),
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "profile_photo": (
                    user_profile.profile_photo.url
                    if user_profile.profile_photo
                    else None
                ),
            }

            print(f"[update_profile_data] Profile updated successfully")
            return updated_profile_data

        except CustomUser.DoesNotExist:
            print(f"[update_profile_data] Error: User with id {user_id} does not exist")
            return None
        except Exception as e:
            error_trace = traceback.format_exc()
            print(
                f"[update_profile_data] Unexpected error updating profile for user_id {user_id}: {str(e)}\n{error_trace}"
            )
            return None

    try:
        # Validate input data
        if not first_name or len(first_name.strip()) == 0:
            raise HTTPException(status_code=400, detail="First name is required")

        if not last_name or len(last_name.strip()) == 0:
            raise HTTPException(status_code=400, detail="Last name is required")

        if not email or len(email.strip()) == 0:
            raise HTTPException(status_code=400, detail="Email is required")

        # Basic email validation
        import re

        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, email):
            raise HTTPException(status_code=400, detail="Invalid email format")

        profile_data = await update_profile_data(
            user_id, first_name.strip(), last_name.strip(), email.strip(), profile_photo
        )

        if profile_data is None:
            await safe_notify_by_bot(
                f"**[API: update_edit_fields]** \n\n User not found: user_id={user_id} \n\n Platform: {platform}",
                platform or "Unknown",
                "ERROR",
                device_info,
            )
            raise HTTPException(status_code=404, detail="User not found")

        print(
            f"[update_edit_fields] Profile updated successfully for user_id: {user_id}"
        )

        # Notify about profile update (optional)
        await safe_notify_by_bot(
            f"**[Profile Update]** \n\n User profile updated: user_id={user_id}, email={email} \n\n Platform: {platform}",
            platform or "Unknown",
            "INFO",
            device_info,
        )

        return {"message": "Profile updated successfully", "profile": profile_data}

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"[update_edit_fields] Unhandled exception: {str(e)}\n{error_trace}")
        await safe_notify_by_bot(
            f"**[API: update_edit_fields]** \n\n Unhandled exception: user_id={user_id}, error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/settings")
async def get_user_settings(
    request: Request,
    user_id: int = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    API endpoint for retrieving user settings and profile information.
    Returns user profile data and settings.
    """
    print(f"[get_user_settings] API called with user_id: {user_id}")

    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def get_settings_async(user_id):
        try:
            print(
                f"[get_settings_async] Retrieving user settings for user_id: {user_id}"
            )
            user = CustomUser.objects.get(id=user_id)
            profile = get_object_or_404(UserProfile, user=user)

            user_serializer = CustomUserSerializer(user)
            profile_serializer = UserProfileSerializer(profile)
            print(f"[get_settings_async] User and profile data serialized successfully")

            return {
                "user": user_serializer.data,
                "profile": profile_serializer.data,
            }
        except CustomUser.DoesNotExist:
            return None
        except Exception as e:
            error_trace = traceback.format_exc()
            print(
                f"[get_user_settings] Unexpected error retrieving settings for user_id {user_id}: {str(e)}\n{error_trace}"
            )
            return None

    try:
        settings_data = await get_settings_async(user_id)
        if settings_data is None:
            await safe_notify_by_bot(
                f"**[API: get_user_settings]** \n\n User not found: user_id={user_id} \n\n Platform: {platform}",
                platform or "Unknown",
                "ERROR",
                device_info,
            )
            raise HTTPException(status_code=404, detail="User not found")
        return settings_data
    except Exception as e:
        if not isinstance(e, HTTPException):
            error_trace = traceback.format_exc()
            print(f"[get_user_settings] Unhandled exception: {str(e)}\n{error_trace}")
            await safe_notify_by_bot(
                f"**[API: get_user_settings]** \n\n Error fetching user settings: user_id={user_id}, error={str(e)} \n\n Platform: {platform}",
                platform or "Unknown",
                "ERROR",
                device_info,
            )
            raise HTTPException(status_code=500, detail="Internal server error")
        raise e


@router.post("/settings")
async def update_user_settings(
    request: Request,
    user_id: int = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    API endpoint for updating user settings and profile information.
    Updates user profile data based on the action provided.
    """
    print(f"[update_user_settings] API called with user_id: {user_id}")

    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    # Check content type and handle accordingly
    content_type = request.headers.get("content-type", "")
    print("[update_user_settings] Content type:", content_type)

    # Initialize data dict
    data = {}
    files = {}

    try:
        if "application/json" in content_type:
            # Handle JSON request
            json_data = await request.json()
            print("[update_user_settings] JSON data:", json_data)
            data = json_data

            # Handle profile photo in JSON format (React Native)
            action = data.get("action")
            if action == "updateProfilePicture" and "profile_photo" in data:
                # Extract the profile_photo data
                profile_photo_data = data.pop("profile_photo", None)
                if profile_photo_data and isinstance(profile_photo_data, dict):
                    print("[update_user_settings] Photo:", profile_photo_data)
                    # Special handling in update_settings_async
                    data["profile_photo_json"] = profile_photo_data
        else:
            # Handle form data request
            form_data = await request.form()
            print("[update_user_settings] Form data:", form_data.keys())

            # Log all form data items for debugging
            for key, value in form_data.items():
                print("[update_user_settings] Form item:", key, type(value))
                if hasattr(value, "filename"):
                    print("[update_user_settings] File:", key, value.filename)
                    # This is a file upload
                    files[key] = value
                else:
                    # This is regular form data
                    data[key] = value
    except Exception as e:
        error_trace = traceback.format_exc()
        print("[update_user_settings] Error:", str(e), "\n", error_trace)
        raise HTTPException(
            status_code=400, detail={"error": f"Invalid request data: {str(e)}"}
        )

    # Extract action from data
    action = data.get("action")
    if not action:
        raise HTTPException(
            status_code=400, detail={"error": "Missing required parameter: action"}
        )

    @database_sync_to_async
    def update_settings_async(user_id, action, form_data, files=None):
        try:
            print(
                f"[update_settings_async] Processing settings update for user_id: {user_id}, action: {action}"
            )
            user = CustomUser.objects.get(id=user_id)
            profile = get_object_or_404(UserProfile, user=user)
            print(f"[update_settings_async] User and profile retrieved successfully")

            if action == "updateProfilePicture":
                print("[update_settings_async] Action: updateProfilePicture")
                print("[update_settings_async] Files:", files)
                print("[update_settings_async] Form keys:", form_data.keys())

                # Check for standard file upload
                if files and "profile_photo" in files:
                    print("[update_settings_async] Standard file upload")

                    # Create Django-compatible files dict
                    django_files = {}
                    upload_file = files["profile_photo"]

                    # Read file content
                    file_content = upload_file.file.read()

                    # Import here to avoid circular imports
                    from django.core.files.base import ContentFile

                    # Create ContentFile object
                    django_files["profile_photo"] = ContentFile(
                        file_content, name=upload_file.filename
                    )

                    # Create and validate form with proper file data
                    form = UpdateProfilePhotoForm(
                        form_data, django_files, instance=profile
                    )

                    if form.is_valid():
                        updated_profile = form.save()
                        serializer = UserProfileSerializer(updated_profile)
                        print(
                            f"[update_settings_async] Profile picture updated successfully"
                        )
                        return {
                            "message": "Profile picture updated successfully!",
                            "profile": serializer.data,
                        }
                    print("[update_settings_async] Validation errors:", form.errors)
                    return {"errors": form.errors, "status_code": 400}

                # Handle React Native style file upload (as JSON data)
                elif "profile_photo_json" in form_data:
                    print("[update_settings_async] React Native upload")
                    file_data = form_data["profile_photo_json"]

                    # Check if it's properly structured
                    if isinstance(file_data, dict) and "uri" in file_data:
                        try:
                            import requests
                            from django.core.files.base import ContentFile
                            from tempfile import NamedTemporaryFile

                            # Get the file URI from React Native
                            file_uri = file_data.get("uri")
                            default = "profile_photo.jpg"
                            file_name = file_data.get("name") or default

                            print("[update_settings_async] Download from:", file_uri)

                            # For local file URIs we need a different approach
                            if file_uri.startswith(("http://", "https://")):
                                # Download the image from the URI
                                response = requests.get(file_uri, stream=True)
                                if response.status_code == 200:
                                    # Create a temporary file
                                    img_temp = NamedTemporaryFile(delete=True)
                                    for chunk in response.iter_content(1024):
                                        img_temp.write(chunk)

                                    # Save the profile photo
                                    img_temp.seek(0)
                                    profile.profile_photo.save(
                                        file_name,
                                        ContentFile(img_temp.read()),
                                        save=True,
                                    )
                                    serializer = UserProfileSerializer(profile)
                                    return {
                                        "message": "Profile picture updated!",
                                        "profile": serializer.data,
                                    }
                            else:
                                return {
                                    "error": "Cannot process file URI",
                                    "status_code": 400,
                                }
                        except Exception as e:
                            print("[update_settings_async] URI error:", str(e))
                            return {
                                "error": f"Failed to process upload: {str(e)}",
                                "status_code": 400,
                            }

                # Handle case where profile_photo isn't processed as a file
                elif "profile_photo" in form_data and not isinstance(
                    form_data["profile_photo"], dict
                ):
                    print("[update_settings_async] Not processed as file")
                    return {
                        "error": "Photo not recognized as file. "
                        "Check form encoding.",
                        "status_code": 400,
                    }

                # Handle JSON-based profile photo metadata from web client
                elif "profile_photo" in form_data and isinstance(
                    form_data["profile_photo"], dict
                ):
                    print("[update_settings_async] Metadata without file")
                    return {
                        "error": "Invalid upload. Use multipart/form-data.",
                        "status_code": 400,
                    }

                else:
                    print("[update_settings_async] No photo in request")
                    return {
                        "error": "No profile photo found in the request",
                        "status_code": 400,
                    }

            elif action == "updatePersonalInfo":
                print(f"[update_settings_async] Action: updatePersonalInfo")
                form = UpdatePersonalInfo(form_data, instance=user)
                if form.is_valid():
                    updated_user = form.save()
                    serializer = CustomUserSerializer(updated_user)
                    print(f"[update_settings_async] Personal info updated successfully")
                    return {
                        "message": "Personal info updated!",
                        "user": serializer.data,
                    }
                print(f"[update_settings_async] Form validation errors: {form.errors}")
                return {"errors": form.errors, "status_code": 400}

            elif action == "updateContactInfo":
                print(f"[update_settings_async] Action: updateContactInfo")
                form = UpdateContactInfo(form_data, instance=user)
                if form.is_valid():
                    updated_user = form.save()
                    serializer = CustomUserSerializer(updated_user)
                    print(f"[update_settings_async] Contact info updated successfully")
                    return {
                        "message": "Contact info updated!",
                        "user": serializer.data,
                    }
                print(f"[update_settings_async] Form validation errors: {form.errors}")
                return {"errors": form.errors, "status_code": 400}

            else:
                print(f"[update_settings_async] Invalid action: {action}")
                return {"error": "Invalid action.", "status_code": 400}

        except CustomUser.DoesNotExist:
            return {"error": "User not found", "status_code": 404}
        except Exception as e:
            error_trace = traceback.format_exc()
            print(
                "[update_settings_async] Error for user:", user_id, str(e), error_trace
            )
            return {"error": f"Error: {str(e)}", "status_code": 500}

    try:
        # Process with form data and files from earlier parsing
        print(
            f"[update_user_settings] Calling update_settings_async with action: {action}"
        )
        result = await update_settings_async(user_id, action, data, files)
        if "status_code" in result:
            status_code = result.pop("status_code")
            print(
                f"[update_user_settings] Error with status code {status_code}: {result}"
            )
            raise HTTPException(status_code=status_code, detail=result)

        print(
            f"[update_user_settings] Successfully processed action '{action}' for user_id: {user_id}"
        )
        print(f"[update_user_settings] Returning result: {result}")
        return result
    except Exception as e:
        if not isinstance(e, HTTPException):
            error_trace = traceback.format_exc()
            print("[update_user_settings] Exception:", str(e), error_trace)
            await safe_notify_by_bot(
                f"**[API: update_user_settings]** \n\n Error updating user settings: user_id={user_id}, error={str(e)} \n\n Platform: {platform}",
                platform or "Unknown",
                "ERROR",
                device_info,
            )
            raise HTTPException(status_code=500, detail="Internal server error")
        raise e


@router.post("/password-reset")
async def password_reset(
    request: Request,
    email: str = Form(...),
    platform: Optional[str] = None,
):
    """
    API endpoint for password reset functionality.
    Sends a password reset email to the user.
    """
    print(f"[password_reset] API called with email: {email}")

    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:

        @database_sync_to_async
        def process_password_reset(email):
            try:
                print(
                    f"[process_password_reset] Processing password reset for email: {email}"
                )

                # Create form instance and validate
                form_data = {"email": email}
                email_form = EmailPasswordResetForm(form_data)

                if email_form.is_valid():
                    email = email_form.cleaned_data["email"]
                    user = CustomUser.objects.filter(email=email).first()

                    if user:
                        token = default_token_generator.make_token(user)
                        uid = urlsafe_base64_encode(force_bytes(user.pk))

                        expiry_time = timezone.now() + ResetLinkExpiryTime

                        # Build the reset URL - using a placeholder since we don't have the full Django URL structure
                        # In a real implementation, you'd need to configure the proper URL
                        reset_url = f"https://waveoncampus.com/forgot/new-password?uid={uid}&token={token}&expires={expiry_time.timestamp()}"

                        subject = "Request to reset password | WAVE."

                        # Create a simple email message since we don't have the template
                        message = f"""
                        Hello,
                        
                        You requested to reset your password. Please click the link below to reset your password:
                        
                        {reset_url}
                        
                        This link will expire in 24 hours.
                        
                        If you didn't request this, please ignore this email.
                        
                        Best regards,
                        WAVE Team
                        """

                        send_mail(subject, message, None, [email])
                        print(
                            f"[process_password_reset] Password reset email sent successfully to: {email}"
                        )
                        return {
                            "success": True,
                            "message": "Password reset email sent successfully!",
                        }
                    else:
                        print(
                            f"[process_password_reset] User not found for email: {email}"
                        )
                        return {"success": False, "error": "Account does not exist"}
                else:
                    print(
                        f"[process_password_reset] Form validation failed: {email_form.errors}"
                    )
                    return {"success": False, "errors": email_form.errors}

            except Exception as e:
                error_trace = traceback.format_exc()
                print(
                    f"[process_password_reset] Unexpected error: {str(e)}\n{error_trace}"
                )
                return {"success": False, "error": "Internal server error"}

        result = await process_password_reset(email)

        if not result["success"]:
            if "error" in result:
                await safe_notify_by_bot(
                    f"**[API: password_reset]** \n\n Error processing password reset: email={email}, error={result['error']} \n\n Platform: {platform}",
                    platform or "Unknown",
                    "ERROR",
                    device_info,
                )
                raise HTTPException(status_code=404, detail=result["error"])
            elif "errors" in result:
                await safe_notify_by_bot(
                    f"**[API: password_reset]** \n\n Validation errors: email={email}, errors={result['errors']} \n\n Platform: {platform}",
                    platform or "Unknown",
                    "ERROR",
                    device_info,
                )
                raise HTTPException(status_code=400, detail=result["errors"])
            else:
                await safe_notify_by_bot(
                    f"**[API: password_reset]** \n\n Internal error: email={email} \n\n Platform: {platform}",
                    platform or "Unknown",
                    "ERROR",
                    device_info,
                )
                raise HTTPException(status_code=500, detail="Internal server error")

        print(
            f"[password_reset] Password reset processed successfully for email: {email}"
        )
        return result
    except Exception as e:
        await safe_notify_by_bot(
            f"**[API: password_reset]** \n\n Error processing password reset: email={email}, error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(
            status_code=500, detail=f"Error processing password reset: {str(e)}"
        )


@router.post("/password-reset-confirm")
async def password_reset_confirm(
    request: Request,
    uid: str = Form(...),
    token: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    platform: Optional[str] = None,
):
    """
    API endpoint for confirming password reset and setting new password.
    Validates the reset token and sets the new password.
    """
    print(f"[password_reset_confirm] API called with uid: {uid}, token: {token}")

    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:

        @database_sync_to_async
        def process_password_reset_confirm(uid, token, new_password, confirm_password):
            try:
                print(
                    f"[process_password_reset_confirm] Processing password reset confirmation"
                )

                # Validate passwords match
                if new_password != confirm_password:
                    print(f"[process_password_reset_confirm] Passwords do not match")
                    return {"success": False, "error": "Passwords do not match"}

                # Validate password strength (basic validation)
                if len(new_password) < 8:
                    print(f"[process_password_reset_confirm] Password too short")
                    return {
                        "success": False,
                        "error": "Password must be at least 8 characters long",
                    }

                # Decode the user ID from the URL-safe base64 string
                try:
                    user_id = force_str(urlsafe_base64_decode(uid))
                    user = CustomUser.objects.get(pk=user_id)
                    print(f"[process_password_reset_confirm] User found: {user.email}")
                except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
                    print(
                        f"[process_password_reset_confirm] Invalid user ID or user not found"
                    )
                    return {"success": False, "error": "Invalid reset link"}

                # Check if the token is valid
                if not default_token_generator.check_token(user, token):
                    print(f"[process_password_reset_confirm] Invalid token")
                    return {"success": False, "error": "Invalid or expired reset link"}

                # Set the new password
                user.set_password(new_password)
                user.save()

                print(
                    f"[process_password_reset_confirm] Password updated successfully for user: {user.email}"
                )
                return {"success": True, "message": "Password updated successfully!"}

            except Exception as e:
                error_trace = traceback.format_exc()
                print(
                    f"[process_password_reset_confirm] Unexpected error: {str(e)}\n{error_trace}"
                )
                return {"success": False, "error": "Internal server error"}

        result = await process_password_reset_confirm(
            uid, token, new_password, confirm_password
        )

        if not result["success"]:
            if "error" in result:
                await safe_notify_by_bot(
                    f"**[API: password_reset_confirm]** \n\n Error confirming password reset: uid={uid}, error={result['error']} \n\n Platform: {platform}",
                    platform or "Unknown",
                    "ERROR",
                    device_info,
                )
                raise HTTPException(status_code=400, detail=result["error"])
            else:
                await safe_notify_by_bot(
                    f"**[API: password_reset_confirm]** \n\n Internal error: uid={uid} \n\n Platform: {platform}",
                    platform or "Unknown",
                    "ERROR",
                    device_info,
                )
                raise HTTPException(status_code=500, detail="Internal server error")

        print(
            f"[password_reset_confirm] Password reset confirmation processed successfully"
        )
        return result
    except Exception as e:
        await safe_notify_by_bot(
            f"**[API: password_reset_confirm]** \n\n Error confirming password reset: uid={uid}, error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(
            status_code=500, detail=f"Error confirming password reset: {str(e)}"
        )


@router.get("/preferences/form")
async def get_preferences_form(
    request: Request,
    platform: Optional[str] = None,
):
    """
    API endpoint for retrieving user preferences form.
    Returns the form fields for user preferences.
    """

    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    is_mobile = request.headers.get("X-Platform") == "mobile"
    FormClass = UserPreferencesForm
    fields_info = get_form_fields(FormClass)
    print(
        f"[get_preferences_form] Returning form fields, field count: {len(fields_info)}"
    )
    return JSONResponse(content=fields_info, status_code=status.HTTP_200_OK)


@router.post("/preferences")
async def set_user_preferences(
    request: Request,
    user_id: int = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    API endpoint for setting user preferences.
    """
    print(f"[set_user_preferences] API called with user_id: {user_id}")

    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:
        # Get form data from request
        form_data = await request.form()
        form_dict = dict(form_data)

        # Helper function to parse list values
        def parse_list(value):
            if not value:
                return []
            if isinstance(value, list):
                return value
            if isinstance(value, str):
                try:
                    parsed = json.loads(value)
                    if isinstance(parsed, list):
                        return parsed
                except Exception:
                    return [item.strip() for item in value.split(",")]
            return []

        @database_sync_to_async
        def set_user_preferences_async(user_id, form_data):
            try:
                print(
                    f"[set_user_preferences_async] Processing preferences for user_id: {user_id}"
                )
                user = CustomUser.objects.get(id=user_id)

                if form_data.get("first_name"):
                    user.first_name = form_data.get("first_name").strip()
                    print(
                        f"[set_user_preferences_async] Updated first_name: {user.first_name}"
                    )
                if form_data.get("last_name"):
                    user.last_name = form_data.get("last_name").strip()
                    print(
                        f"[set_user_preferences_async] Updated last_name: {user.last_name}"
                    )
                user.save()

                try:
                    user_preferences = UserPreferences.objects.get(user=user)
                except UserPreferences.DoesNotExist:
                    user_profile, _ = UserProfile.objects.get_or_create(user=user)
                    user_preferences = UserPreferences.objects.create(
                        user=user, profile=user_profile
                    )
                    print(
                        f"[set_user_preferences_async] Created new UserPreferences for user_id: {user_id}"
                    )

                if "interests" in form_data:
                    user_preferences.interests = parse_list(form_data.get("interests"))

                if "vibe" in form_data:
                    user_preferences.vibe = form_data.get("vibe")

                if "people_to_meet" in form_data:
                    user_preferences.people_to_meet = parse_list(
                        form_data.get("people_to_meet")
                    )

                # Handle preferred_times field
                if "preferred_times" in form_data:
                    print(
                        f"[set_user_preferences_async] Preferred times: {form_data.get('preferred_times')}"
                    )
                    # Handle JSONField mismatch - database has JSONField but model shows CharField
                    preferred_time_value = form_data.get("preferred_times")
                    if preferred_time_value and str(preferred_time_value).strip():
                        clean_value = str(preferred_time_value).strip()
                        # Force JSONField to properly serialize this as JSON
                        import json

                        print(
                            f"[set_user_preferences_async] Clean value: {clean_value}"
                        )
                        user_preferences.preferred_times = json.dumps(clean_value)
                    else:
                        user_preferences.preferred_times = json.dumps("")
                        print(
                            f"[set_user_preferences_async] Preferred times set to empty string: {user_preferences.preferred_times}"
                        )

                user_preferences.preferences_completed = True
                user_preferences.save()

                print(
                    f"[set_user_preferences_async] Preferences saved for user_id: {user_id}"
                )
                return {
                    "success": True,
                    "message": "Preferences and profile updated successfully",
                }

            except Exception as e:
                print(f"[set_user_preferences_async] Error: {str(e)}")
                return {"success": False, "error": str(e)}

        result = await set_user_preferences_async(user_id, form_dict)

        if not result["success"]:
            await safe_notify_by_bot(
                f"**[API: set_user_preferences]** \n\n Error saving preferences: user_id={user_id}, error={result['error']} \n\n Platform: {platform}",
                platform or "Unknown",
                "ERROR",
                device_info,
            )
            raise HTTPException(status_code=400, detail=result["error"])

        return result

    except Exception as e:
        await safe_notify_by_bot(
            f"**[API: set_user_preferences]** \n\n Internal server error: user_id={user_id}, error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(
            status_code=500, detail=f"Error saving preferences: {str(e)}"
        )


@router.get("/preferences")
async def get_user_preferences(
    request: Request,
    user_id: int = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    API endpoint for retrieving all user preferences.
    Returns complete user preferences data.
    """
    print(f"[get_user_preferences] API called with user_id: {user_id}")

    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:

        @database_sync_to_async
        def get_user_preferences_async(user_id):
            try:
                print(
                    f"[get_user_preferences_async] Retrieving preferences for user_id: {user_id}"
                )
                user = CustomUser.objects.get(id=user_id)

                # Get or create user preferences
                try:
                    user_preferences = UserPreferences.objects.get(user=user)
                    print(
                        f"[get_user_preferences_async] UserPreferences found for user: {user.username}"
                    )
                except UserPreferences.DoesNotExist:
                    # Create UserPreferences if it doesn't exist
                    from accountManagementApp.models import UserProfile

                    user_profile, created = UserProfile.objects.get_or_create(user=user)
                    user_preferences = UserPreferences.objects.create(
                        user=user, profile=user_profile
                    )
                    print(
                        f"[get_user_preferences_async] Created new UserPreferences for user_id: {user_id}"
                    )

                # Build preferences data
                preferences_data = {
                    "user_id": str(user.user_id),
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "interests": user_preferences.interests or [],
                    "vibe": user_preferences.vibe or "",
                    "people_to_meet": user_preferences.people_to_meet or [],
                    "preferred_times": user_preferences.preferred_times or "",
                    "preferences_completed": user_preferences.preferences_completed,
                }

                print(
                    f"[get_user_preferences_async] Preferences data prepared successfully"
                )
                return preferences_data

            except CustomUser.DoesNotExist:
                print(
                    f"[get_user_preferences_async] Error: User with id {user_id} does not exist"
                )
                return None
            except Exception as e:
                error_trace = traceback.format_exc()
                print(
                    f"[get_user_preferences_async] Unexpected error retrieving preferences for user_id {user_id}: {str(e)}\n{error_trace}"
                )
                return None

        preferences_data = await get_user_preferences_async(user_id)
        if preferences_data is None:
            await safe_notify_by_bot(
                f"**[API: get_user_preferences]** \n\n User not found: user_id={user_id} \n\n Platform: {platform}",
                platform or "Unknown",
                "ERROR",
                device_info,
            )
            raise HTTPException(status_code=404, detail="User not found")

        print(f"[get_user_preferences] Returning preferences data: {preferences_data}")
        return preferences_data
    except Exception as e:
        if not isinstance(e, HTTPException):
            error_trace = traceback.format_exc()
            print(
                f"[get_user_preferences] Unhandled exception: {str(e)}\n{error_trace}"
            )
            await safe_notify_by_bot(
                f"**[API: get_user_preferences]** \n\n Unhandled exception: user_id={user_id}, error={str(e)} \n\n Platform: {platform}",
                platform or "Unknown",
                "ERROR",
                device_info,
            )
            raise HTTPException(status_code=500, detail="Internal server error")
        raise e


@router.get("/check/college")
async def check_user_college(
    request: Request,
    user_id: int = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    API endpoint for checking if a user is a college student.
    Returns whether the currently logged in user is associated with a college.
    """
    print(f"[check_user_college] API called with user_id: {user_id}")

    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:

        @database_sync_to_async
        def check_user_has_college(user_id):
            try:
                print(
                    f"[check_user_has_college] Checking college association for user_id: {user_id}"
                )
                user = CustomUser.objects.get(id=user_id)

                try:
                    user_profile = UserProfile.objects.get(user=user)
                    print(
                        f"[check_user_has_college] UserProfile found for user: {user.username}"
                    )
                except UserProfile.DoesNotExist:
                    print(
                        f"[check_user_has_college] UserProfile not found for user: {user.username}, creating one..."
                    )
                    user_profile = UserProfile.objects.create(user=user)
                    print(
                        f"[check_user_has_college] UserProfile created for user: {user.username}"
                    )

                # Check if user has a college associated
                has_college = user_profile.college is not None
                college_info = None

                if has_college:
                    college_info = {
                        "collegeId": str(user_profile.college.collegeId),
                        "collegeName": user_profile.college.name,
                    }

                print(f"[check_user_has_college] User has college: {has_college}")

                return {"has_college": has_college, "college": college_info}

            except CustomUser.DoesNotExist:
                print(
                    f"[check_user_has_college] Error: User with id {user_id} does not exist"
                )
                return None
            except Exception as e:
                error_trace = traceback.format_exc()
                print(
                    f"[check_user_has_college] Unexpected error checking college for user_id {user_id}: {str(e)}\n{error_trace}"
                )
                return None

        result = await check_user_has_college(user_id)
        if result is None:
            await safe_notify_by_bot(
                f"**[API: check_user_college]** \n\n User not found: user_id={user_id} \n\n Platform: {platform}",
                platform or "Unknown",
                "ERROR",
                device_info,
            )
            raise HTTPException(status_code=404, detail="User not found")

        print(
            f"[check_user_college] Returning college check result for user_id: {user_id}: {result}"
        )
        return result
    except Exception as e:
        if not isinstance(e, HTTPException):
            error_trace = traceback.format_exc()
            print(f"[check_user_college] Unhandled exception: {str(e)}\n{error_trace}")
            await safe_notify_by_bot(
                f"**[API: check_user_college]** \n\n Unhandled exception: user_id={user_id}, error={str(e)} \n\n Platform: {platform}",
                platform or "Unknown",
                "ERROR",
                device_info,
            )
            raise HTTPException(status_code=500, detail="Internal server error")
        raise e


@router.get("/privacy-settings")
async def get_privacy_settings(
    request: Request,
    user_id: int = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    API endpoint for retrieving user privacy settings.
    Returns privacy settings from the CustomUser model.
    """
    print(f"[get_privacy_settings] API called with user_id: {user_id}")

    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def get_privacy_settings_async(user_id):
        try:
            print(
                f"[get_privacy_settings_async] Retrieving privacy settings for user_id: {user_id}"
            )
            user = CustomUser.objects.get(id=user_id)
            print(f"[get_privacy_settings_async] User found: {user.username}")

            # Build privacy settings data
            privacy_settings = {
                "user_id": str(user.user_id),
                "show_on_guestlist": user.show_on_guestlist,
                "show_others_your_name": user.show_others_your_name,
                "show_yourself_as_a_college_member": user.show_yourself_as_a_college_member,
                "allow_notifications_from_email": user.allow_notifications_from_email,
                "allow_notifications_from_mobile": user.allow_notifications_from_mobile,
            }

            print(
                f"[get_privacy_settings_async] Privacy settings data prepared successfully"
            )
            return privacy_settings

        except CustomUser.DoesNotExist:
            print(
                f"[get_privacy_settings_async] Error: User with id {user_id} does not exist"
            )
            return None
        except Exception as e:
            error_trace = traceback.format_exc()
            print(
                f"[get_privacy_settings_async] Unexpected error retrieving privacy settings for user_id {user_id}: {str(e)}\n{error_trace}"
            )
            return None

    try:
        privacy_settings = await get_privacy_settings_async(user_id)
        if privacy_settings is None:
            await safe_notify_by_bot(
                f"**[API: get_privacy_settings]** \n\n User not found: user_id={user_id} \n\n Platform: {platform}",
                platform or "Unknown",
                "ERROR",
                device_info,
            )
            raise HTTPException(status_code=404, detail="User not found")

        print(
            f"[get_privacy_settings] Returning privacy settings data: {privacy_settings}"
        )
        return privacy_settings
    except Exception as e:
        if not isinstance(e, HTTPException):
            error_trace = traceback.format_exc()
            print(
                f"[get_privacy_settings] Unhandled exception: {str(e)}\n{error_trace}"
            )
            await safe_notify_by_bot(
                f"**[API: get_privacy_settings]** \n\n Unhandled exception: user_id={user_id}, error={str(e)} \n\n Platform: {platform}",
                platform or "Unknown",
                "ERROR",
                device_info,
            )
            raise HTTPException(status_code=500, detail="Internal server error")
        raise e


@router.post("/privacy-settings")
async def set_privacy_settings(
    request: Request,
    user_id: int = Depends(get_current_user),
    show_on_guestlist: Optional[bool] = Form(None),
    show_others_your_name: Optional[bool] = Form(None),
    show_yourself_as_a_college_member: Optional[bool] = Form(None),
    allow_notifications_from_email: Optional[bool] = Form(None),
    allow_notifications_from_mobile: Optional[bool] = Form(None),
    platform: Optional[str] = None,
):
    """
    API endpoint for updating user privacy settings.
    Updates privacy settings in the CustomUser model.
    """
    print(f"[set_privacy_settings] API called with user_id: {user_id}")

    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def set_privacy_settings_async(user_id, settings):
        try:
            print(
                f"[set_privacy_settings_async] Processing privacy settings for user_id: {user_id}"
            )
            user = CustomUser.objects.get(id=user_id)
            print(f"[set_privacy_settings_async] User found: {user.username}")

            # Track what was updated for logging
            updated_fields = []

            # Update privacy settings only if they are provided (not None)
            if settings.get("show_on_guestlist") is not None:
                user.show_on_guestlist = settings["show_on_guestlist"]
                updated_fields.append(
                    f"show_on_guestlist: {settings['show_on_guestlist']}"
                )

            if settings.get("show_others_your_name") is not None:
                user.show_others_your_name = settings["show_others_your_name"]
                updated_fields.append(
                    f"show_others_your_name: {settings['show_others_your_name']}"
                )

            if settings.get("show_yourself_as_a_college_member") is not None:
                user.show_yourself_as_a_college_member = settings[
                    "show_yourself_as_a_college_member"
                ]
                updated_fields.append(
                    f"show_yourself_as_a_college_member: {settings['show_yourself_as_a_college_member']}"
                )

            if settings.get("allow_notifications_from_email") is not None:
                user.allow_notifications_from_email = settings[
                    "allow_notifications_from_email"
                ]
                updated_fields.append(
                    f"allow_notifications_from_email: {settings['allow_notifications_from_email']}"
                )

            if settings.get("allow_notifications_from_mobile") is not None:
                user.allow_notifications_from_mobile = settings[
                    "allow_notifications_from_mobile"
                ]
                updated_fields.append(
                    f"allow_notifications_from_mobile: {settings['allow_notifications_from_mobile']}"
                )

            # Only save if there were actual changes
            if updated_fields:
                user.save()
                print(
                    f"[set_privacy_settings_async] Updated fields: {', '.join(updated_fields)}"
                )

                # Return updated privacy settings
                updated_privacy_settings = {
                    "user_id": str(user.user_id),
                    "show_on_guestlist": user.show_on_guestlist,
                    "show_others_your_name": user.show_others_your_name,
                    "show_yourself_as_a_college_member": user.show_yourself_as_a_college_member,
                    "allow_notifications_from_email": user.allow_notifications_from_email,
                    "allow_notifications_from_mobile": user.allow_notifications_from_mobile,
                }

                print(
                    f"[set_privacy_settings_async] Privacy settings updated successfully"
                )
                return {
                    "success": True,
                    "message": "Privacy settings updated successfully",
                    "privacy_settings": updated_privacy_settings,
                }
            else:
                print(f"[set_privacy_settings_async] No changes provided")
                return {
                    "success": False,
                    "error": "No privacy settings provided for update",
                }

        except CustomUser.DoesNotExist:
            print(
                f"[set_privacy_settings_async] Error: User with id {user_id} does not exist"
            )
            return {"success": False, "error": "User not found"}
        except Exception as e:
            error_trace = traceback.format_exc()
            print(
                f"[set_privacy_settings_async] Unexpected error updating privacy settings for user_id {user_id}: {str(e)}\n{error_trace}"
            )
            return {"success": False, "error": str(e)}

    try:
        # Build settings dictionary from form parameters
        settings = {}
        if show_on_guestlist is not None:
            settings["show_on_guestlist"] = show_on_guestlist
        if show_others_your_name is not None:
            settings["show_others_your_name"] = show_others_your_name
        if show_yourself_as_a_college_member is not None:
            settings["show_yourself_as_a_college_member"] = (
                show_yourself_as_a_college_member
            )
        if allow_notifications_from_email is not None:
            settings["allow_notifications_from_email"] = allow_notifications_from_email
        if allow_notifications_from_mobile is not None:
            settings["allow_notifications_from_mobile"] = (
                allow_notifications_from_mobile
            )

        print(f"[set_privacy_settings] Settings to update: {settings}")

        result = await set_privacy_settings_async(user_id, settings)

        if not result["success"]:
            if "User not found" in result.get("error", ""):
                await safe_notify_by_bot(
                    f"**[API: set_privacy_settings]** \n\n User not found: user_id={user_id} \n\n Platform: {platform}",
                    platform or "Unknown",
                    "ERROR",
                    device_info,
                )
                raise HTTPException(status_code=404, detail="User not found")
            else:
                await safe_notify_by_bot(
                    f"**[API: set_privacy_settings]** \n\n Error updating privacy settings: user_id={user_id}, error={result.get('error')} \n\n Platform: {platform}",
                    platform or "Unknown",
                    "ERROR",
                    device_info,
                )
                raise HTTPException(status_code=400, detail=result.get("error"))

        print(
            f"[set_privacy_settings] Privacy settings updated successfully for user_id: {user_id}"
        )

        # Notify about privacy settings update
        await safe_notify_by_bot(
            f"**[Privacy Settings Update]** \n\n User privacy settings updated: user_id={user_id}, settings={settings} \n\n Platform: {platform}",
            platform or "Unknown",
            "INFO",
            device_info,
        )

        return result

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"[set_privacy_settings] Unhandled exception: {str(e)}\n{error_trace}")
        await safe_notify_by_bot(
            f"**[API: set_privacy_settings]** \n\n Unhandled exception: user_id={user_id}, error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/universal-qr", response_model=UniversalQRResponse)
async def get_user_universal_qr(
    request: Request,
    user_id: int = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    API endpoint for retrieving user's universal QR code.
    Returns the universal QR code image URL and metadata for the authenticated user.
    """
    print(f"[get_user_universal_qr] API called with user_id: {user_id}")

    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def get_universal_qr_data(user_id):
        try:
            print(
                f"[get_universal_qr_data] Retrieving universal QR for user_id: {user_id}"
            )

            # Use select_related to optimize query
            user = CustomUser.objects.select_related("user_profile").get(id=user_id)

            # Ensure user has a profile
            if not hasattr(user, "user_profile") or not user.user_profile:
                # Create profile if it doesn't exist
                from accountManagementApp.models import UserProfile

                user_profile = UserProfile.objects.create(user=user)
                print(
                    f"[get_universal_qr_data] Created new profile for user: {user.username}"
                )
            else:
                user_profile = user.user_profile

            # Get QR code information
            qr_data = {
                "user_id": str(user.user_id),
                "username": user.username,
                "universal_qr_code": (
                    str(user_profile.universal_qr_code)
                    if user_profile.universal_qr_code
                    else None
                ),
                "universal_qr_code_image_url": (
                    user_profile.universal_qr_code_image.url
                    if user_profile.universal_qr_code_image
                    else None
                ),
                "has_qr_code": bool(user_profile.universal_qr_code_image),
                "qr_generated_at": (
                    user_profile.universal_qr_code_image.url
                    if user_profile.universal_qr_code_image
                    else None
                ),
            }

            # Generate QR code if it doesn't exist
            if not user_profile.universal_qr_code_image:
                print(
                    f"[get_universal_qr_data] Generating missing universal QR for user: {user.username}"
                )
                success = user_profile.generate_universal_qr_code()
                if success:
                    user_profile.save(update_fields=["universal_qr_code_image"])
                    qr_data["universal_qr_code_image_url"] = (
                        user_profile.universal_qr_code_image.url
                    )
                    qr_data["has_qr_code"] = True
                    qr_data["universal_qr_code"] = str(user_profile.universal_qr_code)
                    print(
                        f"[get_universal_qr_data] Successfully generated QR for user: {user.username}"
                    )
                else:
                    print(
                        f"[get_universal_qr_data] Failed to generate QR for user: {user.username}"
                    )

            print(
                f"[get_universal_qr_data] Returning QR data for user: {user.username}"
            )
            return qr_data

        except CustomUser.DoesNotExist:
            print(
                f"[get_universal_qr_data] Error: User with id {user_id} does not exist"
            )
            return None
        except Exception as e:
            error_trace = traceback.format_exc()
            print(f"[get_universal_qr_data] Unexpected error: {str(e)}\n{error_trace}")
            return None

    try:
        qr_data = await get_universal_qr_data(user_id)

        if qr_data is None:
            await safe_notify_by_bot(
                f"**[API: get_user_universal_qr]** \n\n User not found: user_id={user_id} \n\n Platform: {platform}",
                platform or "Unknown",
                "ERROR",
                device_info,
            )
            raise HTTPException(status_code=404, detail="User not found")

        print(f"[get_user_universal_qr] Returning QR data for user_id: {user_id}")
        return qr_data

    except HTTPException:
        raise
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"[get_user_universal_qr] Unhandled exception: {str(e)}\n{error_trace}")
        await safe_notify_by_bot(
            f"**[API: get_user_universal_qr]** \n\n Unhandled exception: user_id={user_id}, error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/tickets", response_model=UserTicketsResponse)
async def get_user_tickets_detailed(
    request: Request,
    user_id: int = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    API endpoint for retrieving all tickets associated with the user.
    Returns comprehensive ticket information with individual QR code data.
    """
    print(f"[get_user_tickets_detailed] API called with user_id: {user_id}")

    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def get_user_tickets_data(user_id):
        try:
            print(f"[get_user_tickets_data] Retrieving tickets for user_id: {user_id}")

            # Optimize query with select_related and prefetch_related
            user = CustomUser.objects.select_related("user_profile").get(id=user_id)

            # Get all tickets with optimized queries
            tickets = (
                Ticket.objects.select_related("event", "user__user_profile")
                .filter(user=user)
                .order_by("-created_at")
            )

            print(f"[get_user_tickets_data] Found {tickets.count()} tickets")

            tickets_data = []
            for ticket in tickets:
                # Build comprehensive ticket data
                ticket_data = {
                    "ticket_id": str(ticket.ticketId),
                    "main_id": str(ticket.mainId),
                    "status": ticket.status,
                    "created_at": ticket.created_at.isoformat(),
                    "stripe_session_id": ticket.stripe_session_id,
                    # Event information
                    "event": {
                        "event_id": str(ticket.event.eventId),
                        "title": ticket.event.title,
                        "date": (
                            ticket.event.date.isoformat() if ticket.event.date else None
                        ),
                        "start_time": (
                            ticket.event.start_time.isoformat()
                            if ticket.event.start_time
                            else None
                        ),
                        "end_time": (
                            ticket.event.end_time.isoformat()
                            if ticket.event.end_time
                            else None
                        ),
                        "header_photo": (
                            ticket.event.header_photo.url
                            if ticket.event.header_photo
                            else None
                        ),
                        "description": getattr(ticket.event, "description", None),
                        "venue": getattr(ticket.event, "venue", None),
                        "ticketing": getattr(ticket.event, "ticketing", None),
                    },
                    # Guest information (for guest tickets)
                    "guest_info": (
                        {
                            "first_name": ticket.guestFirstName,
                            "last_name": ticket.guestLastName,
                            "email": ticket.guestEmail,
                        }
                        if any(
                            [
                                ticket.guestFirstName,
                                ticket.guestLastName,
                                ticket.guestEmail,
                            ]
                        )
                        else None
                    ),
                }

                # Add individual ticket QR code information (separate ticket system)
                qr_code_image_url = None
                qr_code_data = None

                if ticket.qrCodeImage:
                    qr_code_image_url = ticket.qrCodeImage.url
                if ticket.qrCodeData:
                    qr_code_data = ticket.qrCodeData

                ticket_data["qr_code"] = {
                    "qr_code_data": qr_code_data,
                    "qr_code_image_url": qr_code_image_url,
                    "has_qr_code": bool(qr_code_image_url and qr_code_data),
                }

                tickets_data.append(ticket_data)

            # Get summary statistics
            total_tickets = tickets.count()
            valid_tickets = tickets.filter(status="Valid").count()
            scanned_tickets = tickets.filter(status="Scanned").count()

            result = {
                "user_id": str(user.user_id),
                "username": user.username,
                "total_tickets": total_tickets,
                "statistics": {
                    "valid": valid_tickets,
                    "scanned": scanned_tickets,
                    "invalid": total_tickets - valid_tickets - scanned_tickets,
                },
                "tickets": tickets_data,
                "has_qr_codes": True,  # Using individual ticket QR codes (separate ticket system)
            }

            print(
                f"[get_user_tickets_data] Returning {total_tickets} tickets for user: {user.username}"
            )
            return result

        except CustomUser.DoesNotExist:
            print(
                f"[get_user_tickets_data] Error: User with id {user_id} does not exist"
            )
            return None
        except Exception as e:
            error_trace = traceback.format_exc()
            print(f"[get_user_tickets_data] Unexpected error: {str(e)}\n{error_trace}")
            return None

    try:
        tickets_data = await get_user_tickets_data(user_id)

        if tickets_data is None:
            await safe_notify_by_bot(
                f"**[API: get_user_tickets_detailed]** \n\n User not found: user_id={user_id} \n\n Platform: {platform}",
                platform or "Unknown",
                "ERROR",
                device_info,
            )
            raise HTTPException(status_code=404, detail="User not found")

        print(
            f"[get_user_tickets_detailed] Returning {tickets_data['total_tickets']} tickets for user_id: {user_id}"
        )
        return tickets_data

    except HTTPException:
        raise
    except Exception as e:
        error_trace = traceback.format_exc()
        print(
            f"[get_user_tickets_detailed] Unhandled exception: {str(e)}\n{error_trace}"
        )
        await safe_notify_by_bot(
            f"**[API: get_user_tickets_detailed]** \n\n Unhandled exception: user_id={user_id}, error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(status_code=500, detail="Internal server error")

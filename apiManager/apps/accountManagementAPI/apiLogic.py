from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    Request,
    Header,
    UploadFile,
    Form,
)
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Optional, Dict, Any
from asgiref.sync import sync_to_async
import traceback
import os
from django.core.files.base import ContentFile

from authenticationApp.models import CustomUser
from authenticationApp.serializers import CustomUserSerializer
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from adminDashboardApp.models import LoginHistoryModel
from eventManagementApp.models import Event
from eventTicketsApp.models import Ticket
from accountManagementApp.models import UserProfile
from accountManagementApp.serializers import UserProfileSerializer
from accountManagementApp.forms import (
    UpdateProfilePhotoForm,
    UpdatePersonalInfo,
    UpdateContactInfo,
)
from fastapi import Depends
from apiManager.dependencies import get_current_user
from django.shortcuts import get_object_or_404

from .serializers import TicketSerializer

router = APIRouter()


@router.get("/profileOverview")
async def profileOverview(user_id: int = Depends(get_current_user)):
    """
    API endpoint for getting profile overview.
    Returns user profile data.
    """
    # Log authentication status
    if user_id is None:
        print("[profileOverview] Authentication failed: No user_id provided")
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    print(f"[profileOverview] Processing request for user_id: {user_id}")

    @sync_to_async
    def get_profile_overview(user_id):
        try:
            user = CustomUser.objects.get(id=user_id)
            user_data = {
                "id": user_id,
                "user_id": str(user.user_id),
                "profile_photo": (
                    user.user_profile.profile_photo.url
                    if user.user_profile.profile_photo
                    else None
                ),
                "first_name": user.first_name,
                "last_name": user.last_name,
                "username": user.username,
            }
            print(
                f"[profileOverview] Successfully retrieved profile data for user_id: {user_id}"
            )
            return user_data
        except CustomUser.DoesNotExist:
            print(f"[profileOverview] Error: User with id {user_id} does not exist")
            return None
        except Exception as e:
            error_trace = traceback.format_exc()
            print(
                f"[profileOverview] Unexpected error retrieving profile for user_id {user_id}: {str(e)}\n{error_trace}"
            )
            return None

    try:
        profile_data = await get_profile_overview(user_id)
        if profile_data is None:
            raise HTTPException(status_code=404, detail="User not found")
        return profile_data
    except Exception as e:
        if not isinstance(e, HTTPException):
            error_trace = traceback.format_exc()
            print(f"[profileOverview] Unhandled exception: {str(e)}\n{error_trace}")
            raise HTTPException(status_code=500, detail="Internal server error")
        raise e


@router.get("/profile/detailed")
async def profile_detailed(user_id: int = Depends(get_current_user)):
    """
    API endpoint for getting detailed profile information.
    Returns user profile data including email and phone number.
    """

    @sync_to_async
    def get_profile_detailed(user_id):
        try:
            user = CustomUser.objects.get(id=user_id)
            user_data = {
                "id": user_id,
                "user_id": str(user.user_id),
                "profile_photo": (
                    user.user_profile.profile_photo.url
                    if user.user_profile.profile_photo
                    else None
                ),
                "first_name": user.first_name,
                "last_name": user.last_name,
                "username": user.username,
                "email": user.email,
            }
            return user_data
        except CustomUser.DoesNotExist:
            return None

    profile_data = await get_profile_detailed(user_id)
    if profile_data is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return profile_data


@router.post("/profile/detailed")
async def update_profile_detailed(
    request: Request,
    user_id: int = Depends(get_current_user),
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    email: Optional[str] = None,
    profile_photo: Optional[UploadFile] = None,
):
    """
    API endpoint for updating detailed profile information.
    Updates user profile data including email, phone number, and profile photo.
    """

    @sync_to_async
    def update_profile_detailed(user_id, first_name, last_name, email, profile_photo):
        try:
            user = CustomUser.objects.get(id=user_id)
            if first_name:
                user.first_name = first_name
            if last_name:
                user.last_name = last_name
            if email:
                user.email = email
            user.save()

            # Handle profile photo upload if provided
            if profile_photo:
                # Get or create user profile
                user_profile = user.user_profile
                # Save the uploaded file to the profile_photo field
                if user_profile.profile_photo:
                    # Delete old photo if it exists to avoid storage buildup
                    old_photo = user_profile.profile_photo
                    if old_photo and os.path.exists(old_photo.path):
                        os.remove(old_photo.path)

                from django.core.files import File
                from tempfile import NamedTemporaryFile

                # Save the uploaded file to a temporary file
                temp_file = NamedTemporaryFile(delete=False)
                try:
                    temp_file.write(profile_photo.file.read())
                    temp_file.close()

                    # Save the file to the profile_photo field
                    with open(temp_file.name, "rb") as f:
                        filename = profile_photo.filename
                        user_profile.profile_photo.save(filename, File(f), save=True)
                finally:
                    # Clean up the temporary file
                    os.unlink(temp_file.name)

            return True
        except CustomUser.DoesNotExist:
            return False

    success = await update_profile_detailed(
        user_id, first_name, last_name, email, profile_photo
    )
    if not success:
        raise HTTPException(status_code=404, detail="User not found")

    return {"message": "Profile updated successfully"}


@router.get("/getUserTickets")
async def get_user_tickets(user_id: int = Depends(get_current_user)):
    @sync_to_async
    def get_user_tickets_async(user_id):
        user = CustomUser.objects.get(id=user_id)
        tickets = Ticket.objects.filter(user=user)
        ticket_list = []
        for ticket in tickets:
            ticket_list.append(
                {
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
                    "qrCodeImage": (
                        ticket.qrCodeImage.url if ticket.qrCodeImage else None
                    ),
                    "status": ticket.status,
                    "eventDate": ticket.event.date,
                    "eventStartTime": ticket.event.start_time,
                    "eventEndTime": ticket.event.end_time,
                }
            )

        return ticket_list

    ticket_data = await get_user_tickets_async(user_id)
    tickets = [TicketSerializer(**ticket) for ticket in ticket_data]

    return {"tickets": tickets}


@router.get("/getUserTickets/{ticketId}/details")
async def get_user_ticket_details(
    ticketId: str, user_id: int = Depends(get_current_user)
):
    """
    API endpoint for getting user ticket details.
    Returns details of a specific ticket belonging to the authenticated user.
    """

    @sync_to_async
    def get_user_ticket_details_async(ticketId, user_id):
        user = CustomUser.objects.get(id=user_id)
        try:
            ticket = Ticket.objects.get(ticketId=ticketId, user=user)
            return {
                "ticketId": str(ticket.ticketId),
                "guestFirstName": ticket.guestFirstName,
                "guestLastName": ticket.guestLastName,
                "guestEmail": ticket.guestEmail,
                "eventId": str(ticket.event.eventId),
                "eventTitle": ticket.event.title,
                "date": ticket.event.date,
                "header_photo": (
                    ticket.event.header_photo.url if ticket.event.header_photo else None
                ),
                "qrCodeImage": ticket.qrCodeImage.url if ticket.qrCodeImage else None,
                "status": ticket.status,
            }

        except Ticket.DoesNotExist:
            return None

    ticket_data = await get_user_ticket_details_async(ticketId, user_id)
    if ticket_data is None:
        raise HTTPException(status_code=404, detail="Ticket not found")

    return ticket_data


@router.get("/profile/favoriteEvents")
async def favoriteEvents(user_id: int = Depends(get_current_user)):
    """
    API endpoint for getting profile overview.
    Returns user profile data.
    """

    @sync_to_async
    def get_fav_events(user_id):
        try:
            user = CustomUser.objects.get(id=user_id)
            user_profile = UserProfile.objects.get(user=user)
            events = user_profile.favorite_events.all()
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
        raise HTTPException(status_code=404, detail="Event not found")
    return events_data


@router.post("/profile/delete")
async def delete_profile(user_id: int = Depends(get_current_user)):
    """
    API endpoint for deleting a user profile.
    Deletes the user profile and associated data.
    """

    @sync_to_async
    def delete_profile(user_id):
        try:
            user = CustomUser.objects.get(id=user_id)
            user.delete()
            return True
        except CustomUser.DoesNotExist:
            return False

    success = await delete_profile(user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")

    return {"message": "Profile deleted successfully"}


@router.get("/checkHost")
async def check_host(user_id: int = Depends(get_current_user)):

    @sync_to_async
    def check_user_is_host(user_id):
        try:
            user = CustomUser.objects.get(id=user_id)
            is_host = user.groups.filter(name="Host").exists()
            return {"is_host": is_host}
        except CustomUser.DoesNotExist:
            return None

    result = await check_user_is_host(user_id)
    if result is None:
        raise HTTPException(status_code=404, detail="User not found")
    return result


@router.get("/getHostDashboardLink")
async def get_host_dashboard_link(user_id: int = Depends(get_current_user)):
    """
    API endpoint for getting Stripe dashboard link for hosts.
    Returns a link to the Stripe dashboard for the user's connected account.
    """

    @sync_to_async
    def get_host_stripe_link(user_id):
        try:
            user = CustomUser.objects.get(id=user_id)

            # Check if stripe account ID exists
            if not user.connectAccountID:
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
                return {"error": f"Failed to get Stripe account link: {str(e)}"}, 400

        except CustomUser.DoesNotExist:
            return None

    result, status_code = await get_host_stripe_link(user_id)
    if result is None:
        raise HTTPException(status_code=404, detail="User not found")

    if status_code != 200:
        raise HTTPException(status_code=status_code, detail=result.get("error"))

    return result


@router.get("/getUserCollege")
async def get_user_college(user_id: int = Depends(get_current_user)):
    """
    API endpoint for getting user's college information.
    Returns the college name and ID associated with the user.
    """

    @sync_to_async
    def get_user_college(user_id):
        try:
            user = CustomUser.objects.get(id=user_id)
            college = user.user_profile.college
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
        raise HTTPException(status_code=404, detail="User not found")

    return college_data


@router.get("/settings")
async def get_user_settings(user_id: int = Depends(get_current_user)):
    """
    API endpoint for retrieving user settings and profile information.
    Returns user profile data and settings.
    """

    @sync_to_async
    def get_settings_async(user_id):
        try:
            user = CustomUser.objects.get(id=user_id)
            profile = get_object_or_404(UserProfile, user=user)

            user_serializer = CustomUserSerializer(user)
            profile_serializer = UserProfileSerializer(profile)

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
            raise HTTPException(status_code=404, detail="User not found")
        return settings_data
    except Exception as e:
        if not isinstance(e, HTTPException):
            error_trace = traceback.format_exc()
            print(f"[get_user_settings] Unhandled exception: {str(e)}\n{error_trace}")
            raise HTTPException(status_code=500, detail="Internal server error")
        raise e


@router.post("/settings")
async def update_user_settings(
    request: Request,
    user_id: int = Depends(get_current_user),
):
    """
    API endpoint for updating user settings and profile information.
    Updates user profile data based on the action provided.
    """
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

    @sync_to_async
    def update_settings_async(user_id, action, form_data, files=None):
        try:
            user = CustomUser.objects.get(id=user_id)
            profile = get_object_or_404(UserProfile, user=user)

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
                        file_content,
                        name=upload_file.filename
                    )
                    
                    # Create and validate form with proper file data
                    form = UpdateProfilePhotoForm(
                        form_data, 
                        django_files, 
                        instance=profile
                    )
                    
                    if form.is_valid():
                        updated_profile = form.save()
                        serializer = UserProfileSerializer(updated_profile)
                        return {
                            "message": "Profile picture updated successfully!",
                            "profile": serializer.data,
                        }
                    print(
                        "[update_settings_async] Validation errors:", 
                        form.errors
                    )
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
                form = UpdatePersonalInfo(form_data, instance=user)
                if form.is_valid():
                    updated_user = form.save()
                    serializer = CustomUserSerializer(updated_user)
                    return {
                        "message": "Personal info updated!",
                        "user": serializer.data,
                    }
                return {"errors": form.errors, "status_code": 400}

            elif action == "updateContactInfo":
                form = UpdateContactInfo(form_data, instance=user)
                if form.is_valid():
                    updated_user = form.save()
                    serializer = CustomUserSerializer(updated_user)
                    return {
                        "message": "Contact info updated!",
                        "user": serializer.data,
                    }
                return {"errors": form.errors, "status_code": 400}

            else:
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
        result = await update_settings_async(user_id, action, data, files)
        if "status_code" in result:
            status_code = result.pop("status_code")
            raise HTTPException(status_code=status_code, detail=result)

        return result
    except Exception as e:
        if not isinstance(e, HTTPException):
            error_trace = traceback.format_exc()
            print("[update_user_settings] Exception:", str(e), error_trace)
            raise HTTPException(status_code=500, detail="Internal server error")
        raise e

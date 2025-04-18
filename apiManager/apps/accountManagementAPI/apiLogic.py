from fastapi import APIRouter, Depends, HTTPException, status, Request, Header, UploadFile, Form
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Optional, Dict, Any
from asgiref.sync import sync_to_async
import traceback
import os

from authenticationApp.models import CustomUser
from authenticationApp.serializers import CustomUserSerializer
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from adminDashboardApp.models import LoginHistoryModel
from eventManagementApp.models import Event
from eventTicketsApp.models import Ticket
from accountManagementApp.models import UserProfile
from accountManagementApp.serializers import UserProfileSerializer
from accountManagementApp.forms import UpdateProfilePhotoForm, UpdatePersonalInfo, UpdateContactInfo
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
        raise HTTPException(status_code=401, detail="Authentication required", headers={"WWW-Authenticate": "Bearer"})
    
    print(f"[profileOverview] Processing request for user_id: {user_id}")
    
    @sync_to_async
    def get_profile_overview(user_id):
        try:
            user = CustomUser.objects.get(id=user_id)
            user_data = {
                "id": user_id,
                "user_id": str(user.user_id),
                "profile_photo": user.user_profile.profile_photo.url if user.user_profile.profile_photo else None,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "username": user.username,
            }
            print(f"[profileOverview] Successfully retrieved profile data for user_id: {user_id}")
            return user_data
        except CustomUser.DoesNotExist:
            print(f"[profileOverview] Error: User with id {user_id} does not exist")
            return None
        except Exception as e:
            error_trace = traceback.format_exc()
            print(f"[profileOverview] Unexpected error retrieving profile for user_id {user_id}: {str(e)}\n{error_trace}")
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
                "profile_photo": user.user_profile.profile_photo.url if user.user_profile.profile_photo else None,
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
                    with open(temp_file.name, 'rb') as f:
                        filename = profile_photo.filename
                        user_profile.profile_photo.save(filename, File(f), save=True)
                finally:
                    # Clean up the temporary file
                    os.unlink(temp_file.name)
                    
            return True
        except CustomUser.DoesNotExist:
            return False
    
    success = await update_profile_detailed(user_id, first_name, last_name, email, profile_photo)
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
            ticket_list.append({
                "ticketId": str(ticket.ticketId),
                "guestFirstName": ticket.guestFirstName,
                "guestLastName": ticket.guestLastName,
                "guestEmail": ticket.guestEmail,
                "eventId": str(ticket.event.eventId),
                "eventTitle": ticket.event.title,
                "date": ticket.event.date,
                "header_photo": ticket.event.header_photo.url if ticket.event.header_photo else None,
                "qrCodeImage": ticket.qrCodeImage.url if ticket.qrCodeImage else None,
                "status": ticket.status,
            })
        
        return ticket_list
        
    ticket_data = await get_user_tickets_async(user_id)
    tickets = [TicketSerializer(**ticket) for ticket in ticket_data]
    
    return {"tickets": tickets}


@router.get("/getUserTickets/{ticketId}/details")
async def get_user_ticket_details(ticketId: str, user_id: int = Depends(get_current_user)):
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
                "header_photo": ticket.event.header_photo.url if ticket.event.header_photo else None,
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
                    "header_photo": event.header_photo.url if event.header_photo else None,
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
                return {"error": "You aren't a host yet. Host your first event to get started."}, 400
            
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
            print(f"[get_user_settings] Unexpected error retrieving settings for user_id {user_id}: {str(e)}\n{error_trace}")
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
    
    # Initialize data dict
    data = {}
    files = {}
    
    try:
        if "application/json" in content_type:
            # Handle JSON request
            json_data = await request.json()
            print(f"[update_user_settings] Received JSON data: {json_data}")
            data = json_data
        else:
            # Handle form data request
            form_data = await request.form()
            print(f"[update_user_settings] Received form data: {dict(form_data)}")
            
            # Extract file uploads from form data
            for key, value in form_data.items():
                if hasattr(value, "filename"):
                    # This is a file upload
                    files[key] = value
                else:
                    # This is regular form data
                    data[key] = value
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"[update_user_settings] Error processing request data: {str(e)}\n{error_trace}")
        raise HTTPException(status_code=400, detail={"error": f"Invalid request data: {str(e)}"})
    
    # Extract action from data
    action = data.get("action")
    if not action:
        raise HTTPException(status_code=400, detail={"error": "Missing required parameter: action"})
        
    @sync_to_async
    def update_settings_async(user_id, action, form_data, files=None):
        try:
            user = CustomUser.objects.get(id=user_id)
            profile = get_object_or_404(UserProfile, user=user)
            if action == "updateProfilePicture":
                if files and 'profile_photo' in files:
                    form = UpdateProfilePhotoForm(form_data, files, instance=profile)
                    if form.is_valid():
                        updated_profile = form.save()
                        serializer = UserProfileSerializer(updated_profile)
                        return {
                            "message": "Profile picture updated successfully!",
                            "profile": serializer.data
                        }
                    return {"errors": form.errors, "status_code": 400}
                # Handle JSON-based profile photo metadata
                elif 'profile_photo' in form_data and isinstance(form_data['profile_photo'], dict):
                    # This is for JSON requests with profile_photo metadata
                    return {
                        "error": "Invalid profile photo upload. Please send the actual file using multipart/form-data.",
                        "status_code": 400
                    }
                    
            elif action == "updatePersonalInfo":
                form = UpdatePersonalInfo(form_data, instance=user)
                if form.is_valid():
                    updated_user = form.save()
                    serializer = CustomUserSerializer(updated_user)
                    return {
                        "message": "Personal information updated successfully!",
                        "user": serializer.data
                    }
                return {"errors": form.errors, "status_code": 400}
                
            elif action == "updateContactInfo":
                form = UpdateContactInfo(form_data, instance=user)
                if form.is_valid():
                    updated_user = form.save()
                    serializer = CustomUserSerializer(updated_user)
                    return {
                        "message": "Contact information updated successfully!",
                        "user": serializer.data
                    }
                return {"errors": form.errors, "status_code": 400}
                
            else:
                return {"error": "Invalid action.", "status_code": 400}
                
        except CustomUser.DoesNotExist:
            return {"error": "User not found", "status_code": 404}
        except Exception as e:
            error_trace = traceback.format_exc()
            print(f"[update_user_settings] Unexpected error updating settings for user_id {user_id}: {str(e)}\n{error_trace}")
            return {"error": f"An error occurred: {str(e)}", "status_code": 500}
    try:
        # We already have the form data and files dictionaries from earlier parsing
        # No need to recreate them
        result = await update_settings_async(user_id, action, data, files)
        if "status_code" in result:
            status_code = result.pop("status_code")
            raise HTTPException(status_code=status_code, detail=result)
        
        return result
    except Exception as e:
        if not isinstance(e, HTTPException):
            error_trace = traceback.format_exc()
            print(f"[update_user_settings] Unhandled exception: {str(e)}\n{error_trace}")
            raise HTTPException(status_code=500, detail="Internal server error")
        raise e
from fastapi import APIRouter, Depends, HTTPException, status, Request, Header, UploadFile
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Optional
from asgiref.sync import sync_to_async
import traceback
import os

from authenticationApp.models import CustomUser
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from adminDashboardApp.models import LoginHistoryModel
from eventManagementApp.models import Event
from eventTicketsApp.models import Ticket
from accountManagementApp.models import UserProfile
from fastapi import Depends
from apiManager.dependencies import get_current_user

from .serializers import TicketSerializer

router = APIRouter()


@router.get("/profileOverview")
async def profileOverview(user_id: int = Depends(get_current_user)):
    """
    API endpoint for getting profile overview.
    Returns user profile data.
    """
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
            return user_data
        except CustomUser.DoesNotExist:
            return None
    
    profile_data = await get_profile_overview(user_id)
    if profile_data is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return profile_data


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
    """
    API endpoint for getting user tickets.
    Returns a list of tickets belonging to the authenticated user.
    """
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
                "qrCodeImage": ticket.qrCodeImage.url if ticket.qrCodeImage else None,
                "status": ticket.status,
            })
        
        return ticket_list
        
    ticket_data = await get_user_tickets_async(user_id)
    tickets = [TicketSerializer(**ticket) for ticket in ticket_data]
    
    return {"tickets": tickets}


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
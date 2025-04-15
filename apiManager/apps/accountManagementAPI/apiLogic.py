from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Optional
from asgiref.sync import sync_to_async
import traceback

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
                "phone_number": user.phone_number,
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
):
    """
    API endpoint for updating detailed profile information.
    Updates user profile data including email and phone number.
    """
    @sync_to_async
    def update_profile_detailed(user_id, first_name, last_name, email):
        try:
            user = CustomUser.objects.get(id=user_id)
            if first_name:
                user.first_name = first_name
            if last_name:
                user.last_name = last_name
            if email:
                user.email = email
            user.save()
            return True
        except CustomUser.DoesNotExist:
            return False
    
    success = await update_profile_detailed(user_id, first_name, last_name, email)
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


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
from fastapi import Depends
from apiManager.dependencies import get_current_user

from .serializers import ProfileOverview

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
    if not profile_data:
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
    if not profile_data:
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
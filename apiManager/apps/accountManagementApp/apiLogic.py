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
    return {"message": f"User {user_id} accessed profile overview."}
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
                "first_name": user.first_name,
                "last_name": user.last_name,
                "username": user.username,
            }
            return user.data
        except CustomUser.DoesNotExist:
            return None
    
    profile_data = await get_profile_overview(request.user.user_id)
    if not profile_data:
        raise HTTPException(status_code=404, detail="Event not found")
    return profile_data
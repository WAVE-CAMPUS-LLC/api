from datetime import datetime
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
)
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Optional, Dict, Any
from asgiref.sync import sync_to_async
import traceback
import os
from django.core.files.base import ContentFile
from django.conf import settings

from authenticationApp.models import CustomUser
from authenticationApp.serializers import CustomUserSerializer
from django.contrib.auth import authenticate

from apiManager.dependencies import get_current_user
from django.shortcuts import get_object_or_404


router = APIRouter()


@router.get("/dashboard")
async def admin_dashboard():
    print(f"[admin_dashboard] API called with user_id:")
    return {"message": "Admin dashboard"}

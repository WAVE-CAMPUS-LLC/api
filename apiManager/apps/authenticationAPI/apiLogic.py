from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Optional
from channels.db import database_sync_to_async
import traceback

from authenticationApp.models import CustomUser
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from authenticationApp.serializers import CustomUserSerializer
from adminDashboardApp.models import LoginHistoryModel
from authenticationApp.forms import MobileUserJoinForm

from .serializers import LoginRequest, JoinRequest
from apiManager.utilities.form_fields import get_form_fields
from apiManager.utilities.notify_by_bot import notify_by_bot
from apiManager.utilities.device_info import get_device_info

from jose import jwt
from datetime import datetime, timedelta
import secrets

from dotenv import load_dotenv
import os

router = APIRouter()


load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 183  # ~6 months to match Django settings
REFRESH_TOKEN_EXPIRE_DAYS = 365  # 1 year to match Django settings
SECRET_ADMIN_URL = os.getenv("SECRET_ADMIN_URL")
SECRET_ADMIN_KEY = os.getenv("SECRET_ADMIN_KEY")
SECRET_ADMIN_USER = os.getenv("SECRET_ADMIN_USER")


class AdminURLCheckRequest(BaseModel):
    urlKey: str


class AdminKeyCheckRequest(BaseModel):
    adminKey: str


class AdminUserCheckRequest(BaseModel):
    userEmail: str


@router.get("/ping")
async def ping(
    request: Request,
    platform: Optional[str] = None,
):
    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:
        return {"message": "Authentication API is running!"}
    except Exception as e:
        await notify_by_bot(
            f"**[API: ping]** \n\n Error in ping endpoint: error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(status_code=500, detail=f"Error in ping endpoint: {str(e)}")


@router.post("/check-admin-url")
async def check_admin_url(
    payload: AdminURLCheckRequest,
    request: Request,
    platform: Optional[str] = None,
):
    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:
        if payload.urlKey:
            print(f"[check_admin_url] function called with: {payload.urlKey}")
        elif payload:
            print(f"[check_admin_url] function called incorrect body: {payload}")
        else:
            print(f"[check_admin_url] function called no body")

        if payload.urlKey == SECRET_ADMIN_URL:
            return JSONResponse(content={"match": True})
        else:
            return JSONResponse(content={"match": False}, status_code=401)
    except Exception as e:
        await notify_by_bot(
            f"**[API: check_admin_url]** \n\n Error checking admin URL: error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(
            status_code=500, detail=f"Error checking admin URL: {str(e)}"
        )


@router.post("/check-admin-key")
async def check_admin_key(
    payload: AdminKeyCheckRequest,
    request: Request,
    platform: Optional[str] = None,
):
    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:
        if payload.adminKey:
            print(f"[check_admin_key] function called with: {payload.adminKey}")
        elif payload:
            print(f"[check_admin_key] function called incorrect body: {payload}")
        else:
            print(f"[check_admin_key] function called no body")
        if payload.adminKey == SECRET_ADMIN_KEY:
            return JSONResponse(content={"match": True})
        else:
            return JSONResponse(content={"match": False}, status_code=401)
    except Exception as e:
        await notify_by_bot(
            f"**[API: check_admin_key]** \n\n Error checking admin key: error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(
            status_code=500, detail=f"Error checking admin key: {str(e)}"
        )


@router.post("/check-admin-user")
async def check_admin_user(
    payload: AdminUserCheckRequest,
    request: Request,
    platform: Optional[str] = None,
):
    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:
        if payload.userEmail:
            print(f"[check_admin_user] function called with: {payload.userEmail}")
        elif payload:
            print(f"[check_admin_user] function called incorrect body: {payload}")
        else:
            print(f"[check_admin_user] function called no body")
        if payload.userEmail == SECRET_ADMIN_USER:
            return JSONResponse(content={"match": True})
        else:
            return JSONResponse(content={"match": False}, status_code=401)
    except Exception as e:
        await notify_by_bot(
            f"**[API: check_admin_user]** \n\n Error checking admin user: error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(
            status_code=500, detail=f"Error checking admin user: {str(e)}"
        )


@router.post("/login")
async def login_api(
    request: Request, login_data: LoginRequest, platform: Optional[str] = None
):
    """
    API endpoint for user authentication using email/username and password.
    Returns JWT tokens and user data upon successful authentication.
    """
    print(f"[login_api] Function called with identifier: {login_data.identifier}")

    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def login_sync(identifier, password, client_ip):
        try:
            if not identifier or not password:
                return (
                    None,
                    {"error": "Please provide both identifier and password"},
                    status.HTTP_400_BAD_REQUEST,
                )

            # Check if the identifier is an email or username
            user = (
                CustomUser.objects.filter(email=identifier).first()
                or CustomUser.objects.filter(username=identifier).first()
            )

            if not user:
                return (
                    None,
                    {"error": "Invalid email/username or password"},
                    status.HTTP_401_UNAUTHORIZED,
                )

            # Authenticate using email
            authenticated_user = authenticate(
                request=None, email=user.email, password=password
            )

            if not authenticated_user:
                return (
                    None,
                    {"error": "Invalid email/username or password"},
                    status.HTTP_401_UNAUTHORIZED,
                )

            # Create login history
            LoginHistoryModel.objects.create(
                user=authenticated_user,
                email=authenticated_user.email,
                ip_address=client_ip,
            )

            # Serialize the user data
            user_serializer = CustomUserSerializer(authenticated_user)
            # Access token with additional claims for better security and debugging
            access_payload = {
                "sub": str(authenticated_user.id),
                "exp": datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS),
                "iat": datetime.utcnow(),  # Issued at time
                "type": "access",
                "username": authenticated_user.username,
                "jti": secrets.token_hex(16),  # Unique token ID for tracking
            }
            print(
                f"[login_api] Generating access token for user {authenticated_user.id} with expiry in {ACCESS_TOKEN_EXPIRE_DAYS} days"
            )
            access_token = jwt.encode(access_payload, SECRET_KEY, algorithm=ALGORITHM)

            # Refresh token
            refresh_payload = {
                "sub": str(authenticated_user.id),
                "exp": datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
                "iat": datetime.utcnow(),  # Issued at time
                "type": "refresh",
                "jti": secrets.token_hex(16),  # Unique token ID for tracking
            }
            print(
                f"[login_api] Generating refresh token for user {authenticated_user.id} with expiry in {REFRESH_TOKEN_EXPIRE_DAYS} days"
            )
            refresh_token = jwt.encode(refresh_payload, SECRET_KEY, algorithm=ALGORITHM)

            return (
                {
                    "access": access_token,
                    "refresh": refresh_token,
                    "user": user_serializer.data,
                },
                None,
                status.HTTP_200_OK,
            )

        except Exception as e:
            traceback_str = traceback.format_exc()
            print(f"Login error: {str(e)}\n{traceback_str}")
            return (
                None,
                {"error": "An unexpected error occurred"},
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # Get client IP from request
    client_ip = request.client.host if request.client else None

    # Call the synchronous function with FastAPI request parameters
    result, error, status_code = await login_sync(
        login_data.identifier, login_data.password, client_ip
    )

    if error:
        print(
            f"[login_api] Authentication failed with status code {status_code}: {error}"
        )
        await notify_by_bot(
            f"**[API: login_api]** \n\n Authentication failed: identifier={login_data.identifier}, status={status_code} \n\n Platform: {platform} \n\n Error: {error}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        return JSONResponse(content=error, status_code=status_code)

    print(f"[login_api] Authentication successful with status code {status_code}")
    return JSONResponse(content=result, status_code=status_code)


@router.post("/logout")
async def logout_api(
    request: Request, Authorization: str = Header(None), platform: Optional[str] = None
):
    """
    API endpoint for user logout.
    Invalidates the refresh token and clears session data.
    """
    print(
        f"[logout_api] Function called with Authorization header: {Authorization[:10]}..."
        if Authorization
        else "[logout_api] Function called without Authorization header"
    )

    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:
        # Invalidate the refresh token (if applicable)
        # This can be done by removing it from the database or marking it as invalid
        # For simplicity, we'll just return a success message

        response = {"message": "Logout successful"}
        print(
            f"[logout_api] Logout successful, returning status code {status.HTTP_200_OK}"
        )
        return JSONResponse(content=response, status_code=status.HTTP_200_OK)
    except Exception as e:
        traceback_str = traceback.format_exc()
        print(f"Logout error: {str(e)}\n{traceback_str}")
        await notify_by_bot(
            f"**[API: logout_api]** \n\n Unexpected error: {str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        return JSONResponse(
            content={"error": "An unexpected error occurred"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get("/join")
async def get_join_form(request: Request, platform: Optional[str] = None):
    print(
        f"[get_join_form] Function called with X-Platform: {request.headers.get('X-Platform')}"
    )

    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    is_mobile = request.headers.get("X-Platform") == "mobile"
    FormClass = MobileUserJoinForm
    fields_info = get_form_fields(FormClass)
    print(f"[get_join_form] Returning form fields, field count: {len(fields_info)}")
    return JSONResponse(content=fields_info, status_code=status.HTTP_200_OK)


@router.post("/join")
async def join_api(request: Request, platform: Optional[str] = None):
    print("[join_api] Function called")

    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:
        # Get form data from request - this is async and fast
        form_data = await request.form()
        # Convert form data to dict
        form_dict = dict(form_data)
        print(
            f"[join_api] Received form data with fields: {', '.join(form_dict.keys())}"
        )

        # Run user creation in a background task to improve response time
        @database_sync_to_async
        def validate_and_create_user(form_data):
            # Minimal validation for required fields to speed things up
            errors = {}

            # Check required fields (email, username, passwords)
            if not form_data.get("email"):
                errors["email"] = ["Email is required"]
            if not form_data.get("username"):
                errors["username"] = ["Username is required"]
            if not form_data.get("password1"):
                errors["password1"] = ["Password is required"]
            if form_data.get("password1") != form_data.get("password2"):
                errors["password2"] = ["Passwords do not match"]

            # Return errors if basic validation failed
            if errors:
                return errors, status.HTTP_400_BAD_REQUEST
            # Use the form but with optimizations
            form = MobileUserJoinForm(form_data)
            if form.is_valid():
                # Create user with optimized save
                user = form.save(commit=False)
                user.is_active = True
                user.email_verified = True
                user.is_staff = False
                user.is_superuser = False
                user.is_superadmin = False
                user.save()

                # Assign "Member" and "Verified" groups to the user
                from django.contrib.auth.models import Group

                member_group, _ = Group.objects.get_or_create(name="Member")
                verified_group, _ = Group.objects.get_or_create(name="Verified")
                user.groups.add(member_group)
                user.groups.add(verified_group)

                return None, status.HTTP_201_CREATED
            else:
                return form.errors, status.HTTP_400_BAD_REQUEST

        # Run validation and user creation
        errors, status_code = await validate_and_create_user(form_dict)

        if errors:
            print(f"[join_api] Registration failed with errors: {errors}")
            return JSONResponse(content=errors, status_code=status_code)
        else:
            print(
                f"[join_api] User registered successfully with status code {status_code}"
            )
            return JSONResponse(
                content={"message": "User registered successfully"},
                status_code=status_code,
            )
    except Exception as e:
        traceback_str = traceback.format_exc()
        print(f"Registration error: {str(e)}\n{traceback_str}")
        await notify_by_bot(
            f"**[API: join_api]** \n\n Unexpected error: {str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        return JSONResponse(
            content={"error": f"An unexpected error occurred: {str(e)}"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# @router.post("/join/verify")
# async def join_verify_api(request: Request, platform: Optional[str] = None):
#     print("[join_verify_api] Function called")

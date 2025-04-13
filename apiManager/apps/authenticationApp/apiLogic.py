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
from authenticationApp.serializers import CustomUserSerializer
from adminDashboardApp.models import LoginHistoryModel
from authenticationApp.forms import MobileUserJoinForm

from .serializers import LoginRequest, JoinRequest
from .utilities import get_form_fields


from jose import jwt
from datetime import datetime, timedelta

from dotenv import load_dotenv
import os

router = APIRouter()


load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY") 
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7


@router.get("/ping")
async def ping():
    return {"message": "Authentication API is running!"}

@router.post("/login")
async def login_api(request: Request, login_data: LoginRequest):
    """
    API endpoint for user authentication using email/username and password.
    Returns JWT tokens and user data upon successful authentication.
    """
    @sync_to_async
    def login_sync(identifier, password, client_ip):
        try:
            if not identifier or not password:
                return None, {"error": "Please provide both identifier and password"}, status.HTTP_400_BAD_REQUEST

            # Check if the identifier is an email or username
            user = (
                CustomUser.objects.filter(email=identifier).first()
                or CustomUser.objects.filter(username=identifier).first()
            )

            if not user:
                return None, {"error": "Invalid email/username or password"}, status.HTTP_401_UNAUTHORIZED

            # Authenticate using email
            authenticated_user = authenticate(request=None, email=user.email, password=password)

            if not authenticated_user:
                return None, {"error": "Invalid email/username or password"}, status.HTTP_401_UNAUTHORIZED

            # Create login history
            LoginHistoryModel.objects.create(
                user=authenticated_user,
                email=authenticated_user.email,
                ip_address=client_ip,
            )

            # Serialize the user data
            user_serializer = CustomUserSerializer(authenticated_user)
            
            # Access token
            access_payload = {
                "sub": str(authenticated_user.id),
                "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
                "type": "access"
            }
            access_token = jwt.encode(access_payload, SECRET_KEY, algorithm=ALGORITHM)

            # Refresh token
            refresh_payload = {
                "sub": str(authenticated_user.id),
                "exp": datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
                "type": "refresh"
            }
            refresh_token = jwt.encode(refresh_payload, SECRET_KEY, algorithm=ALGORITHM)
            
            return {
                "access": access_token,
                "refresh": refresh_token,
                "user": user_serializer.data,
            }, None, status.HTTP_200_OK


        except Exception as e:
            traceback_str = traceback.format_exc()
            print(f"Login error: {str(e)}\n{traceback_str}")
            return None, {"error": "An unexpected error occurred"}, status.HTTP_500_INTERNAL_SERVER_ERROR

    # Get client IP from request
    client_ip = request.client.host if request.client else None
    
    # Call the synchronous function with FastAPI request parameters
    result, error, status_code = await login_sync(
        login_data.identifier, 
        login_data.password, 
        client_ip
    )
    
    if error:
        return JSONResponse(content=error, status_code=status_code)
    
    return JSONResponse(content=result, status_code=status_code)
        
        

@router.post("/logout")
async def logout_api(request: Request, Authorization: str = Header(None)):
    """
    API endpoint for user logout.
    Invalidates the refresh token and clears session data.
    """
    try:
        # Invalidate the refresh token (if applicable)
        # This can be done by removing it from the database or marking it as invalid
        # For simplicity, we'll just return a success message

        return JSONResponse(
            content={"message": "Logout successful"}, status_code=status.HTTP_200_OK
        )
    except Exception as e:
        traceback_str = traceback.format_exc()
        print(f"Logout error: {str(e)}\n{traceback_str}")
        return JSONResponse(
            content={"error": "An unexpected error occurred"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
        
        
@router.get("/join")
async def get_join_form(request: Request):
   is_mobile = request.headers.get("X-Platform") == "mobile"
   FormClass = MobileUserJoinForm
   fields_info = get_form_fields(FormClass)
   return JSONResponse(content=fields_info, status_code=status.HTTP_200_OK)


@router.post("/join")
async def join_api(request: Request):
    try:
        # Get form data from request - this is async and fast
        form_data = await request.form()
        # Convert form data to dict
        form_dict = dict(form_data)
        
        # Run user creation in a background task to improve response time
        @sync_to_async
        def validate_and_create_user(form_data):
            # Minimal validation for required fields to speed things up
            errors = {}
            
            # Check required fields (email, username, passwords)
            if not form_data.get('email'):
                errors['email'] = ['Email is required']
            if not form_data.get('username'):
                errors['username'] = ['Username is required']
            if not form_data.get('password1'):
                errors['password1'] = ['Password is required']
            if form_data.get('password1') != form_data.get('password2'):
                errors['password2'] = ['Passwords do not match']
            
            # Return errors if basic validation failed
            if errors:
                return errors, status.HTTP_400_BAD_REQUEST
            
            # Use the form but with optimizations
            form = MobileUserJoinForm(form_data)
            if form.is_valid():
                # Create user with optimized save
                user = form.save(commit=False)
                user.is_active = True
                user.save()
                return None, status.HTTP_201_CREATED
            else:
                return form.errors, status.HTTP_400_BAD_REQUEST
        
        # Run validation and user creation
        errors, status_code = await validate_and_create_user(form_dict)
        
        if errors:
            return JSONResponse(content=errors, status_code=status_code)
        else:
            return JSONResponse(content={"message": "User registered successfully"}, status_code=status_code)
    except Exception as e:
        traceback_str = traceback.format_exc()
        print(f"Registration error: {str(e)}\n{traceback_str}")
        return JSONResponse(
            content={"error": f"An unexpected error occurred: {str(e)}"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
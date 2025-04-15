from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from typing import Optional
from asgiref.sync import sync_to_async
from django.core.mail import send_mail
from django.conf import settings
from django.utils.crypto import get_random_string
from django.shortcuts import get_object_or_404

# Django imports
from adminDashboardApp.models import College
from collegeManagementApp.forms import JoinCollegeForm
from authenticationApp.models import CustomUser
from apiManager.dependencies import get_current_user

# Create a router for college joining endpoints
router = APIRouter()

# Pydantic model for the join college request
class JoinCollegeRequest(BaseModel):
    email: EmailStr
    
    class Config:
        schema_extra = {
            "example": {
                "email": "student@university.edu"
            }
        }

# Response model for a successful join request
class JoinCollegeResponse(BaseModel):
    message: str
    next_step: str
    collegeId: str
    
# Error response model
class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None

@router.post("/{collegeId}/join", 
             response_model=JoinCollegeResponse,
             responses={
                 400: {"model": ErrorResponse},
                 500: {"model": ErrorResponse}
             })
async def join_college(
    collegeId: str,
    join_request: JoinCollegeRequest,
    request: Request,
    current_user: CustomUser = Depends(get_current_user)
):
    """
    Send a verification email to join a college.
    
    This endpoint:
    1. Validates the email belongs to the college domain
    2. Sends a verification code to the provided email
    3. Stores verification data in the session
    
    Returns verification status and next steps
    """
    
    @sync_to_async
    def process_join_request(collegeId, email, user):
        try:
            college = get_object_or_404(College, collegeId=collegeId)
            
            # Create form data dict with email
            form_data = {"email": email}
            
            # Validate using the Django form
            join_form = JoinCollegeForm(form_data, college=college)
            join_form.user = user
            
            if not join_form.is_valid():
                # Extract error messages from form
                errors = dict(join_form.errors)
                error_message = "; ".join([f"{k}: {v[0]}" for k, v in errors.items()])
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=error_message
                )
            
            # Generate verification code
            code = get_random_string(6, allowed_chars="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
            
            # Store in session
            request.session["verification_code"] = code
            request.session["college_id"] = str(collegeId)
            request.session["user_email"] = email
            
            # Send verification email
            send_mail(
                "Verify your campus email",
                f"Your verification code is: {code}",
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False
            )
            
            return {
                "message": "Verification email sent successfully",
                "next_step": "verify",
                "collegeId": collegeId
            }
            
        except HTTPException as e:
            # Re-raise HTTP exceptions
            raise e
        except Exception as e:
            # Handle other exceptions
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to send verification email: {str(e)}"
            )
    
    # Process the request
    result = await process_join_request(collegeId, join_request.email, current_user)
    return result

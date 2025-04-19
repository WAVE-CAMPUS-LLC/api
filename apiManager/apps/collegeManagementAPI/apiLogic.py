from asgiref.sync import sync_to_async
from fastapi import APIRouter, Depends, HTTPException, status, Request, Body
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Optional

# Django imports
from adminDashboardApp.models import College

# Serializers
from .serializers import CollegeExplorePage, CollegeDetails, VerificationRequest


router = APIRouter()


@router.get("/ping")
async def ping():
    return {"message": "Pong!"}


@router.get("/explore")
async def explore_colleges():
    print("[DEBUG - explore_colleges] Function called")
    try:

        @sync_to_async
        def get_colleges():
            college_list = []
            for college in College.objects.all():
                college_list.append(
                    {
                        "collegeId": str(college.collegeId),  # Convert UUID to string
                        "name": college.name,
                        "campus_image": (
                            college.campus_image.url if college.campus_image else None
                        ),
                        "state": college.state,
                        "city": college.city,
                        "logo": college.logo.url if college.logo else None,
                    }
                )
            return college_list

        college_data = await get_colleges()
        print(f"[DEBUG - explore_colleges] Retrieved {len(college_data)} colleges from database")
        colleges = [CollegeExplorePage(**college) for college in college_data]

        response = {"colleges": colleges}
        print(f"[DEBUG - explore_colleges] Returning response with {len(colleges)} colleges")
        return response
    except Exception as e:
        # Log the error for debugging
        print(f"Error in explore_colleges: {str(e)}")
        # Return a more helpful error response
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch college data: {str(e)}",
        )


@router.get("/college/{collegeId}/details")
async def get_college_details(collegeId: str):
    print(f"[DEBUG - get_college_details] Function called with collegeId: {collegeId}")
    try:

        @sync_to_async
        def get_college_details_data(collegeId):
            try:
                college = College.objects.get(collegeId=collegeId)
                return {
                    "collegeId": str(college.collegeId),
                    "name": college.name,
                    "address": college.address,
                    "city": college.city,
                    "state": college.state,
                    "zip_code": college.zip_code,
                    "campus_image": (
                        college.campus_image.url if college.campus_image else None
                    ),
                    "motto": college.motto,
                    "contact_website": college.contact_website,
                    "email_domain": college.email_domain,
                    "logo": college.logo.url if college.logo else None,
                }

            except College.DoesNotExist:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="College not found",
                )

        college_details = await get_college_details_data(collegeId)
        print(f"[DEBUG - get_college_details] Retrieved details for college: {college_details['name']}")
        response = {"collegeDetails": CollegeDetails(**college_details)}
        print(f"[DEBUG - get_college_details] Returning college details response")
        return response

    except Exception as e:
        # Log the error for debugging
        print(f"Error in get_college_details: {str(e)}")
        # Return a more helpful error response
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch college details: {str(e)}",
        )


@router.get("/college/{collegeId}/events")
async def get_college_events(collegeId: str):
    print(f"[DEBUG - get_college_events] Function called with collegeId: {collegeId}")
    try:

        @sync_to_async
        def get_college_events_data(collegeId):
            try:
                college = College.objects.get(collegeId=collegeId)

                # Get events through the CollegeEventLink model using the correct related name
                college_event_links = college.college_events.all()
                events = [link.event for link in college_event_links]

                return [
                    {
                        "eventId": str(event.eventId),
                        "title": event.title,
                        "date": event.date,
                        "location": f"{event.city}, {event.state}",
                        "description": event.description,
                        "header_photo": (
                            event.header_photo.url if event.header_photo else None
                        ),
                    }
                    for event in events
                ]

            except College.DoesNotExist:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="College not found",
                )

        college_events = await get_college_events_data(collegeId)
        print(f"[DEBUG - get_college_events] Retrieved {len(college_events)} events for college")
        response = {"events": college_events}
        print(f"[DEBUG - get_college_events] Returning events response")
        return response

    except Exception as e:
        # Log the error for debugging
        print(f"Error in get_college_events: {str(e)}")
        # Return a more helpful error response
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch college events: {str(e)}",
        )


@router.get("/college/{collegeId}/members")
async def get_college_members(collegeId: str, page: int = 1, limit: int = 20):
    print(f"[DEBUG - get_college_members] Function called with collegeId: {collegeId}, page: {page}, limit: {limit}")
    try:

        @sync_to_async
        def get_college_members_data(collegeId, page, limit):
            try:
                college = College.objects.get(collegeId=collegeId)

                # Get members through the UserProfile model with optimizations
                from accountManagementApp.models import UserProfile
                from django.db.models import Count

                # Calculate total count separately for pagination info
                total_count = UserProfile.objects.filter(college=college).count()

                # Find all user profiles associated with this college
                # Using pagination and select_related for the user data
                # Only fetch the fields we actually need
                offset = (page - 1) * limit
                members = (
                    UserProfile.objects.filter(college=college)
                    .select_related("user")
                    .only(
                        "id",
                        "profile_photo",
                        "user__id",
                        "user__first_name",
                        "user__last_name",
                        "user__username",
                    )
                    .order_by("user__first_name", "user__last_name")[
                        offset : offset + limit
                    ]
                )

                # Convert to list of dictionaries for JSON response
                member_data = [
                    {
                        "id": str(member.id),
                        "userId": str(member.user.id),
                        "first_name": member.user.first_name,
                        "last_name": member.user.last_name,
                        "profile_photo": (
                            member.profile_photo.url if member.profile_photo else None
                        ),
                        "username": member.user.username,
                    }
                    for member in members
                ]

                # Add pagination information
                pagination = {
                    "total": total_count,
                    "pages": (total_count + limit - 1) // limit,  # Ceiling division
                    "current_page": page,
                    "has_next": offset + limit < total_count,
                    "has_prev": page > 1,
                }

                return member_data, pagination

            except College.DoesNotExist:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="College not found",
                )

        member_data, pagination = await get_college_members_data(collegeId, page, limit)
        print(f"[DEBUG - get_college_members] Retrieved {len(member_data)} members, page {pagination['current_page']} of {pagination['pages']}")
        response = {"members": member_data, "pagination": pagination}
        print(f"[DEBUG - get_college_members] Returning members response")
        return response

    except Exception as e:
        # Log the error for debugging
        print(f"Error in get_college_members: {str(e)}")
        # Return a more helpful error response
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch college members: {str(e)}",
        )


# Class for join college request
class JoinCollegeRequest(BaseModel):
    email: str

    class Config:
        json_schema_extra = {"example": {"email": "student@university.edu"}}


@router.post("/college/{collegeId}/join")
async def join_college(collegeId: str, join_request: JoinCollegeRequest):
    """
    Send a verification email to join a college.

    This endpoint:
    1. Validates the email belongs to the college domain
    2. Sends a verification code to the provided email
    3. Stores verification data in database
    """
    print(f"[DEBUG - join_college] Function called with collegeId: {collegeId}, email: {join_request.email}")
    try:

        @sync_to_async
        def process_join_request(collegeId, email):
            try:
                from django.shortcuts import get_object_or_404
                from django.utils.crypto import get_random_string
                from django.core.mail import send_mail
                from django.conf import settings
                from django.utils import timezone
                from datetime import timedelta
                from collegeManagementApp.forms import JoinCollegeForm
                from collegeManagementApp.models import VerificationCode

                # Get the college
                college = get_object_or_404(College, collegeId=collegeId)

                # Get current user - we'll need to replace this with proper auth
                from django.contrib.auth import get_user_model

                User = get_user_model()
                user = User.objects.first()  # Replace with proper auth logic

                # Create form data with email
                form_data = {"email": email}

                # Validate using the Django form
                join_form = JoinCollegeForm(form_data, college=college)
                join_form.user = user

                if not join_form.is_valid():
                    # Extract error messages from form
                    errors = dict(join_form.errors)
                    error_message = "; ".join(
                        [f"{k}: {v[0]}" for k, v in errors.items()]
                    )
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST, detail=error_message
                    )

                # Generate verification code
                code = get_random_string(
                    6, allowed_chars="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
                )

                # Set expiration time (1 hour from now)
                expiry_time = timezone.now() + timedelta(hours=1)

                # Delete any existing verification codes for this user and college
                VerificationCode.objects.filter(user=user, college=college).delete()

                # Store code in database
                verification = VerificationCode.objects.create(
                    code=code,
                    user=user,
                    college=college,
                    email=email,
                    expires_at=expiry_time,
                )

                # Send verification email
                send_mail(
                    "Verify your campus email",
                    f"Your verification code is: {code}",
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    fail_silently=False,
                )

                return {
                    "message": "Verification email sent successfully",
                    "next_step": "verify",
                    "collegeId": collegeId,
                    "expires_at": expiry_time,
                }

            except HTTPException as e:
                # Re-raise HTTP exceptions
                raise e
            except Exception as e:
                # Handle other exceptions
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to send verification email: {str(e)}",
                )

        # Process the request
        result = await process_join_request(collegeId, join_request.email)
        print(f"[DEBUG - join_college] Verification email sent to: {join_request.email}")
        print(f"[DEBUG - join_college] Returning result: {result['message']}")
        return result

    except Exception as e:
        # Log the error for debugging
        print(f"Error in join_college: {str(e)}")
        # Return a more helpful error response
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process join college request: {str(e)}",
        )


@router.post("/college/{collegeId}/verify")
async def verify_join_college(collegeId: str, verification: VerificationRequest):
    """
    Verify a college join code and complete the membership process.

    This endpoint:
    1. Validates the verification code against stored code in database
    2. Updates user profile with college association
    3. Creates membership record linking user to college
    """
    print(f"[DEBUG - verify_join_college] Function called with collegeId: {collegeId}, code: {verification.code}")
    try:

        @sync_to_async
        def process_verification(collegeId, code):
            try:
                from django.shortcuts import get_object_or_404
                from django.utils import timezone
                from accountManagementApp.models import UserProfile
                from collegeManagementApp.models import Membership, VerificationCode
                from collegeManagementApp.forms import VerifyCollegeJoinForm

                college = get_object_or_404(College, collegeId=collegeId)

                from django.contrib.auth import get_user_model

                User = get_user_model()
                user = User.objects.first()  # Replace with proper auth logic

                # Basic code format validation
                form_data = {"code": code}
                verify_form = VerifyCollegeJoinForm(form_data)

                if not verify_form.is_valid():
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid verification code format",
                    )

                # Find the verification code in the database
                verification_obj = VerificationCode.objects.filter(
                    user=user, college=college, code=code, used=False
                ).first()

                if not verification_obj:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid or expired verification code. Please request a new code.",
                    )

                # Check if the code has expired
                if verification_obj.is_expired():
                    verification_obj.delete()
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Verification code has expired. Please request a new code.",
                    )

                # Update user profile with college association
                user_profile = get_object_or_404(UserProfile, user=user)
                user_profile.college = college
                user_profile.save()

                # Create college membership
                membership, created = Membership.objects.get_or_create(
                    user=user, college=college
                )

                # Mark the verification code as used
                verification_obj.used = True
                verification_obj.save()

                return {
                    "message": f"You have successfully joined {college.name}",
                    "college": {"id": str(college.collegeId), "name": college.name},
                    "membership_created": created,
                }

            except HTTPException as e:
                raise e
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to verify college join: {str(e)}",
                )

        # Process the verification
        result = await process_verification(collegeId, verification.code)
        print(f"[DEBUG - verify_join_college] Verification processed successfully")
        print(f"[DEBUG - verify_join_college] Returning result: {result['message']}")
        return result

    except Exception as e:
        # Log the error for debugging
        print(f"Error in verify_join_college: {str(e)}")
        # Return a more helpful error response
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process verification: {str(e)}",
        )


@router.post("/college/{collegeId}/leave")
async def leave_college(collegeId: str):
    """
    Leave a college and remove membership.

    This endpoint:
    1. Validates the college ID
    2. Removes the user from the college membership
    """
    print(f"[DEBUG - leave_college] Function called with collegeId: {collegeId}")
    try:

        @sync_to_async
        def process_leave_request(collegeId):
            try:
                from django.shortcuts import get_object_or_404
                from accountManagementApp.models import UserProfile
                from collegeManagementApp.models import Membership, College

                # Get the college and user profile
                college = get_object_or_404(College, collegeId=collegeId)

                from django.contrib.auth import get_user_model

                User = get_user_model()
                user = User.objects.first()  # Replace with proper auth logic

                user_profile = get_object_or_404(UserProfile, user=user)

                # Check if the user is a member of the college
                if user_profile.college != college:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="You are not a member of this college.",
                    )

                # Remove membership and update user profile
                Membership.objects.filter(user=user, college=college).delete()
                user_profile.college = None  # or set to another college if needed
                user_profile.save()

                return {
                    "message": f"You have successfully left {college.name}",
                    "college": {"id": str(college.collegeId), "name": college.name},
                }

            except HTTPException as e:
                raise e
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to leave college: {str(e)}",
                )

        # Process the leave request
        result = await process_leave_request(collegeId)
        print(f"[DEBUG - leave_college] College membership removed successfully")
        print(f"[DEBUG - leave_college] Returning result: {result['message']}")
        return result

    except Exception as e:
        # Log the error for debugging
        print(f"Error in leave_college: {str(e)}")
        # Return a more helpful error response
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process leave request: {str(e)}",
        )

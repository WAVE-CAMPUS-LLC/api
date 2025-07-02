from typing import Optional
from channels.db import database_sync_to_async
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
import bleach
import uuid


from ambassadorManagement.forms import AmbassadorApplicationForm
from ambassadorManagement.models import AmbassadorApplication
from authenticationApp.models import CustomUser

from apiManager.dependencies import get_current_user
from apiManager.utilities.notify_by_bot import notify_by_bot
from apiManager.utilities.device_info import get_device_info
from apiManager.utilities.form_fields import get_form_fields


router = APIRouter()


@router.get("/tide/application/form")
async def get_tide_form_fields(
    request: Request,
    platform: Optional[str] = None,
):
    print(
        f"[get_join_form] Function called with X-Platform: {request.headers.get('X-Platform')}"
    )

    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    FormClass = AmbassadorApplicationForm
    fields_info = get_form_fields(FormClass)
    return JSONResponse(content=fields_info, status_code=status.HTTP_200_OK)


@router.post("/tide/apply")
async def apply_for_tide_program(request: Request, platform: Optional[str] = None):
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:
        # Get form data from request - this is async and fast
        form_data = await request.form()
        # Convert form data to dict
        form_dict = dict(form_data)

        @database_sync_to_async
        def validate_and_submit_application(form_data):
            try:
                # Sanitize input data
                sanitized_data = {}
                for key, value in form_data.items():
                    if isinstance(value, str):
                        sanitized_data[key] = bleach.clean(value.strip())
                    else:
                        sanitized_data[key] = value

                print(
                    f"[apply_for_tide_program] Form data keys: {', '.join(sanitized_data.keys())}"
                )

                # Create the form instance with sanitized data
                form = AmbassadorApplicationForm(sanitized_data)

                if form.is_valid():
                    # Check if email already exists to prevent duplicates
                    email = sanitized_data.get("email")

                    # Check if this specific user already has tide ambassador role
                    existing_tide_ambassador = CustomUser.objects.filter(
                        email=email, is_tide_ambassador=True
                    ).exists()

                    # Check if application already exists for this email
                    existing_application = AmbassadorApplication.objects.filter(
                        email=email
                    ).exists()

                    if existing_tide_ambassador:
                        return {
                            "success": False,
                            "errors": {
                                "email": [
                                    "You already have a Tide Ambassador account. Please contact support if you need assistance."
                                ]
                            },
                            "status_code": status.HTTP_400_BAD_REQUEST,
                        }

                    if existing_application:
                        return {
                            "success": False,
                            "errors": {
                                "email": [
                                    "An application with this email already exists. Please check your application status or contact support."
                                ]
                            },
                            "status_code": status.HTTP_400_BAD_REQUEST,
                        }

                    # Save the application
                    application = form.save(commit=False)
                    application.status = "pending"  # Ensure status is set to pending
                    application.save()

                    print(
                        f"[apply_for_tide_program] Application submitted successfully: {application.full_name}"
                    )

                    return {
                        "success": True,
                        "message": "Application submitted successfully! We'll review your application and get back to you soon.",
                        "application_id": str(application.app_id),
                        "status_code": status.HTTP_201_CREATED,
                    }
                else:
                    print(
                        f"[apply_for_tide_program] Form validation failed: {form.errors}"
                    )
                    return {
                        "success": False,
                        "errors": form.errors,
                        "status_code": status.HTTP_400_BAD_REQUEST,
                    }

            except Exception as e:
                print(f"[apply_for_tide_program] Database error: {str(e)}")
                return {
                    "success": False,
                    "error": f"An error occurred while processing your application: {str(e)}",
                    "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                }

        # Execute the validation and submission
        result = await validate_and_submit_application(form_dict)

        # Handle the result
        status_code = result.pop("status_code", status.HTTP_200_OK)

        if not result.get("success", True):
            print(
                f"[apply_for_tide_program] Application failed with status {status_code}"
            )
            return JSONResponse(content=result, status_code=status_code)

        print(f"[apply_for_tide_program] Application submitted successfully")
        return JSONResponse(content=result, status_code=status_code)

    except Exception as e:
        print(f"[apply_for_tide_program] Unexpected error: {str(e)}")
        await notify_by_bot(
            f"**[API: apply_for_tide_program]** \n\n Unexpected error: {str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        return JSONResponse(
            content={"error": "An unexpected error occurred. Please try again later."},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

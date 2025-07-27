import asyncio


from typing import Optional, List
from datetime import timedelta
from channels.db import database_sync_to_async
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    status,
    Query,
    UploadFile,
    File,
    Form,
    Body,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
import bleach
import os
from user_agents import parse as parse_user_agent
from django.db.models import Q, Prefetch
from django.db import transaction
from django.db import models
from django.utils import timezone
import re
from django.shortcuts import get_object_or_404
from django.utils.timezone import now

from apiManager.utilities.notify_by_bot import notify_by_bot
from apiManager.utilities.device_info import get_device_info
from apiManager.utilities.form_fields import get_form_fields
from authenticationApp.models import CustomUser
from versionManagementApp.models import AppVersion
from versionManagementApp.forms import AppVersionForm
from versionManagementAPI.serializers import VersionCheckResponse

import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/version", response_model=VersionCheckResponse)
async def check_version(request: Request, platform: str):
    version_info = (
        AppVersion.objects.filter(platform=platform).order_by("-updated_at").first()
    )
    if version_info:
        return VersionCheckResponse(
            latest_version=version_info.latest_version,
            minimum_required_version=version_info.minimum_required_version,
            force_update=getattr(version_info, "force_update", False),
        )

    return {
        "latest_version": "1.0.0",
        "minimum_required_version": "1.0.0",
        "force_update": False,
    }


@router.get("/create/form/fields")
async def get_app_version_create_form_fields(
    request: Request,
    platform: Optional[str] = None,
):
    """
    Get form fields for creating a new app version.
    """
    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:
        form = AppVersionForm()
        form_fields = get_form_fields(form)

        result = {
            "success": True,
            "message": "Form fields retrieved successfully",
            "data": {
                "form_fields": form_fields,
                "platform": platform,
            },
        }

        await notify_by_bot(
            f"**[API: get_app_version_create_form_fields]** \n\n Form fields retrieved successfully \n\n Platform: {platform}",
            platform or "Unknown",
            "INFO",
            device_info,
        )

        return JSONResponse(content=result, status_code=200)

    except Exception as e:
        await notify_by_bot(
            f"**[API: get_app_version_create_form_fields]** \n\n Error retrieving form fields: {str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(
            status_code=500, detail=f"Error retrieving form fields: {str(e)}"
        )


@router.post("/create")
async def create_app_version(
    request: Request,
    platform: Optional[str] = None,
):
    """
    Create a new app version.
    """
    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:
        # Parse form data
        form_data = await request.form()

        # Create form instance
        form = AppVersionForm(form_data)

        if form.is_valid():
            # Save the app version
            app_version = form.save()

            result = {
                "success": True,
                "message": "App version created successfully",
                "data": {
                    "version_id": app_version.version_id,
                    "platform": app_version.platform,
                    "latest_version": app_version.latest_version,
                    "minimum_required_version": app_version.minimum_required_version,
                    "updated_at": app_version.updated_at.isoformat(),
                },
            }

            await notify_by_bot(
                f"**[API: create_app_version]** \n\n App version created successfully: {app_version.platform} - {app_version.latest_version} \n\n Platform: {platform}",
                platform or "Unknown",
                "INFO",
                device_info,
            )

            return JSONResponse(content=result, status_code=201)
        else:
            result = {
                "success": False,
                "message": "Form validation failed",
                "errors": form.errors,
            }

            await notify_by_bot(
                f"**[API: create_app_version]** \n\n Form validation failed: {form.errors} \n\n Platform: {platform}",
                platform or "Unknown",
                "WARNING",
                device_info,
            )

            return JSONResponse(content=result, status_code=400)

    except Exception as e:
        await notify_by_bot(
            f"**[API: create_app_version]** \n\n Error creating app version: {str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(
            status_code=500, detail=f"Error creating app version: {str(e)}"
        )


@router.get("/getAll")
async def get_all_app_versions(
    request: Request,
    platform: Optional[str] = None,
):
    """
    Get all app versions for admin portal.
    """
    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:
        # Get all app versions ordered by platform and updated_at
        app_versions = AppVersion.objects.all().order_by("platform", "-updated_at")

        versions_data = []
        for version in app_versions:
            versions_data.append(
                {
                    "version_id": version.version_id,  # type: ignore
                    "platform": version.platform,
                    "latest_version": version.latest_version,
                    "minimum_required_version": version.minimum_required_version,
                    "updated_at": version.updated_at.isoformat(),
                }
            )

        result = {
            "success": True,
            "message": "App versions retrieved successfully",
            "data": {
                "versions": versions_data,
                "total_count": len(versions_data),
            },
        }

        await notify_by_bot(
            f"**[API: get_all_app_versions]** \n\n App versions retrieved successfully: {len(versions_data)} versions \n\n Platform: {platform}",
            platform or "Unknown",
            "INFO",
            device_info,
        )

        return JSONResponse(content=result, status_code=200)

    except Exception as e:
        await notify_by_bot(
            f"**[API: get_all_app_versions]** \n\n Error retrieving app versions: {str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(
            status_code=500, detail=f"Error retrieving app versions: {str(e)}"
        )


@router.delete("/{version_id}/delete")
async def delete_app_version(
    version_id: int,
    request: Request,
    platform: Optional[str] = None,
):
    """
    Delete an app version.
    """
    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:
        # Get the app version
        app_version = AppVersion.objects.get(version_id=version_id)  # type: ignore

        # Store info for logging
        platform_name = app_version.platform
        version_number = app_version.latest_version

        # Delete the app version
        app_version.delete()

        result = {
            "success": True,
            "message": "App version deleted successfully",
            "data": {
                "deleted_version": {
                    "id": version_id,
                    "platform": platform_name,
                    "latest_version": version_number,
                },
            },
        }

        await notify_by_bot(
            f"**[API: delete_app_version]** \n\n App version deleted successfully: {platform_name} - {version_number} \n\n Platform: {platform}",
            platform or "Unknown",
            "INFO",
            device_info,
        )

        return JSONResponse(content=result, status_code=200)

    except AppVersion.DoesNotExist:  # type: ignore
        result = {
            "success": False,
            "message": "App version not found",
            "data": {"version_id": version_id},
        }

        await notify_by_bot(
            f"**[API: delete_app_version]** \n\n App version not found: {version_id} \n\n Platform: {platform}",
            platform or "Unknown",
            "WARNING",
            device_info,
        )

        return JSONResponse(content=result, status_code=404)

    except Exception as e:
        await notify_by_bot(
            f"**[API: delete_app_version]** \n\n Error deleting app version: {str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(
            status_code=500, detail=f"Error deleting app version: {str(e)}"
        )

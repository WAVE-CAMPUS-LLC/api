from typing import Optional
from channels.db import database_sync_to_async
from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
import bleach
import os
from user_agents import parse as parse_user_agent
from django.db.models import Q, Prefetch
from django.db import transaction
from django.utils import timezone
import re
from django.conf import settings
import uuid

from walle import config, suggest_friends_ai, suggest_friends_graph

from authenticationApp.models import CustomUser
from accountManagementApp.models import UserProfile
from socialGraphManagement.recommendations.social.friend import suggest_friends_for_user

from apiManager.utilities.notify_by_bot import notify_by_bot
from apiManager.utilities.device_info import get_device_info
from apiManager.dependencies import get_current_user

config.set_config(
    NEO4J_URI=settings.NEO4J_URI,
    NEO4J_USER=settings.NEO4J_USER,
    NEO4J_PASSWORD=settings.NEO4J_PASSWORD,
    OPENAI_KEY=settings.COLLEGE_OPENAI_API_KEY,
)

router = APIRouter()


@database_sync_to_async
def get_user_profiles_from_ids(user_data_list):
    """
    Fetch user profiles from a list of user data dictionaries.
    Returns a list of user profile dictionaries.
    """
    try:
        # Extract user IDs from the data structure returned by walle
        user_ids = []
        for item in user_data_list:
            if isinstance(item, dict) and "user_id" in item:
                try:
                    # Convert string UUID to UUID object
                    user_uuid = uuid.UUID(item["user_id"])
                    user_ids.append(user_uuid)
                except ValueError as e:
                    print(f"Invalid UUID format: {item['user_id']} - {e}")
                    continue
            elif isinstance(item, str):
                # Handle case where it might be just a string UUID
                try:
                    user_uuid = uuid.UUID(item)
                    user_ids.append(user_uuid)
                except ValueError as e:
                    print(f"Invalid UUID format: {item} - {e}")
                    continue

        print(f"Extracted user IDs: {user_ids}")  # Debug print

        if not user_ids:
            return []

        # Check if any users exist in the database
        users = CustomUser.objects.filter(user_id__in=user_ids).select_related(
            "user_profile"
        )
        print(f"Found users: {[str(u.user_id) for u in users]}")  # Debug print

        # Debug: Check total users in database
        total_users = CustomUser.objects.count()
        print(f"Total users in database: {total_users}")

        # Debug: Check a few sample users
        sample_users = CustomUser.objects.all()
        print(f"Sample user IDs: {[str(u.user_id) for u in sample_users]}")

        # Debug: Check if specific walle user IDs exist
        for walle_user_id in user_ids:
            exists = CustomUser.objects.filter(user_id=walle_user_id).exists()
            print(f"User {walle_user_id} exists in database: {exists}")
            if exists:
                user = CustomUser.objects.get(user_id=walle_user_id)
                print(f"  - Username: {user.username}")
                print(f"  - Name: {user.first_name} {user.last_name}")

        user_profiles = []

        for user in users:
            try:
                user_profile = user.user_profile  # type: ignore[attr-defined]
                user_profiles.append(
                    {
                        "user_id": str(user.user_id),
                        "username": user.username,
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                        "profile_photo": (
                            user_profile.profile_photo.url
                            if user_profile.profile_photo
                            else None
                        ),
                    }
                )
            except AttributeError:
                # Skip users without profiles
                continue

        # If no users found in database, return the original walle data structure
        if not user_profiles and user_data_list:
            print("No matching users found in database, returning original walle data")
            return user_data_list

        return user_profiles
    except Exception as e:
        print(f"Error fetching user profiles: {str(e)}")
        return []


@router.get("/suggest/friends")
async def suggest_friends(
    request: Request,
    user_id: str = Query(..., description="User ID to suggest friends for"),
    limit: int = Query(10, description="Maximum number of suggestions"),
    platform: Optional[str] = None,
):
    """
    Suggest friends for a user using both graph and AI methods.
    Returns user profiles with detailed information.
    """
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:
        # Use walle.suggest.suggest_friends_graph and walle.core.suggest_friends_ai
        graph_suggestions = suggest_friends_graph(user_id, limit)
        ai_suggestions = suggest_friends_ai(user_id)

        # Convert user IDs to user profiles
        graph_user_profiles = await get_user_profiles_from_ids(graph_suggestions)
        ai_user_profiles = await get_user_profiles_from_ids(ai_suggestions)

        return {
            "user_id": user_id,
            "graph_suggestions": graph_user_profiles,
            "ai_suggestions": ai_user_profiles,
            "platform": platform,
        }
    except Exception as e:
        await notify_by_bot(
            f"**[API: suggest_friends]** \n\n Error: {str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(
            status_code=500, detail=f"Error suggesting friends: {str(e)}"
        )


@router.get("/suggest/friends/personalized")
async def suggest_friends_personalized(
    request: Request,
    current_user_id: int = Depends(get_current_user),
    limit: int = Query(5, description="Maximum number of suggestions"),
    platform: Optional[str] = None,
):
    """
    Get personalized friend suggestions with AI-generated messages for the currently logged in user.
    Returns a personalized message suggesting friends for the user.
    """
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:
        # Get user details for personalization
        user = await database_sync_to_async(CustomUser.objects.get)(id=current_user_id)
        user_name = user.username or str(user.user_id)

        # Get friend recommendations with user details
        from socialGraphManagement.recommendations.social.friend import (
            get_friend_recommendations,
        )

        recommendations = get_friend_recommendations(str(user.user_id), limit)

        # Get detailed user profiles for recommendations
        recommended_users = []
        for rec in recommendations:
            try:
                recommended_user = await database_sync_to_async(CustomUser.objects.get)(
                    user_id=rec["user_id"]
                )
                user_profile = await database_sync_to_async(
                    lambda: recommended_user.user_profile
                )()

                recommended_users.append(
                    {
                        "user_id": str(recommended_user.user_id),
                        "username": recommended_user.username,
                        "first_name": recommended_user.first_name,
                        "last_name": recommended_user.last_name,
                        "profile_photo": (
                            user_profile.profile_photo.url
                            if user_profile and user_profile.profile_photo
                            else None
                        ),
                        "score": rec["score"],
                    }
                )
            except CustomUser.DoesNotExist:  # type: ignore[attr-defined]
                continue

        # Generate personalized friend suggestion message
        personalized_message = suggest_friends_for_user(
            str(user.user_id), user_name, limit
        )

        return {
            "user_id": str(user.user_id),
            "user_name": user_name,
            "personalized_message": personalized_message,
            "recommended_users": recommended_users,
            "limit": limit,
            "platform": platform,
        }
    except CustomUser.DoesNotExist:  # type: ignore[attr-defined]
        await notify_by_bot(
            f"**[API: suggest_friends_personalized]** \n\n User not found: {current_user_id} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(
            status_code=404, detail=f"User with ID {current_user_id} not found"
        )
    except Exception as e:
        await notify_by_bot(
            f"**[API: suggest_friends_personalized]** \n\n Error: {str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Error generating personalized friend suggestions: {str(e)}",
        )

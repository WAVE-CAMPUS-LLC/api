import asyncio
import bleach
import os
import re
import uuid

from typing import Optional
from channels.db import database_sync_to_async
from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm

from user_agents import parse as parse_user_agent
from django.db.models import Q, Prefetch
from django.db import transaction
from django.utils import timezone

from django.conf import settings


from walle import config, suggest_friends_ai, suggest_friends_graph

from authenticationApp.models import CustomUser
from accountManagementApp.models import UserProfile
from socialGraphManagement.recommendations.social.friend import (
    suggest_friends_for_user,
    get_paginated_friend_recommendations,
)
from socialGraphManagement.recommendations.event.event import (
    get_event_recommendations_for_user,
    get_users_for_event_recommendation,
    get_similar_events,
    get_event_details_from_ids,
    get_personalized_event_discovery,
    get_college_events,
)
from socialGraphManagement.graph.crew_graph import suggest_crews_for_user
from socialApp.models import Crew, CrewJoinRequest
from django.db import IntegrityError

from apiManager.utilities.notify_by_bot import notify_by_bot
from apiManager.utilities.device_info import get_device_info
from apiManager.dependencies import get_current_user
import random

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
    page: int = Query(1, ge=1, description="Page number (starts from 1)"),
    page_size: int = Query(
        20, ge=1, le=50, description="Number of suggestions per page (max 50)"
    ),
    platform: Optional[str] = None,
):
    """
    Get personalized friend suggestions with pagination.
    Returns friend recommendations with user profiles and pagination metadata.
    """
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:
        # Get user details for personalization
        user = await database_sync_to_async(CustomUser.objects.get)(id=current_user_id)
        user_name = user.username or str(user.user_id)

        # Get paginated friend recommendations
        paginated_data = await database_sync_to_async(
            get_paginated_friend_recommendations
        )(str(user.user_id), page, page_size)

        # Get detailed user profiles for recommendations
        recommended_users = []
        for rec in paginated_data["recommendations"]:
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
            except Exception:
                continue

        # Generate personalized friend suggestion message
        personalized_message = await database_sync_to_async(suggest_friends_for_user)(
            str(user.user_id), user_name, len(paginated_data["recommendations"])
        )

        return {
            "user_id": str(user.user_id),
            "user_name": user_name,
            "personalized_message": personalized_message,
            "recommended_users": recommended_users,
            "pagination": paginated_data["pagination"],
            "platform": platform,
        }
    except Exception as e:
        if "does not exist" in str(e).lower():
            await notify_by_bot(
                f"**[API: suggest_friends_personalized]** \n\n User not found: {current_user_id} \n\n Platform: {platform}",
                platform or "Unknown",
                "ERROR",
                device_info,
            )
            raise HTTPException(
                status_code=404, detail=f"User with ID {current_user_id} not found"
            )
        else:
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


@router.get("/suggest/events")
async def suggest_events(
    request: Request,
    current_user_id: int = Depends(get_current_user),
    college_name: Optional[str] = Query(
        None,
        description="User's college name (optional - will auto-detect from profile)",
    ),
    limit: int = Query(10, description="Maximum number of event suggestions"),
    platform: Optional[str] = None,
):
    """
    Get personalized event recommendations for the currently logged in user.
    Returns events based on user's social network, preferences, and college context.
    Automatically detects college from user profile if not provided.
    """
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:
        # Get user details
        user = await database_sync_to_async(CustomUser.objects.get)(id=current_user_id)

        # Auto-detect college from user profile if not provided
        detected_college_name = college_name
        if not detected_college_name:
            try:
                user_profile = await database_sync_to_async(lambda: user.user_profile)()
                if user_profile and user_profile.college:
                    detected_college_name = user_profile.college.name
                else:
                    # If no college found, use None to indicate no college context
                    detected_college_name = None
            except Exception as e:
                print(f"Error detecting college from profile: {str(e)}")
                detected_college_name = None  # Fallback

        # Get event recommendations from Neo4j
        event_recommendations = get_event_recommendations_for_user(
            str(user.user_id), detected_college_name, limit
        )

        # Fetch detailed event information from database
        detailed_recommendations = await database_sync_to_async(
            get_event_details_from_ids
        )(event_recommendations)

        return {
            "user_id": str(user.user_id),
            "user_name": user.username or str(user.user_id),
            "college_name": detected_college_name,
            "college_auto_detected": college_name is None,
            "has_college_context": detected_college_name is not None,
            "event_recommendations": detailed_recommendations,
            "limit": limit,
            "platform": platform,
        }
    except Exception as e:
        if "does not exist" in str(e).lower():
            await notify_by_bot(
                f"**[API: suggest_events]** \n\n User not found: {current_user_id} \n\n Platform: {platform}",
                platform or "Unknown",
                "ERROR",
                device_info,
            )
            raise HTTPException(
                status_code=404, detail=f"User with ID {current_user_id} not found"
            )
        else:
            await notify_by_bot(
                f"**[API: suggest_events]** \n\n Error: {str(e)} \n\n Platform: {platform}",
                platform or "Unknown",
                "ERROR",
                device_info,
            )
            raise HTTPException(
                status_code=500, detail=f"Error generating event suggestions: {str(e)}"
            )


@router.get("/suggest/events/{event_id}/users")
async def suggest_users_for_event(
    request: Request,
    event_id: str,
    limit: int = Query(20, description="Maximum number of user suggestions"),
    platform: Optional[str] = None,
):
    """
    Get user recommendations for a specific event.
    Returns users who might be interested in attending the event.
    """
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:
        # Get user recommendations for the event
        user_recommendations = get_users_for_event_recommendation(event_id, limit)

        return {
            "event_id": event_id,
            "user_recommendations": user_recommendations,
            "limit": limit,
            "platform": platform,
        }
    except Exception as e:
        await notify_by_bot(
            f"**[API: suggest_users_for_event]** \n\n Error: {str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Error generating user suggestions for event: {str(e)}",
        )


@router.get("/suggest/events/{event_id}/similar")
async def suggest_similar_events(
    request: Request,
    event_id: str,
    limit: int = Query(5, description="Maximum number of similar event suggestions"),
    platform: Optional[str] = None,
):
    """
    Get similar event recommendations for a specific event.
    Returns events that are similar based on category, host, interests, etc.
    """
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:
        # Get similar events from Neo4j
        similar_events = get_similar_events(event_id, limit)

        # Fetch detailed event information from database
        detailed_similar_events = await database_sync_to_async(
            get_event_details_from_ids
        )(similar_events)

        return {
            "event_id": event_id,
            "similar_events": detailed_similar_events,
            "limit": limit,
            "platform": platform,
        }
    except Exception as e:
        await notify_by_bot(
            f"**[API: suggest_similar_events]** \n\n Error: {str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Error generating similar event suggestions: {str(e)}",
        )


@router.get("/discover/events")
async def discover_events(
    request: Request,
    current_user_id: int = Depends(get_current_user),
    page: int = Query(1, ge=1, description="Page number (starts from 1)"),
    page_size: int = Query(
        15, ge=5, le=50, description="Number of events per page (min 5, max 50)"
    ),
    platform: Optional[str] = None,
):
    """
    Get personalized event discovery with pagination optimized for React Native.
    Returns events prioritized by user preferences and social connections.
    Supports infinite scrolling with larger page sizes for better UX.
    """
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:
        # Get user details
        user = await database_sync_to_async(CustomUser.objects.get)(id=current_user_id)

        # Calculate offset for pagination
        offset = (page - 1) * page_size

        # Get personalized event discovery from Neo4j (fetch more to allow for pagination)
        total_limit = (
            page_size * 15
        )  # Fetch more events to ensure we have enough for pagination
        event_discovery = get_personalized_event_discovery(
            str(user.user_id), total_limit
        )

        # Apply pagination to the results
        paginated_events = event_discovery[offset : offset + page_size]

        # Fetch detailed event information from database
        detailed_events = await database_sync_to_async(get_event_details_from_ids)(
            paginated_events
        )

        # Calculate pagination metadata
        total_events = len(event_discovery)
        total_pages = (total_events + page_size - 1) // page_size
        has_next = page < total_pages
        has_previous = page > 1

        return {
            "user_id": str(user.user_id),
            "user_name": user.username or str(user.user_id),
            "events": detailed_events,
            "pagination": {
                "current_page": page,
                "page_size": page_size,
                "total_events": total_events,
                "total_pages": total_pages,
                "has_next": has_next,
                "has_previous": has_previous,
                "next_page": page + 1 if has_next else None,
                "previous_page": page - 1 if has_previous else None,
                "remaining_events": total_events - (page * page_size),
            },
            "platform": platform,
        }
    except Exception as e:
        if "does not exist" in str(e).lower():
            await notify_by_bot(
                f"**[API: discover_events]** \n\n User not found: {current_user_id} \n\n Platform: {platform}",
                platform or "Unknown",
                "ERROR",
                device_info,
            )
            raise HTTPException(
                status_code=404, detail=f"User with ID {current_user_id} not found"
            )
        else:
            await notify_by_bot(
                f"**[API: discover_events]** \n\n Error: {str(e)} \n\n Platform: {platform}",
                platform or "Unknown",
                "ERROR",
                device_info,
            )
            raise HTTPException(
                status_code=500, detail=f"Error generating event discovery: {str(e)}"
            )


@router.get("/discover/events/college")
async def discover_college_events(
    request: Request,
    current_user_id: int = Depends(get_current_user),
    page: int = Query(1, ge=1, description="Page number (starts from 1)"),
    page_size: int = Query(
        15, ge=5, le=50, description="Number of events per page (min 5, max 50)"
    ),
    platform: Optional[str] = None,
):
    """
    Get college-specific event discovery with pagination optimized for React Native.
    Returns events only from the user's college, prioritized by preferences.
    Supports infinite scrolling with larger page sizes for better UX.
    """
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:
        # Get user details
        user = await database_sync_to_async(CustomUser.objects.get)(id=current_user_id)
        user_profile = await database_sync_to_async(lambda: user.user_profile)()
        if (
            not user_profile
            or not user_profile.college
            or not user_profile.college.name
        ):
            raise HTTPException(
                status_code=400,
                detail="User does not have a college set in their profile.",
            )
        college_name = user_profile.college.name

        # Calculate offset for pagination
        offset = (page - 1) * page_size

        # Get college events from Neo4j (fetch more to allow for pagination)
        total_limit = page_size * 15
        event_discovery = get_college_events(
            str(user.user_id), college_name, total_limit
        )

        # Apply pagination to the results
        paginated_events = event_discovery[offset : offset + page_size]

        # Fetch detailed event information from database
        detailed_events = await database_sync_to_async(get_event_details_from_ids)(
            paginated_events
        )

        # Calculate pagination metadata
        total_events = len(event_discovery)
        total_pages = (total_events + page_size - 1) // page_size
        has_next = page < total_pages
        has_previous = page > 1

        return {
            "user_id": str(user.user_id),
            "user_name": user.username or str(user.user_id),
            "college_name": college_name,
            "events": detailed_events,
            "pagination": {
                "current_page": page,
                "page_size": page_size,
                "total_events": total_events,
                "total_pages": total_pages,
                "has_next": has_next,
                "has_previous": has_previous,
                "next_page": page + 1 if has_next else None,
                "previous_page": page - 1 if has_previous else None,
                "remaining_events": total_events - (page * page_size),
            },
            "platform": platform,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error discovering college events: {str(e)}"
        )


@router.get("/suggest/crews")
async def suggest_crews(
    request: Request,
    current_user_id: int = Depends(get_current_user),
    limit: int = Query(10, description="Maximum number of crew suggestions"),
    platform: Optional[str] = None,
):
    """
    Suggest relevant crews for a user to join, using the graph system. If the user is not in any crew, suggest up to 10 random crews.
    """
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]
    try:
        user = await database_sync_to_async(CustomUser.objects.get)(id=current_user_id)
        # Check if user is in any crew
        from socialApp.models import CrewMember

        user_crews_count = await database_sync_to_async(
            lambda: CrewMember.objects.filter(user=user).count()
        )()
        if user_crews_count == 0:
            # Suggest up to 10 random crews
            random_crews = await database_sync_to_async(
                lambda: list(Crew.objects.order_by("?")[:limit])
            )()
            # Serialize minimal info for random crews
            random_crews_data = []
            for crew in random_crews:
                # Fix closure capture issue by creating a proper function
                async def get_member_count(crew_instance):
                    return await database_sync_to_async(
                        lambda: CrewMember.objects.filter(crew=crew_instance).count()
                    )()

                try:
                    num_members = await get_member_count(crew)
                except:
                    num_members = 0  # Fallback if relationship doesn't exist

                random_crews_data.append(
                    {
                        "crewId": str(crew.crewId),
                        "name": crew.name or "",
                        "bio": crew.bio or "",
                        "crew_image": crew.crew_image.url if crew.crew_image else None,
                        "created_by": (
                            crew.created_by.username if crew.created_by else None
                        ),
                        "num_members": num_members,
                    }
                )
            return {
                "user_id": str(user.user_id),
                "random_crews": random_crews_data,
                "platform": platform,
                "message": "User is not in any crew. Showing random crews.",
            }
        # Otherwise, use the graph suggestion system
        suggestions = await database_sync_to_async(suggest_crews_for_user)(
            str(user.user_id), limit
        )

        # If no suggestions from graph system (no connections through friends/interests),
        # suggest random crews instead
        if not suggestions or len(suggestions) == 0:
            print(
                f"No graph-based suggestions found for user {user.user_id}, suggesting random crews"
            )

            # Get user's current crews to exclude them
            user_crew_ids = await database_sync_to_async(
                lambda: list(
                    CrewMember.objects.filter(user=user).values_list(
                        "crew_id", flat=True
                    )
                )
            )()

            # Get random crews excluding ones user is already in
            random_crews = await database_sync_to_async(
                lambda: list(
                    Crew.objects.exclude(crewId__in=user_crew_ids).order_by("?")[:limit]
                )
            )()

            random_crews_data = []
            for crew in random_crews:
                # Fix closure capture issue by creating a proper function
                async def get_member_count(crew_instance):
                    return await database_sync_to_async(
                        lambda: CrewMember.objects.filter(crew=crew_instance).count()
                    )()

                try:
                    num_members = await get_member_count(crew)
                except:
                    num_members = 0  # Fallback if relationship doesn't exist

                random_crews_data.append(
                    {
                        "crewId": str(crew.crewId),
                        "name": crew.name or "",
                        "bio": crew.bio or "",
                        "crew_image": crew.crew_image.url if crew.crew_image else None,
                        "created_by": (
                            crew.created_by.username if crew.created_by else None
                        ),
                        "num_members": num_members,
                    }
                )

            return {
                "user_id": str(user.user_id),
                "suggested_crews": random_crews_data,
                "platform": platform,
                "suggestion_type": "random",
                "message": "No recommendations through friends or interests. Showing random crews.",
            }

        # If suggestions are a list of dicts with crewId, enrich with image and num_members
        enriched_suggestions = []
        for suggestion in suggestions:
            crew_id = (
                suggestion.get("crewId")
                or suggestion.get("crew_id")
                or suggestion.get("id")
            )

            # Fix closure capture issue by creating a proper function
            async def get_crew_and_count(crew_uuid):
                crew = await database_sync_to_async(
                    lambda: Crew.objects.filter(crewId=crew_uuid).first()
                )()
                if crew:
                    try:
                        num_members = await database_sync_to_async(
                            lambda: CrewMember.objects.filter(crew=crew).count()
                        )()
                    except:
                        num_members = 0
                    return crew, num_members
                return None, 0

            crew, num_members = await get_crew_and_count(crew_id)

            suggestion["crew_image"] = (
                crew.crew_image.url if crew and crew.crew_image else None
            )
            suggestion["num_members"] = num_members
            enriched_suggestions.append(suggestion)

        return {
            "user_id": str(user.user_id),
            "suggested_crews": enriched_suggestions,
            "platform": platform,
            "suggestion_type": "graph_based",
            "message": "Recommendations based on your friends and interests.",
        }
    except Exception as e:
        await notify_by_bot(
            f"**[API: suggest_crews]** \n\n Error: {str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(status_code=500, detail=f"Error suggesting crews: {str(e)}")

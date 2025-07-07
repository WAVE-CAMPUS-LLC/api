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

from walle import config, suggest


from apiManager.utilities.notify_by_bot import notify_by_bot
from apiManager.utilities.device_info import get_device_info

config.set_config(
    NEO4J_URI=settings.NEO4J_URI,
    NEO4J_USER=settings.NEO4J_USER,
    NEO4J_PASSWORD=settings.NEO4J_PASSWORD,
    OPENAI_KEY=settings.COLLEGE_OPENAI_API_KEY,
)

router = APIRouter()


@router.get("/suggest/friends")
async def suggest_friends(
    request: Request,
    user_id: str = Query(..., description="User ID to suggest friends for"),
    limit: int = Query(10, description="Maximum number of suggestions"),
    platform: Optional[str] = None,
):
    """
    Suggest friends for a user using both graph and AI methods.
    """
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:
        # Use walle.suggest.suggest_friends_graph and walle.core.suggest_friends_ai
        from walle.core import suggest_friends_ai, suggest_friends_graph

        graph_suggestions = suggest_friends_graph(user_id, limit)
        ai_suggestions = suggest_friends_ai(user_id)

        return {
            "user_id": user_id,
            "graph_suggestions": graph_suggestions,
            "ai_suggestions": ai_suggestions,
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

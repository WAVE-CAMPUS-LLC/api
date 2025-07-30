import httpx
import os
import time
from typing import Optional


api_url = "https://walle-6okl.onrender.com/api"
DISCORD_BOT_API_KEY = os.getenv("BOT_API_KEY")

# Simple rate limiting - max 1 notification per 2 seconds
_last_notification_time = 0
_min_notification_interval = 2.0  # seconds


async def notify_by_bot(
    message: str, platform: str, level: str = "ERROR", device_info: str = None
) -> Optional[bool]:
    """
    Send a notification to the Discord bot with rate limiting.

    Args:
        message (str): The message to send
        level (str): The log level (default: "ERROR")

    Returns:
        Optional[bool]: True if successful, False if failed, None if API key is missing
    """
    global _last_notification_time
    
    if not DISCORD_BOT_API_KEY:
        print("[notify_by_bot] Error: BOT_API_KEY environment variable is not set")
        return None

    if not message:
        print("[notify_by_bot] Error: Message cannot be empty")
        return False

    if not platform:
        print("[notify_by_bot] Error: Platform cannot be empty")
        return False

    # Rate limiting check
    current_time = time.time()
    time_since_last = current_time - _last_notification_time
    
    if time_since_last < _min_notification_interval:
        print(f"[notify_by_bot] Rate limited: skipping notification (last sent {time_since_last:.1f}s ago)")
        return False
    
    _last_notification_time = current_time

    try:
        # Use shorter timeout and better connection settings for reliability
        timeout_config = httpx.Timeout(
            connect=2.0,  # Connection timeout
            read=3.0,     # Read timeout
            write=2.0,    # Write timeout
            pool=5.0      # Pool timeout
        )
        
        async with httpx.AsyncClient(timeout=timeout_config) as client:
            response = await client.post(
                f"{api_url}/log/error",
                json={
                    "message": message,
                    "level": level,
                    "platform": platform,
                    "device_info": device_info,
                },
                headers={"X-API-Key": DISCORD_BOT_API_KEY},
            )
            response.raise_for_status()
            print(f"[notify_by_bot] Successfully sent notification: {level}")
            return True
    except httpx.TimeoutException:
        print(f"[notify_by_bot] Error: Request timed out after 3 seconds")
        return False
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            print(f"[notify_by_bot] Warning: Rate limited (429) - notification service is busy")
            return False
        else:
            print(f"[notify_by_bot] Error: HTTP {e.response.status_code} error occurred: {str(e)}")
            return False
    except httpx.HTTPError as e:
        print(f"[notify_by_bot] Error: HTTP error occurred: {str(e)}")
        return False
    except httpx.ConnectError as e:
        print(f"[notify_by_bot] Error: Could not connect to notification service: {str(e)}")
        return False
    except Exception as e:
        print(f"[notify_by_bot] Error sending message: {str(e)}")
        return False

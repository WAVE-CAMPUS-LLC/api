import httpx
import os
from typing import Optional


api_url = "https://walle-6okl.onrender.com/api"
DISCORD_BOT_API_KEY = os.getenv("BOT_API_KEY")


async def notify_by_bot(
    message: str, platform: str, level: str = "ERROR", device_info: str = None
) -> Optional[bool]:
    """
    Send a notification to the Discord bot.

    Args:
        message (str): The message to send
        level (str): The log level (default: "ERROR")

    Returns:
        Optional[bool]: True if successful, False if failed, None if API key is missing
    """
    if not DISCORD_BOT_API_KEY:
        print("[notify_by_bot] Error: BOT_API_KEY environment variable is not set")
        return None

    if not message:
        print("[notify_by_bot] Error: Message cannot be empty")
        return False

    if not platform:
        print("[notify_by_bot] Error: Platform cannot be empty")
        return False

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
    except httpx.HTTPError as e:
        print(f"[notify_by_bot] Error: HTTP error occurred: {str(e)}")
        return False
    except httpx.ConnectError as e:
        print(f"[notify_by_bot] Error: Could not connect to notification service: {str(e)}")
        return False
    except Exception as e:
        print(f"[notify_by_bot] Error sending message: {str(e)}")
        return False

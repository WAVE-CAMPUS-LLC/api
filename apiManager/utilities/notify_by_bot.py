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
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{api_url}/log/error",
                json={
                    "message": message,
                    "level": level,
                    "platform": platform,
                    "device_info": device_info,
                },
                headers={"X-API-Key": DISCORD_BOT_API_KEY},
                timeout=5,  # Increased timeout for better reliability
            )
            response.raise_for_status()
            return True
    except httpx.TimeoutException:
        print("[notify_by_bot] Error: Request timed out")
        return False
    except httpx.HTTPError as e:
        print(f"[notify_by_bot] Error: HTTP error occurred: {str(e)}")
        return False
    except Exception as e:
        print(f"[notify_by_bot] Error sending message: {str(e)}")
        return False

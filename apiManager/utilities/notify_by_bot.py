import httpx
import os


api_url = "https://walle-6okl.onrender.com/api"
DISCORD_BOT_API_KEY = os.getenv("BOT_API_KEY")


async def notify_by_bot(message: str, level: str = "ERROR"):
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{api_url}/log/error",
                json={"message": message, "level": level},
                headers={"X-API-Key": DISCORD_BOT_API_KEY},
                timeout=1,
            )
    except Exception as e:
        print(f"[notify_by_bot] Error sending message: {str(e)}")

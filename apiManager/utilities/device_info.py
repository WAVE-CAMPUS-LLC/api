from user_agents import parse as parse_user_agent
from typing import Dict


def get_device_info(user_agent_str: str) -> Dict[str, str]:
    """
    Extract device information from user agent string.

    Args:
        user_agent_str (str): The user agent string from request headers

    Returns:
        Dict[str, str]: Dictionary containing device type and detailed device info
    """
    user_agent = parse_user_agent(user_agent_str)

    # Determine device type
    device_type = (
        "iOS"
        if user_agent.is_mobile and user_agent.os.family == "iOS"
        else (
            "Android"
            if user_agent.is_mobile and user_agent.os.family == "Android"
            else "Web" if user_agent.is_pc else "Unknown"
        )
    )

    # Get detailed device information
    browser = f"{user_agent.browser.family} {user_agent.browser.version_string}"
    ops = f"{user_agent.os.family} {user_agent.os.version_string}"
    device_family = user_agent.device.family or "Unknown Device"
    device_brand = user_agent.device.brand or "Generic"
    device_model = user_agent.device.model or "Generic Model"

    device = f"{device_family} {device_brand} {device_model}"

    # Combine all device info
    device_info = f"{device_type} - {browser} - {ops} - {device}"

    return {"device_type": device_type, "device_info": device_info}

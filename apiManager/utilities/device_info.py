from user_agents import parse as parse_user_agent
from typing import Dict, Optional
import requests
import os
import logging
from django.conf import settings
from django.core.cache import cache
import hashlib

# Configure logging for this module
logger = logging.getLogger(__name__)

# Cache timeout for geolocation data (24 hours)
GEOLOCATION_CACHE_TIMEOUT = 24 * 60 * 60


def get_client_ip(request) -> str:
    """
    Extract the client's IP address from the request.
    
    Args:
        request: The Django/FastAPI request object
        
    Returns:
        str: The client's IP address
    """
    try:
        # Check for forwarded IP first (common in production with load balancers)
        x_forwarded_for = None
        
        # Handle both Django and FastAPI request objects
        if hasattr(request, 'META'):
            # Django request
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if not x_forwarded_for:
                x_forwarded_for = request.META.get('HTTP_X_REAL_IP')
            if not x_forwarded_for:
                return request.META.get('REMOTE_ADDR', 'Unknown')
        elif hasattr(request, 'headers'):
            # FastAPI request
            x_forwarded_for = request.headers.get('x-forwarded-for')
            if not x_forwarded_for:
                x_forwarded_for = request.headers.get('x-real-ip')
            if not x_forwarded_for and hasattr(request, 'client'):
                return request.client.host if request.client else 'Unknown'
        
        if x_forwarded_for:
            # Take the first IP if multiple are present
            ip = x_forwarded_for.split(',')[0].strip()
            return ip
            
        return 'Unknown'
    except Exception as e:
        logger.error(f"Error extracting client IP: {e}")
        return 'Unknown'


def get_geolocation(ip_address: str) -> Dict[str, str]:
    """
    Get geographic location information for an IP address with caching.
    
    Args:
        ip_address (str): The IP address to look up
        
    Returns:
        Dict[str, str]: Dictionary containing location information
    """
    try:
        # Skip geolocation for local/private IPs
        if (ip_address in ['Unknown', 'localhost', '127.0.0.1'] or 
            ip_address.startswith('192.168.') or 
            ip_address.startswith('10.') or
            ip_address.startswith('172.')):
            return {
                "country": "Local/Private",
                "region": "Local/Private", 
                "city": "Local/Private",
                "timezone": "Unknown",
                "isp": "Local/Private"
            }
        
        # Create cache key for this IP
        cache_key = f"geolocation_{hashlib.md5(ip_address.encode()).hexdigest()}"
        
        # Check cache first
        try:
            cached_data = cache.get(cache_key)
            if cached_data:
                logger.debug(f"Using cached geolocation data for IP {ip_address}")
                return cached_data
        except Exception as e:
            logger.warning(f"Cache lookup failed for IP {ip_address}: {e}")
        
        # Use ip-api.com (free tier: 1000 requests/month, no API key required)
        # For production, consider upgrading to a paid service like IPinfo, MaxMind, or ipgeolocation.io
        url = f"http://ip-api.com/json/{ip_address}"
        
        # Set a short timeout to avoid slowing down requests
        response = requests.get(url, timeout=2)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('status') == 'success':
                location_data = {
                    "country": data.get('country', 'Unknown'),
                    "region": data.get('regionName', 'Unknown'),
                    "city": data.get('city', 'Unknown'), 
                    "timezone": data.get('timezone', 'Unknown'),
                    "isp": data.get('isp', 'Unknown')
                }
                
                # Cache the result
                try:
                    cache.set(cache_key, location_data, GEOLOCATION_CACHE_TIMEOUT)
                    logger.debug(f"Cached geolocation data for IP {ip_address}")
                except Exception as e:
                    logger.warning(f"Failed to cache geolocation data for IP {ip_address}: {e}")
                
                return location_data
        
        # Fallback if API fails
        fallback_data = {
            "country": "Unknown",
            "region": "Unknown",
            "city": "Unknown", 
            "timezone": "Unknown",
            "isp": "Unknown"
        }
        
        # Cache the fallback data for a shorter time (1 hour) to retry sooner
        try:
            cache.set(cache_key, fallback_data, 60 * 60)
        except Exception:
            pass
        
        return fallback_data
        
    except requests.RequestException as e:
        logger.warning(f"Geolocation API request failed for IP {ip_address}: {e}")
        return {
            "country": "API Error",
            "region": "API Error",
            "city": "API Error",
            "timezone": "Unknown", 
            "isp": "Unknown"
        }
    except Exception as e:
        logger.error(f"Unexpected error in geolocation lookup for IP {ip_address}: {e}")
        return {
            "country": "Error",
            "region": "Error", 
            "city": "Error",
            "timezone": "Unknown",
            "isp": "Unknown"
        }


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


def get_comprehensive_request_info(request, user_agent_str: Optional[str] = None) -> Dict[str, str]:
    """
    Get comprehensive request information including device info, IP address, and geographic location.
    
    Args:
        request: The Django/FastAPI request object
        user_agent_str (Optional[str]): User agent string (will be extracted from request if not provided)
        
    Returns:
        Dict[str, str]: Comprehensive request information for logging
    """
    try:
        # Extract user agent if not provided
        if not user_agent_str:
            if hasattr(request, 'META'):
                # Django request
                user_agent_str = request.META.get('HTTP_USER_AGENT', '')
            elif hasattr(request, 'headers'):
                # FastAPI request  
                user_agent_str = request.headers.get('user-agent', '')
            else:
                user_agent_str = ''
        
        # Get device information
        device_data = get_device_info(user_agent_str)
        
        # Get client IP address
        client_ip = get_client_ip(request)
        
        # Get geographic location (with caching for performance)
        location_data = get_geolocation(client_ip)
        
        # Combine all information
        comprehensive_info = {
            "device_type": device_data["device_type"],
            "device_info": device_data["device_info"],
            "client_ip": client_ip,
            "country": location_data["country"],
            "region": location_data["region"], 
            "city": location_data["city"],
            "timezone": location_data["timezone"],
            "isp": location_data["isp"],
            "location_string": f"{location_data['city']}, {location_data['region']}, {location_data['country']}",
            "log_prefix": f"[{client_ip}|{location_data['city']}, {location_data['country']}|{device_data['device_type']}]"
        }
        
        return comprehensive_info
        
    except Exception as e:
        logger.error(f"Error getting comprehensive request info: {e}")
        return {
            "device_type": "Unknown",
            "device_info": "Error extracting device info",
            "client_ip": "Unknown",
            "country": "Unknown",
            "region": "Unknown",
            "city": "Unknown", 
            "timezone": "Unknown",
            "isp": "Unknown",
            "location_string": "Unknown Location",
            "log_prefix": "[Unknown|Unknown|Unknown]"
        }


def create_enhanced_log_message(function_name: str, message: str, request_info: Dict[str, str]) -> str:
    """
    Create an enhanced log message with location and device information.
    
    Args:
        function_name (str): Name of the function/API endpoint
        message (str): The log message
        request_info (Dict[str, str]): Request information from get_comprehensive_request_info
        
    Returns:
        str: Enhanced log message with location and device info
    """
    return f"{request_info['log_prefix']} [{function_name}] {message}"

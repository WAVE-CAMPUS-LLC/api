import requests
from datetime import datetime
import pytz
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def get_server_location():
    """Get the server's location based on IP address using ipinfo.io"""
    try:
        response = requests.get('https://ipinfo.io/json', timeout=5)
        if response.status_code == 200:
            data = response.json()
            return {
                'city': data.get('city', 'Unknown'),
                'region': data.get('region', 'Unknown'),
                'country': data.get('country', 'US'),
                'timezone': data.get('timezone', settings.TIME_ZONE)
            }
    except Exception as e:
        logger.error(f"Error determining server location: {e}")
    
    # Default to the settings.TIME_ZONE if we can't get location info
    return {
        'city': 'Unknown',
        'region': 'Unknown',
        'country': 'US',
        'timezone': settings.TIME_ZONE
    }

def get_current_timezone():
    """Get the current timezone for the server location"""
    location = get_server_location()
    return location['timezone']

def get_localized_datetime(dt=None):
    """
    Convert a datetime to the server's local timezone.
    If dt is None, returns the current datetime in the server's timezone.
    """
    if dt is None:
        dt = datetime.now(pytz.UTC)
    elif dt.tzinfo is None:
        dt = pytz.UTC.localize(dt)
    
    server_tz = pytz.timezone(get_current_timezone())
    return dt.astimezone(server_tz)

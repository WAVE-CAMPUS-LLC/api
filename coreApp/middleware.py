import requests
import pytz
from django.utils import timezone
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class TimezoneMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        self.set_timezone()
        response = self.get_response(request)
        return response

    def set_timezone(self):
        try:
            response = requests.get('https://ipinfo.io/json', timeout=5)
            if response.status_code == 200:
                data = response.json()
                timezone_name = data.get('timezone', settings.TIME_ZONE)
                timezone.activate(pytz.timezone(timezone_name))
            else:
                timezone.deactivate()
        except Exception as e:
            logger.error(f"Error determining server location: {e}")
            timezone.deactivate()

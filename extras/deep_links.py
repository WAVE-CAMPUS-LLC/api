"""
Utility for handling Universal Links between iOS app and web app.
This module helps manage app-to-web and web-to-app redirections.
"""

import logging
import os
from django.http import HttpResponse, HttpResponseRedirect
from django.conf import settings
from django.urls import reverse

logger = logging.getLogger(__name__)

def handle_event_link(request, eventId):
    """
    Handle deep linking for events - redirects to either the app or web based on user agent/device.
    
    Args:
        request: The HTTP request
        eventId: The ID of the event to be viewed
    
    Returns:
        HttpResponseRedirect to appropriate destination
    """
    user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
    
    # Check if the request is from iOS and potentially has the app installed
    is_ios = 'iphone' in user_agent or 'ipad' in user_agent or 'ipod' in user_agent
    
    # App scheme URL - this will open the app if installed
    app_url = f"waveapp://event/{eventId}"
    
    # Web fallback URL (using the correct URL structure for our site)
    web_url = request.build_absolute_uri(reverse('core:eventDetails', kwargs={'eventId': eventId}))
    
    # For iOS devices, we use a special HTML that attempts to open the app first
    if is_ios:
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Opening Event in Wave App</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <meta http-equiv="refresh" content="2;url={web_url}">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; text-align: center; padding-top: 50px; }}
                .loader {{ border: 5px solid #f3f3f3; border-top: 5px solid #008d95; border-radius: 50%; width: 50px; height: 50px; animation: spin 1s linear infinite; margin: 20px auto; }}
                @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
            </style>
        </head>
        <body>
            <h2>Opening Event in Wave App...</h2>
            <div class="loader"></div>
            <p>If the app doesn't open automatically, <a href="{web_url}">click here</a> to view in browser.</p>
            <script>
                window.onload = function() {{
                    // Try to open the app
                    window.location.href = "{app_url}";
                    
                    // If still here after delay, redirect to web version (fallback happens via meta refresh)
                }}
            </script>
        </body>
        </html>
        """
        return HttpResponse(html)
    
    # For all other devices, redirect to web URL
    return HttpResponseRedirect(web_url)

def serve_apple_app_site_association(request):
    """
    Serve the apple-app-site-association file with proper content type.
    This is important as Apple requires this file to be served with 
    the 'application/json' content type.
    """
    # Use request parameter to log information if needed
    logger.info(f"Apple app site association requested from: {request.META.get('REMOTE_ADDR')}")
    
    # Use absolute path to ensure file is found regardless of current working directory
    file_path = os.path.join(settings.BASE_DIR, 'apple-app-site-association.json')
    
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    return HttpResponse(content, content_type='application/json')
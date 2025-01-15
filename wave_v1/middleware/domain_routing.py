from django.shortcuts import redirect
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin
from django.utils import timezone
from django.http import HttpResponseForbidden, JsonResponse
import logging

logger = logging.getLogger(__name__)

class DomainRoutingMiddleware:
    """
    Middleware to route requests based on the domain and handle API access.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host().lower()
        path = request.path.lower()
        
        # Log request details for debugging
        logger.debug(f"Request Host: {host}")
        logger.debug(f"Request Path: {path}")

        # Set API flag based on domain
        if "wavecampus.net" in host:
            request.is_api = True
            # Only allow API requests to the .net domain
            if not path.startswith('/nativetsureactapi/'):
                logger.warning(f"Blocked non-API request to API domain: {path}")
                return JsonResponse({
                    "error": "Access denied",
                    "message": "This domain is for API access only",
                    "path": path,
                    "host": host
                }, status=403)
        else:
            request.is_api = False
            # Block API requests from non-API domain
            if path.startswith('/nativetsureactapi/'):
                logger.warning(f"Blocked API request from non-API domain: {host}")
                return JsonResponse({
                    "error": "Access denied",
                    "message": "API access is only allowed through wavecampus.net",
                    "path": path,
                    "host": host
                }, status=403)

        response = self.get_response(request)
        
        # Add CORS headers for API requests
        if request.is_api:
            response["Access-Control-Allow-Origin"] = "*"
            response["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
            response["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        """
        Additional processing before the view is called
        """
        return None

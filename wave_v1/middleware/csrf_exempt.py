from django.conf import settings
from django.middleware.csrf import CsrfViewMiddleware

class CustomCsrfMiddleware(CsrfViewMiddleware):
    """
    Custom CSRF middleware that exempts specified paths from CSRF protection.
    Useful for mobile API endpoints that don't use Django's CSRF protection.
    """
    def process_view(self, request, callback, callback_args, callback_kwargs):
        # Check if the request path starts with any of the exempt paths
        exempt_paths = getattr(settings, 'CSRF_EXEMPT_PATHS', [])
        for path in exempt_paths:
            if request.path.startswith(path):
                return None  # Skip CSRF validation for this request
        
        # For all other paths, use the default CSRF validation
        return super().process_view(request, callback, callback_args, callback_kwargs) 
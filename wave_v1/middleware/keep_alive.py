from django.utils.deprecation import MiddlewareMixin


class KeepAliveMiddleware:
    """
    Middleware to add necessary response headers for keeping connections alive
    and handling CORS (Cross-Origin Resource Sharing).
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Add CORS and connection keep-alive headers
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response["Connection"] = "keep-alive"
        response["Keep-Alive"] = "timeout=5, max=100"
        
        return response

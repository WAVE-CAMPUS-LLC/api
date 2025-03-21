from django.utils.deprecation import MiddlewareMixin


class KeepAliveMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response["Connection"] = "keep-alive"
        response["Keep-Alive"] = "timeout=5, max=100"
        return response

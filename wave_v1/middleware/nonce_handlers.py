import random
import string
from django.utils.deprecation import MiddlewareMixin

class NonceMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        # Generate a random nonce string for each request
        nonce = ''.join(random.choices(string.ascii_letters + string.digits, k=16))

        # Add nonce to response header for CSP
        response['Content-Security-Policy'] = f"script-src 'self' 'nonce-{nonce}'"

        # Add nonce to the context so it can be used in templates
        response.context_data = {'nonce': nonce}
        
        return response

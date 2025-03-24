from functools import wraps
from rest_framework.response import Response
from .apiUtils import get_form_fields

def include_form_fields(form_class):
    """
    Decorator that adds form field information to API response
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(*args, **kwargs):
            response = view_func(*args, **kwargs)
            
            # Only modify Response objects
            if isinstance(response, Response):
                # Get the form fields
                fields_info = get_form_fields(form_class)
                
                # If response.data is not a dict, wrap it
                if not isinstance(response.data, dict):
                    response.data = {'data': response.data}
                
                # Add form fields to response
                response.data['form_fields'] = fields_info
                
            return response
        return wrapped_view
    return decorator
from .location_utils import get_server_location, get_localized_datetime

def location_info(request):
    """
    Add server location information to the context.
    Makes the following variables available in templates:
    - server_location: dict with location details
    - current_local_time: datetime object in server's timezone
    """
    return {
        'server_location': get_server_location(),
        'current_local_time': get_localized_datetime()
    }

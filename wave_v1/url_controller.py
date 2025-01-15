from django.conf import settings
from django.urls import include, path, re_path
from django.http import HttpResponseBadRequest

# Define functions to check if it's an API or site request
def is_api_request(host):
    return 'wavecampus.net' in host

def is_site_request(host):
    return 'waveoncampus.com' in host

# Dynamic URL routing function
def dynamic_urlpatterns(request):
    host = request.get_host()

    if is_api_request(host):
        # Load API URLs
        from wave_v1 import urlsapi as api_urls
        return api_urls.urlpatterns
    elif is_site_request(host):
        # Load public website URLs
        from wave_v1 import urls as site_urls
        return site_urls.urlpatterns
    else:
        return [path('', lambda request: HttpResponseBadRequest("Invalid host"))]

# Root urlpatterns
urlpatterns = [
    # Route dynamically based on host
    re_path(r'^', lambda request: include(dynamic_urlpatterns(request))),
]

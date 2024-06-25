from django_hosts import patterns, host
from django.conf import settings


host_patterns = patterns(
    "",
    host(r"www", settings.ROOT_URLCONF, name="www"),
    host(r"controlling", "adminDashboardApp.urls", name="adminPortal"),
    host(r"host", "eventManagementApp.urls", name="hosting"),
    host(r"support", "supportCenterApp.urls", name="support"),
)

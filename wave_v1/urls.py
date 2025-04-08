"""
URL configuration for wave_v1 project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.urls import path, include
from django.conf.urls.static import static
from django.conf.urls import handler404
from authenticationApp.admin import super_admin_restricted_site

urlpatterns = [
    path("", include("extras.urls")),
    path("", include("authenticationApp.urls")),
    path("theadminportal/", include("adminDashboardApp.urls")),
    path("", include("accountManagementApp.urls")),
    path("", include("eventManagementApp.urls")),
    path("support/", include("supportCenterApp.urls")),
    path("colleges/", include("collegeManagementApp.urls")),
    path("", include("coreApp.urls")),
    path("", include("careerApp.urls")),
    path("", include("newsroomApp.urls")),
    path("", include("socialApp.urls")),
    path("ticketing/", include("eventTicketsApp.urls")),
    path("manager/", include("campusManagerApp.urls")),
    path("blog/", include("blogApp.urls")),
    path('chat/', include('supportCenterApp.urls')),
    path("admin/", super_admin_restricted_site.urls),
    path("analytics/", include("dataAnalyticsApp.urls")),
    path("dataApi/", include("dataAnalyticsAPI.urls")),
    path('nativeTSUReactAPI/', include('wave_v1.urlsapi')),
    path("silk/", include("silk.urls", namespace="silk")),
]

# Using s3 for media storage
if settings.DEBUG:
   urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = "extras.views.error_404"
handler403 = "extras.views.error_403"  # Added 403 handler
handler500 = "extras.views.error_500"  # Added 500 handler

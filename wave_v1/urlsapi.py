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
    # API endpoints
    path("nativeTSUReactAPI/", include("extras.nativeTSUReactAPIUrls")),
    path("nativeTSUReactAPI/auth/", include("authenticationApp.nativeTSUReactAPIUrls")),
    path("nativeTSUReactAPI/admin/", include("adminDashboardApp.nativeTSUReactAPIUrls")),
    path("nativeTSUReactAPI/account/", include("accountManagementApp.nativeTSUReactAPIUrls")),
    path("nativeTSUReactAPI/host/", include("eventManagementApp.nativeTSUReactAPIUrls")),
    path("nativeTSUReactAPI/support/", include("supportCenterApp.nativeTSUReactAPIUrls")),
    path("nativeTSUReactAPI/colleges/", include("collegeManagementApp.nativeTSUReactAPIUrls")),
    path("nativeTSUReactAPI/core/", include("coreApp.nativeTSUReactAPIUrls")),
    path("nativeTSUReactAPI/career/", include("careerApp.nativeTSUReactAPIUrls")),
    path("nativeTSUReactAPI/news/", include("newsroomApp.nativeTSUReactAPIUrls")),
    path("nativeTSUReactAPI/social/", include("socialApp.nativeTSUReactAPIUrls")),
    path("nativeTSUReactAPI/tickets/", include("eventTicketsApp.nativeTSUReactAPIUrls")),
    path("nativeTSUReactAPI/manager/", include("campusManagerApp.nativeTSUReactAPIUrls")),
    path("nativeTSUReactAPI/blog/", include("blogApp.nativeTSUReactAPIUrls")),
    path("nativeTSUReactAPI/chat/", include("supportCenterApp.nativeTSUReactAPIUrls")),
    path("nativeTSUReactAPI/analytics/", include("dataAnalyticsApp.nativeTSUReactAPIUrls")),
]
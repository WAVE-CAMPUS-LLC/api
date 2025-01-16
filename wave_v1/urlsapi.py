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
    path("nativeTSUReactAPI/", include("extras.apiUrls")),
    path("nativeTSUReactAPI/auth/", include("authenticationApp.apiUrls")),
    path("nativeTSUReactAPI/admin/", include("adminDashboardApp.apiUrls")),
    path("nativeTSUReactAPI/account/", include("accountManagementApp.apiUrls")),
    path("nativeTSUReactAPI/host/", include("eventManagementApp.apiUrls")),
    path("nativeTSUReactAPI/support/", include("supportCenterApp.apiUrls")),
    path("nativeTSUReactAPI/colleges/", include("collegeManagementApp.apiUrls")),
    path("nativeTSUReactAPI/core/", include("coreApp.apiUrls")),
    path("nativeTSUReactAPI/career/", include("careerApp.apiUrls")),
    path("nativeTSUReactAPI/news/", include("newsroomApp.apiUrls")),
    path("nativeTSUReactAPI/social/", include("socialApp.apiUrls")),
    path("nativeTSUReactAPI/tickets/", include("eventTicketsApp.apiUrls")),
    path("nativeTSUReactAPI/manager/", include("campusManagerApp.apiUrls")),
    path("nativeTSUReactAPI/blog/", include("blogApp.apiUrls")),
    path("nativeTSUReactAPI/chat/", include("supportCenterApp.apiUrls")),
    path("nativeTSUReactAPI/analytics/", include("dataAnalyticsApp.apiUrls")),
]

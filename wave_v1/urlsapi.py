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
    # # API endpoints
    # path("", include("extras.apiUrls")),
    path("auth/", include("authenticationApp.apiUrls")),
    # path("admin/", include("adminDashboardApp.apiUrls")),
    path("account/", include("accountManagementApp.apiUrls")),
    path("host/", include("eventManagementApp.apiUrls")),
    # path("support/", include("supportCenterApp.apiUrls")),
    path("colleges/", include("collegeManagementApp.apiUrls")),
    path("core/", include("coreApp.apiUrls")),
    # path("career/", include("careerApp.apiUrls")),
    # path("news/", include("newsroomApp.apiUrls")),
    # path("social/", include("socialApp.apiUrls")),
    # path("tickets/", include("eventTicketsApp.apiUrls")),
    # path("manager/", include("campusManagerApp.apiUrls")),
    # path("blog/", include("blogApp.apiUrls")),
    # path("chat/", include("supportCenterApp.apiUrls")),
    # path("analytics/", include("dataAnalyticsApp.apiUrls")),
]

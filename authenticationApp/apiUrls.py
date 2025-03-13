from django.urls import path
from . import apiViews
from .apiViews import logout_api

app_name="authentication_api"


urlpatterns = [
    path("api_login/", apiViews.login_api, name="login"),
    path('get-csrf-token/', apiViews.get_csrf_token, name='get-csrf-token'),
    path('api_logout/', logout_api, name='api-logout'),
]
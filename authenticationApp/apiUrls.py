from django.urls import path
from . import apiViews
from .apiViews import logout_api

app_name="authentication_api"

urlpatterns = [
    path("api_login/", apiViews.login_api, name="login"),
    path('get-csrf-token/', apiViews.get_csrf_token, name='get-csrf-token'),
    path('csrf/', apiViews.csrf_token_api, name='csrf-token-api'),
    path('csrf-test/', apiViews.csrf_test_api, name='csrf-test-api'),
    path('api_logout/', logout_api, name='api-logout'),
    path('forgot-password/', apiViews.forgot_password_api, name='forgot_password_api'),
    path("api_join/", apiViews.join_api, name="join"),
    path('reset-password/<str:uidb64>/<str:token>/', apiViews.set_new_password_api, name='reset_password_api'),
]
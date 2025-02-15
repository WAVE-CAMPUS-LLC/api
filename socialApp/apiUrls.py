from django.urls import path
from .apiViews import SocialHomeView

app_name = "socialAPI"


urlpatterns = [
    path("home/", SocialHomeView.as_view(), name="home"),
]
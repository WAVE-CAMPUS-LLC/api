from django.urls import path
from . import apiViews

app_name = "socialAPI"

urlpatterns = [
    path("home/", apiViews.SocialHomeView.as_view(), name="home"),
    path(
        "non-friends/", apiViews.NonFriendsListView.as_view(), name="non-friends-list"
    ),
    path(
        "profile/<str:username>/",
        apiViews.PublicProfileAPIView.as_view(),
        name="api_public_profile",
    ),
    path("crew/<uuid:crewId>/", apiViews.crew_api_view, name="api_crew"),
    path("crew/create/", apiViews.create_crew_api_view, name="api_create_crew"),
    path(
        "crew/<uuid:crewId>/kick/",
        apiViews.kick_member_view,
        name="api_kick_crew_member",
    ),
    path(
        "crew/<uuid:crewId>/delete/",
        apiViews.delete_crew_view,
        name="api_delete_crew",
    ),
    path(
        "crew/<uuid:crewId>/leave/",
        apiViews.leave_crew_view,
        name="api_leave_crew",
    ),
    path("crew/<uuid:crewId>/invite/", apiViews.invite_member, name="api_invite"),
]

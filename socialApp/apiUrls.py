from django.urls import path
from . import apiViews

app_name = "socialAPI"

urlpatterns = [
    path(
        "profile/<str:username>/",
        apiViews.public_profile,
        name="api_public_profile",
    ),
    path("profile/friends/", apiViews.user_friends_and_non_friends, name="api_friends"),
    path("profile/crews/", apiViews.user_crews, name="api_crewInfo"),
    path("crew/<uuid:crewId>/", apiViews.crew_api_view, name="api_crew"),
    path("friend/connect/<str:username>/", apiViews.send_friend_request_api, name="api_send_friend_request"),
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
    path("crew/<uuid:crewId>/member/", apiViews.crew_invite_action, name="api_crew_invite_action"),
    path(
        "crew/<uuid:crewId>/leave/",
        apiViews.leave_crew_view,
        name="api_leave_crew",
    ),
    path("crew/<uuid:crewId>/invite/", apiViews.invite_member, name="api_invite"),
]

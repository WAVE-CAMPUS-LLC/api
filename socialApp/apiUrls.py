from django.urls import path
from . import apiViews

app_name = "socialAPI"

urlpatterns = [
    # Put specific paths before pattern paths to avoid conflicts
    path("profile/friends/", apiViews.friends_api_view, name="api_friends"),
    path("profile/crews/", apiViews.crewInfo_api_view, name="api_crewInfo"),
        # Then include the pattern paths
    path(
        "profile/<str:username>/",
        apiViews.public_profile,
        name="api_public_profile",
    ),
    path("crew/<uuid:crewId>/", apiViews.crew_api_view, name="api_crew"),
    path("friend/connect/<str:username>/", apiViews.send_friend_request_api, name="api_send_friend_request"),
    path("crew/create/", apiViews.create_crew_api_view, name="api_create_crew"),
    path("profile/get-requests/", apiViews.getAllRequests, name="api_get_requests"),
    path("profile/friend-request/accept/", apiViews.accept_friend_request, name="accept_friend_request"),
    path("profile/friend-request/decline/", apiViews.decline_friend_request, name="decline_friend_request"),
    path("profile/friend-request/cancel/", apiViews.cancel_friend_request, name="cancel_friend_request"),
    path("crew/decline/", apiViews.decline_crew_request, name="decline_crew_request"),
    path("crew/accept/", apiViews.accept_crew_request, name="accept_crew_request"),
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

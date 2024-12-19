from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path("profile/<str:username>/", consumers.FriendRequestConsumer.as_asgi()),
    path("social/", consumers.SocialHomeConsumer.as_asgi()),
]

# websocket_urlpatterns = [
#     # WebSocket for handling friend requests sent at publicProfileView
#     re_path(r'/profile/(?P<username>[^/]+)/$', consumers.FriendRequestConsumer.as_asgi()),

#     # WebSocket for sending friend request updates to socialHomeView
#     re_path(r'/social/$', consumers.SocialHomeConsumer.as_asgi()),
# ]

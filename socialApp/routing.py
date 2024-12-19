from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path("profile/<str:username>/", consumers.FriendRequestConsumer.as_asgi()),
    path("social/", consumers.SocialHomeConsumer.as_asgi()),
]
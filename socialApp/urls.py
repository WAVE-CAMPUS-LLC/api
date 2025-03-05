from django.urls import path
from . import views

app_name = "social"


urlpatterns = [
    path('social/', views.socialHomeView, name='home'),
    path('profile/<str:username>/', views.publicProfileView, name='publicProfile'),
    path('copy-link-suucess/', views.copyLinkSuccessView, name='copyLinkSuccess'),
    path('social/crew/create/', views.createCrewView, name='createCrew'),
    path('social/crew/<uuid:crewId>/', views.crewView, name='crew'),
    path('social/send-friend-request/', views.send_friend_request_view, name='sendFriendRequest'),
    path('social/cancel-friend-request/', views.cancel_friend_request, name='cancelFriendRequest'),
]
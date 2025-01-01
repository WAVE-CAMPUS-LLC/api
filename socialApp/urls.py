from django.urls import path
from . import views

app_name = "social"


urlpatterns = [
    path('social/', views.socialHomeView, name='home'),
    path('profile/<str:username>/', views.publicProfileView, name='publicProfile'),
    path('copy-link-suucess/', views.copyLinkSuccessView, name='copyLinkSuccess'),
    path('social/crew/create/', views.createCrewView, name='createCrew'),
    path('social/crew/<uuid:crewId>/', views.crewView, name='crew'),
]
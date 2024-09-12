from django.urls import path
from . import views

app_name = "social"


urlpatterns = [
    path('social/', views.socialHomeView, name='home'),
    path('profile/<str:username>/', views.publicProfileView, name='publicProfile'),
]
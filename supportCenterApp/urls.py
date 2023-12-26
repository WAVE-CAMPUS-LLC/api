from django.urls import path
from . import views

app_name = "support"

urlpatterns = [
    path('support/', views.mainSupportView, name="home")
]

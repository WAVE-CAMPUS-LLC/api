from django.urls import path
from . import views


app_name = "eventManagement"

urlpatterns = [
    path("host/", views.hostView, name="hostHome"),
    path("host/onboarding/apply/", views.hostApplyView, name="hostApply")
]

from django.urls import path
from . import apiViews

app_name = "colleges_api"

urlpatterns = [
    path("colleges/list/", apiViews.college_campuses_api, name="colleges"),
]

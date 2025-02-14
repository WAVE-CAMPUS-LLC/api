from django.urls import path
from . import apiViews

app_name = "colleges_api"

urlpatterns = [
    path("colleges/list/", apiViews.college_campuses_api, name="colleges"),
    path("college/<uuid:collegeId>/", apiViews.view_college_information_api, name="college_info"),
]

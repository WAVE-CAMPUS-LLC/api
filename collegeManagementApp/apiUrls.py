from django.urls import path
from . import apiViews

app_name = "colleges_api"

urlpatterns = [
    path("colleges/list/", apiViews.college_campuses_api, name="colleges"),
    path(
        "college/<uuid:collegeId>/",
        apiViews.view_college_information_api,
        name="college_info",
    ),
    path(
        "college/<uuid:collegeId>/join/", apiViews.join_college_api, name="join_college"
    ),
    path(
        "college/<uuid:collegeId>/verify/",
        apiViews.verify_join_college_api,
        name="verify_college_join",
    ),
    path(
        "college/<uuid:collegeId>/exit/", apiViews.exit_college_api, name="exit_college"
    ),
]

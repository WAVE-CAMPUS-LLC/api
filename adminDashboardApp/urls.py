from django.urls import path
from . import views

app_name = "waveAdmin"

urlpatterns = [
    path("", views.adminPortalView, name="adminDashboard"),
    path("dashboard/", views.adminDashboardView, name="dashboard"),
    path("departments/", views.adminDepartmentView, name="departments"),
    path(
        "departments/<str:departmentID>/<str:department_name>/",
        views.adminDepartmentDetailedView,
        name="departmentDetails",
    ),
    path("applications", views.adminApplicationsView, name="applications"),
    path("events/", views.adminEventsView, name="events"),
    # User Management
    path("users/", views.adminUsersView, name="users"),
    path("users/<str:username>/", views.adminUserDetailedView, name="user-detailed"),
    # Roles & Permissions Management
    path("roles/", views.adminRoleView, name="roles"),
    path("careers/", views.adminCareersView, name="careers"),
    path(
        "careers/4ujdh sdha9 <uuid:roleID>ek98ep0 ujhdikjd/",
        views.adminCareerDetailView,
        name="careerDetails",
    ),
    path("finances/", views.adminFinanceView, name="finances"),
    path("support/", views.adminSupportView, name="support"),
    path("feedback/", views.adminFeedbackView, name="feedback"),
    path("colleges/", views.adminCollegeView, name="colleges"),
    path("colleges/<uuid:collegeId>/view/", views.adminCollegeDetailView, name="collegeDetail"),
    path("organizations/", views.adminCollegeOrgsView, name="organizations"),
    path("newsroom/", views.adminNewsRoomView, name="newsroom"),
    path("newsroom/create/", views.adminCreateNewsView, name="createNews"),
    path("newsroom/<uuid:newsId>/edit/", views.adminEditNewsView, name="editNews"),
    path("blog/", views.adminBlogView, name="newsroom"),
    
    path("emailing/", views.adminEmailingView, name="emailing"),
    path("send_emailwith_resend/", views.send_email, name="resend-emailing")
]

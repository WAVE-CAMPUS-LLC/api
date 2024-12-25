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
    path("analytics/users/", views.adminUserAnalyticsView, name="userAnalytics"),
    path(
        "applications/career/",
        views.adminCareerApplicationsView,
        name="careerApplications",
    ),
    path(
        "applications/career/<uuid:applicationId>/review/",
        views.adminCareerApplicationsDetailView,
        name="careerApplicationDetail",
    ),
    path(
        "applications/host/", views.adminHostApplicationsView, name="hostApplications"
    ),
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
    path("support/", views.adminSupportView, name="support"),
    path("feedback/", views.adminFeedbackView, name="feedback"),
    path("colleges/", views.adminCollegeView, name="colleges"),
    path(
        "colleges/<uuid:collegeId>/view/",
        views.adminCollegeDetailView,
        name="collegeDetail",
    ),
    path("organizations/", views.adminCollegeOrgsView, name="organizations"),
    path("newsroom/", views.adminNewsRoomView, name="newsroom"),
    path("newsroom/create/", views.adminCreateNewsView, name="createNews"),
    path("newsroom/<uuid:newsId>/edit/", views.adminEditNewsView, name="editNews"),
    path("blog/", views.adminBlogView, name="blog"),
    path("events/hosts/", views.adminEventHostsView, name="eventHosts"),
    path("emailing/", views.adminEmailingView, name="emailing"),
    path("send_emailwith_resend/", views.send_email, name="resend-emailing"),
    path(
        "ticket/<str:ticket_id>/",
        views.admin_ticket_details,
        name="admin_ticket_details",
    ),
    path(
        "ticket/<str:ticket_id>/messages/",
        views.ticket_messages,
        name="ticket_messages",
    ),
    path(
        "send_ticket_reply/<str:ticket_id>/",
        views.admin_send_ticket_reply,
        name="admin_send_ticket_reply",
    ),
    path(
        "toggle_ticket_status/<str:ticket_id>/",
        views.toggle_ticket_status,
        name="toggle_ticket_status",
    ),
    path(
        "financial/connected/accounts/",
        views.adminConnectedAccountsView,
        name="connectedAccounts",
    ),
    path(
        "financial/connected/accounts/<str:account_id>/",
        views.adminConnectedAccountDetailView,
        name="connectedAccountDetail",
    ),
    path("financial/products/", views.adminProductsView, name="stripeProducts"),
    path(
        "financial/settings/",
        views.adminFinancialSettingsView,
        name="financialSettings",
    ),
]

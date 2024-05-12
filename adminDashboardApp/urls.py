from django.urls import path
from . import views

app_name = "waveAdmin"

urlpatterns = [
    path('management/admin/', views.adminPortalView, name="adminDashboard"),
    path('management/admin/dashboard/', views.adminDashboardView, name="dashboard"),
    path('management/admin/departments', views.adminDepartmentView, name="departments"),
    path('management/admin/departments/<str:departmentID>/<str:department_name>/', views.adminDepartmentDetailedView, name="departmentDetails"),
    path('management/admin/events', views.adminEventsView, name="events"),
    path('management/admin/users', views.adminUsersView, name="users"),
    path('management/admin/users/<str:user_id>/', views.adminUserDetailedView, name="user-detailed"), 
    path('management/admin/careers', views.adminCareersView, name="careers"), 
    path('management/admin/finances', views.adminFinanceView, name="finances"), 
    path('management/admin/support', views.adminSupportView, name="support"),
    path('management/admin/feedback', views.adminFeedbackView, name="feedback")
]
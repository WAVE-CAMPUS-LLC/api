from django.urls import path
from . import views

app_name = "support"

urlpatterns = [
    path('support/', views.mainSupportView, name="home"),
    path('support/portal/', views.supportPortal, name="supportPortal"),
    path('support/ticket/new/', views.supportTicket, name="newTicket"), 
    path('feedback/', views.userFeedback, name="feedback"),
    
    path('support/portal/ticket/<str:ticket_id>/', views.viewTicket, name="viewTicket"),
]

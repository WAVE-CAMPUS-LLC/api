from django.urls import path
from . import views

app_name = "support"

urlpatterns = [
    path('', views.mainSupportView, name="home"),
    path('portal/', views.supportPortal, name="supportPortal"),
    path('ticket/new/', views.supportTicket, name="newTicket"), 
    path('feedback/', views.userFeedback, name="feedback"),
    
    path('portal/ticket/<str:ticket_id>/', views.viewTicket, name="viewTicket"),
]

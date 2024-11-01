from django.urls import path
from . import views


app_name = "eventTickets"

urlpatterns = [
    path('checkout/', views.checkoutView, name="checkout"),
    path("cart/update/", views.updateCartView, name="updateCart"),
    
    path("ticket/<str:mainId>/view/", views.viewTicket, name="viewTicket"),
]

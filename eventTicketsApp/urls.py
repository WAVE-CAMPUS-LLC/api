from django.urls import path
from . import views


app_name = "eventTickets"

urlpatterns = [
    path('checkout/', views.checkoutView, name="checkout"),
    path(r"cart/update/", views.updateCart, name="updateCart"),
]

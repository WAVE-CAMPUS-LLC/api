from django.urls import path
from . import views


app_name = "eventTickets"

urlpatterns = [
    path('checkout/', views.checkoutView, name="checkout"),
    path('paymentSuccessful/', views.paymentSuccessful, name="paymentSuccessful"),
    path('paymentFailed/', views.paymentFailed, name="paymentFailed"),
    path('stripeWebhook/', views.stripeWebhook, name="stripeWebhook"),
    path("cart/update/", views.updateCartView, name="updateCart"),
    
    path("ticket/<str:mainId>/view/", views.viewTicket, name="viewTicket"),
    path("ticket/verify/", views.verifyTicket, name="verifyTicket"),
    path('crew-purchase/', views.crewPurchaseView, name='crewPurchase'),
]

from django.urls import path
from . import views


app_name = "eventTickets"

urlpatterns = [
    path('checkout/', views.checkoutView, name="checkout"),
    # path('checkout/crew/<uuid:ticketId>/<uuid:crewId>/', views.crewCheckoutView, name="crewCheckout"),
    path('paymentSuccessful/', views.paymentSuccessful, name="paymentSuccessful"),
    path('paymentRedirect/', views.paymentRedirect, name="paymentRedirect"),
    path('paymentFailed/', views.paymentFailed, name="paymentFailed"),
    path('stripeWebhook/', views.stripeWebhook, name="stripeWebhook"),
    path("cart/update/", views.updateCartView, name="updateCart"),
    path("create-payment-intent/", views.createPaymentIntent, name="createPaymentIntent"),
    path("ticket/<str:mainId>/view/", views.viewTicket, name="viewTicket"),
    path("ticket/verify/", views.verifyTicket, name="verifyTicket"),
]

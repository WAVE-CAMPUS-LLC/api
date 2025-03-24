from django.urls import path
from . import views


app_name = "eventTickets"

urlpatterns = [
    path('paymentSuccessful/', views.paymentSuccessful, name="paymentSuccessful"),
    path('hostedCheckout/', views.hostedCheckout, name="hostedCheckout"),
    path('paymentRedirect/', views.paymentRedirect, name="paymentRedirect"),
    path('paymentFailed/', views.paymentFailed, name="paymentFailed"),
    path('stripeWebhook/', views.stripeWebhook, name="stripeWebhook"),
    path("cart/update/", views.updateCartView, name="updateCart"),
    path("ticket/<str:mainId>/view/", views.viewTicket, name="viewTicket"),
    path("ticket/verify/", views.verifyTicket, name="verifyTicket"),
    path("coupon/apply/", views.applyCouponCode, name="applyCouponCode"),
    path("ticket/activate/<str:mainId>", views.activateTicket, name="activateTicket"),
]

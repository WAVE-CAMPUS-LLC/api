from django.urls import path
from . import views


app_name = "extras"


urlpatterns = [
    path("about/", views.aboutView, name="about"),      
    path("faq/", views.faqView, name="faq"),
    path("privacy/", views.privacyView, name="privacy"), 
    path("safety/", views.safetyView, name="safety"), 
    path("terms/", views.termsView, name="terms"), 
    path("partner/", views.partnersView, name="partners"),
    path("affiliate/", views.affiliateView, name="affiliate"), 
]
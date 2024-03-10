from django.urls import path
from . import views


app_name = "extras"


urlpatterns = [
    path("company/", views.aboutView, name="about"),
    path("careers/", views.careersView, name="jobs"),
    path("newsroom/", views.newsroomView, name="newsroom"), 
    path("team/", views.teamView, name="teams"),
    
    path("faq/", views.faqView, name="faq"),
    path("privacy/", views.privacyView, name="privacy"), 
    path("safety/", views.safetyView, name="safety"), 
    path("terms/", views.termsView, name="terms"), 
    
    path("colleges/", views.collegesView, name="colleges"), 
    path("creators/", views.creatorsView, name="creators"), 
    path("hosts/", views.organizersView, name="organizers"),
    path("partners/", views.partnersView, name="partners")
]
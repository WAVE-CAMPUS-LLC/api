from django.urls import path
from . import views


app_name = "extras"


urlpatterns = [
    path("about/", views.aboutView, name="about"),
    
    path("newsroom/", views.newsroomView, name="newsroom"), 
    path("news/", views.newsView, name="news"),    
    
    path("team/", views.teamView, name="team"),
    
    path("faq/", views.faqView, name="faq"),
    path("privacy/", views.privacyView, name="privacy"), 
    path("safety/", views.safetyView, name="safety"), 
    path("terms/", views.termsView, name="terms"), 
    
    path("colleges/", views.collegeCampusesView, name="colleges"), 
    path("partner/", views.partnersView, name="partners"),
    path("affiliate/", views.affiliateView, name="affiliate"), 
]
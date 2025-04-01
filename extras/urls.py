from django.urls import path
from . import views
from .deep_links import handle_event_link, serve_apple_app_site_association


app_name = "extras"


urlpatterns = [
    path("about/", views.aboutView, name="about"),      
    path("faq/", views.faqView, name="faq"),
    path("privacy/", views.privacyView, name="privacy"), 
    path("safety/", views.safetyView, name="safety"), 
    path("terms/", views.termsView, name="terms"), 
    path("partner/", views.partnersView, name="partners"),
    path('policy/verified-hosts/', views.verifiedHostsView, name="verifiedHosts"),
    path('policy/active-members/', views.activeMembersView, name="activeMembers"),
    path("affiliate/", views.affiliateView, name="affiliate"),
    
    # Universal Links handlers
    path("apple-app-site-association", serve_apple_app_site_association, name="apple_app_site_association"),
    path(".well-known/apple-app-site-association", serve_apple_app_site_association, name="apple_app_site_association_well_known"),
    path("app/event/<uuid:eventId>/", handle_event_link, name="app_event_link"),
]
from django.contrib.sitemaps.views import sitemap
from django.urls import path

urlpatterns = [
    path("sitemap.xml", sitemap, {"sitemaps": {}}),
]
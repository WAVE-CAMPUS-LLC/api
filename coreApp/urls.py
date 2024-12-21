from django.urls import path
from . import views


app_name = "core"

urlpatterns = [
    path("", views.indexView, name="index"),
    path("explore/", views.exploreView, name="explore"),
    path("categories/", views.categoriesView, name="categories"),
    path("event/<uuid:eventId>/", views.eventDetailsView, name="eventDetails"),
    path("event/<str:eventId>/<uuid:token>/", views.eventDetailsView, name="eventDetails_withToken"),
    path("category/<str:name>/", views.categoryView, name="category"),
    path("load-more/", views.load_more_events, name="load_more_events"),
    path("event/reserved/", views.rsvpConfirm, name="rsvpConfirm"),
    path("explore/search/", views.searchEvents, name="search"),
    path("social/search/", views.search_users, name="search_users"),
    path('send-connect-request/', views.send_connect_request, name='send_connect_request'),  
]

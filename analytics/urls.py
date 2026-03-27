from django.urls import path

from analytics.api_views import track

urlpatterns = [
    path("api/track/", track, name="api_track"),
]

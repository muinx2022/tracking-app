from django.urls import path
from django.views.generic import RedirectView

from core.views import (
    DashboardView,
    ProjectCreateView,
    ProjectDeleteView,
    ProjectDetailView,
    ProjectUpdateView,
    TrackTestView,
)

urlpatterns = [
    path("user/dashboard/", DashboardView.as_view(), name="user_dashboard"),
    path("user/projects/new/", ProjectCreateView.as_view(), name="user_project_create"),
    path(
        "user/projects/<int:pk>/edit/",
        ProjectUpdateView.as_view(),
        name="user_project_update",
    ),
    path(
        "user/projects/<int:pk>/delete/",
        ProjectDeleteView.as_view(),
        name="user_project_delete",
    ),
    path("user/projects/<int:pk>/", ProjectDetailView.as_view(), name="user_project_detail"),
    path("user/track-test/<int:pk>/", TrackTestView.as_view(), name="user_track_test"),
    path("dashboard/", RedirectView.as_view(pattern_name="user_dashboard", permanent=False)),
    path(
        "projects/new/",
        RedirectView.as_view(pattern_name="user_project_create", permanent=False),
    ),
    path(
        "projects/<int:pk>/edit/",
        RedirectView.as_view(pattern_name="user_project_update", permanent=False),
    ),
    path(
        "projects/<int:pk>/delete/",
        RedirectView.as_view(pattern_name="user_project_delete", permanent=False),
    ),
    path(
        "projects/<int:pk>/",
        RedirectView.as_view(pattern_name="user_project_detail", permanent=False),
    ),
    path(
        "track-test/<int:pk>/",
        RedirectView.as_view(pattern_name="user_track_test", permanent=False),
    ),
]

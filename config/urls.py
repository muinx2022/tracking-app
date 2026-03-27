from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from core.views import HomeView

admin.site.site_header = "Tracking administration"
admin.site.site_title = "Tracking admin"
admin.site.index_title = "Overview"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", HomeView.as_view(), name="home"),
    path("user", HomeView.as_view()),
    path("user/", HomeView.as_view(), name="user_home"),
    path(
        "user/login/",
        auth_views.LoginView.as_view(template_name="registration/login.html"),
        name="user_login",
    ),
    path("user/logout/", auth_views.LogoutView.as_view(), name="user_logout"),
    path(
        "accounts/login/",
        auth_views.LoginView.as_view(template_name="registration/login.html"),
    ),
    path("accounts/logout/", auth_views.LogoutView.as_view()),
    path("", include("core.urls")),
    path("", include("analytics.urls")),
]

from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path

from apps.common.views.media import media_view

app_name = "common"

urlpatterns = [
    # Django's own views. The login view is reachable without a login; Django marks it so itself.
    path("anmelden/", LoginView.as_view(template_name="common/login.html"), name="login-view"),
    path("abmelden/", LogoutView.as_view(), name="logout-view"),
    # Every photo and scan, behind the login - see docs/patterns/data-storage.md, "Photos and scans".
    path("medien/<path:path>", media_view, name="media-view"),
]

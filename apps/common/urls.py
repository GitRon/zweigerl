from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path

from apps.common.views.favicon import favicon_view
from apps.common.views.media import media_view

app_name = "common"

urlpatterns = [
    # Django's own views. The login view is reachable without a login; Django marks it so itself.
    path("login/", LoginView.as_view(template_name="common/login.html"), name="login-view"),
    path("logout/", LogoutView.as_view(), name="logout-view"),
    # Every photo and scan, behind the login - see docs/patterns/data-storage.md, "Photos and scans".
    path("media/<path:path>", media_view, name="media-view"),
    # The browser's own guess for the tab icon, on every page that does not link one - the admin above all.
    path("favicon.ico", favicon_view, name="favicon-view"),
]

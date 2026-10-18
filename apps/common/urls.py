from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path

app_name = "common"

urlpatterns = [
    # Django's own views. The login view is reachable without a login; Django marks it so itself.
    path("anmelden/", LoginView.as_view(template_name="common/login.html"), name="login-view"),
    path("abmelden/", LogoutView.as_view(), name="logout-view"),
]

from django.urls import path

from apps.stammbaum.views.start import start_view

app_name = "stammbaum"

urlpatterns = [
    path("", start_view, name="start-view"),
]

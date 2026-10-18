from django.urls import path

from apps.family_tree.views.start import start_view

app_name = "family_tree"

urlpatterns = [
    path("", start_view, name="start-view"),
]

from django.urls import path

from apps.family_tree.views.person_search import person_search_view
from apps.family_tree.views.start import start_view

app_name = "family_tree"

urlpatterns = [
    path("", start_view, name="start-view"),
    path("persons/search/", person_search_view, name="person-search-view"),
]

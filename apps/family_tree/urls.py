from django.urls import path

from apps.family_tree.views.new_person import (
    create_person_view,
    create_relative_view,
    new_person_view,
    new_relative_view,
)
from apps.family_tree.views.person import person_view
from apps.family_tree.views.person_search import person_search_view
from apps.family_tree.views.start import start_view
from apps.family_tree.views.tree_settings import home_person_view, tree_settings_view

app_name = "family_tree"

urlpatterns = [
    path("", start_view, name="start-view"),
    path("persons/", create_person_view, name="create-person-view"),
    path("persons/new/", new_person_view, name="new-person-view"),
    path("persons/<int:pk>/", person_view, name="person-view"),
    path("persons/<int:pk>/relatives/", create_relative_view, name="create-relative-view"),
    path("persons/<int:pk>/relatives/new/", new_relative_view, name="new-relative-view"),
    path("persons/search/", person_search_view, name="person-search-view"),
    path("settings/", tree_settings_view, name="tree-settings-view"),
    path("settings/home-person/", home_person_view, name="home-person-view"),
]

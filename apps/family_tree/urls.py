from django.urls import path

from apps.family_tree.views.person import person_view
from apps.family_tree.views.person_search import person_search_view
from apps.family_tree.views.source import source_create_view, source_files_view
from apps.family_tree.views.start import start_view
from apps.family_tree.views.tree_settings import home_person_view, tree_settings_view

app_name = "family_tree"

urlpatterns = [
    path("", start_view, name="start-view"),
    path("persons/<int:pk>/", person_view, name="person-view"),
    path("persons/search/", person_search_view, name="person-search-view"),
    path("persons/<int:pk>/sources/", source_create_view, name="source-create-view"),
    path("persons/<int:pk>/sources/<int:source_pk>/files/", source_files_view, name="source-files-view"),
    path("settings/", tree_settings_view, name="tree-settings-view"),
    path("settings/home-person/", home_person_view, name="home-person-view"),
]

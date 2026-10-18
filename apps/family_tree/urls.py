from django.urls import path

from apps.family_tree.views.fact import (
    change_fact_view,
    create_fact_view,
    delete_fact_view,
    edit_fact_view,
    new_fact_view,
)
from apps.family_tree.views.new_person import (
    create_person_view,
    create_relative_view,
    new_person_view,
    new_relative_view,
)
from apps.family_tree.views.person import person_name_view, person_view
from apps.family_tree.views.person_search import person_search_view
from apps.family_tree.views.photo import photo_create_view, photo_describe_view, photo_portrait_view
from apps.family_tree.views.source import source_create_view, source_files_view
from apps.family_tree.views.start import start_view
from apps.family_tree.views.tree_settings import home_person_view, tree_settings_view

app_name = "family_tree"

urlpatterns = [
    path("", start_view, name="start-view"),
    path("persons/", create_person_view, name="create-person-view"),
    path("persons/new/", new_person_view, name="new-person-view"),
    path("persons/<int:pk>/", person_view, name="person-view"),
    path("persons/<int:pk>/name/", person_name_view, name="person-name-view"),
    path("persons/<int:pk>/facts/", create_fact_view, name="create-fact-view"),
    path("persons/<int:pk>/facts/new/", new_fact_view, name="new-fact-view"),
    path("persons/<int:pk>/facts/<int:fact_pk>/", change_fact_view, name="change-fact-view"),
    path("persons/<int:pk>/facts/<int:fact_pk>/edit/", edit_fact_view, name="edit-fact-view"),
    path("persons/<int:pk>/facts/<int:fact_pk>/delete/", delete_fact_view, name="delete-fact-view"),
    path("persons/<int:pk>/relatives/", create_relative_view, name="create-relative-view"),
    path("persons/<int:pk>/relatives/new/", new_relative_view, name="new-relative-view"),
    path("persons/search/", person_search_view, name="person-search-view"),
    path("persons/<int:pk>/sources/", source_create_view, name="source-create-view"),
    path("persons/<int:pk>/sources/<int:source_pk>/files/", source_files_view, name="source-files-view"),
    path("persons/<int:pk>/photos/", photo_create_view, name="photo-create-view"),
    path("persons/<int:pk>/photos/<int:photo_pk>/portrait/", photo_portrait_view, name="photo-portrait-view"),
    path("persons/<int:pk>/photos/<int:photo_pk>/", photo_describe_view, name="photo-describe-view"),
    path("settings/", tree_settings_view, name="tree-settings-view"),
    path("settings/home-person/", home_person_view, name="home-person-view"),
]

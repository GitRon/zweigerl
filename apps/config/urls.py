from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    # Default
    path("admin/", admin.site.urls),
    # Custom
    path("", include("apps.common.urls")),
    path("", include("apps.family_tree.urls")),
]

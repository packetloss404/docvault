"""URL configuration for the entities module."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"entity-types", views.EntityTypeViewSet, basename="entity-type")

urlpatterns = [
    path("entities/", views.EntityListView.as_view(), name="entity-list"),
    path(
        "documents/<int:document_id>/entities/",
        views.DocumentEntityListView.as_view(),
        name="document-entity-list",
    ),
    path(
        "entities/<str:entity_type>/<path:value>/documents/",
        views.EntityDocumentsView.as_view(),
        name="entity-documents",
    ),
    path("", include(router.urls)),
]

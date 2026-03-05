"""URL configuration for the relationships module."""

from django.urls import path

from . import views

urlpatterns = [
    # Relationship Types
    path(
        "relationship-types/",
        views.RelationshipTypeListCreateView.as_view(),
        name="relationship-type-list",
    ),
    path(
        "relationship-types/<int:pk>/",
        views.RelationshipTypeDetailView.as_view(),
        name="relationship-type-detail",
    ),
    # Document Relationships
    path(
        "documents/<int:document_id>/relationships/",
        views.DocumentRelationshipListCreateView.as_view(),
        name="document-relationship-list",
    ),
    path(
        "documents/<int:document_id>/relationships/<int:pk>/",
        views.DocumentRelationshipDeleteView.as_view(),
        name="document-relationship-detail",
    ),
    # Relationship Graph
    path(
        "documents/<int:document_id>/relationship-graph/",
        views.DocumentRelationshipGraphView.as_view(),
        name="document-relationship-graph",
    ),
]

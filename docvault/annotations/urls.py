"""URL configuration for the annotations module."""

from django.urls import path

from . import views

urlpatterns = [
    path(
        "documents/<int:document_id>/annotations/",
        views.DocumentAnnotationViewSet.as_view({"get": "list", "post": "create"}),
        name="document-annotations",
    ),
    path(
        "documents/<int:document_id>/annotations/<int:pk>/",
        views.DocumentAnnotationViewSet.as_view(
            {"get": "retrieve", "patch": "partial_update", "delete": "destroy"},
        ),
        name="document-annotation-detail",
    ),
    path(
        "documents/<int:document_id>/annotations/export/",
        views.DocumentAnnotationViewSet.as_view({"post": "export"}),
        name="document-annotations-export",
    ),
    path(
        "documents/<int:document_id>/annotations/<int:annotation_id>/replies/",
        views.AnnotationReplyListCreateView.as_view(),
        name="annotation-replies",
    ),
]

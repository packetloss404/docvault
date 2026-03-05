"""URL configuration for the ML classification module."""

from django.urls import path

from . import views

urlpatterns = [
    path(
        "documents/<int:document_pk>/suggestions/",
        views.DocumentSuggestionsView.as_view(),
        name="document-suggestions",
    ),
    path(
        "classifier/status/",
        views.ClassifierStatusView.as_view(),
        name="classifier-status",
    ),
    path(
        "classifier/train/",
        views.ClassifierTrainView.as_view(),
        name="classifier-train",
    ),
]

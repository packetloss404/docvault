"""URL configuration for core module."""

from django.urls import path

from . import views

urlpatterns = [
    path("preferences/", views.UserPreferencesView.as_view(), name="user-preferences"),
    path("bulk/", views.BulkOperationView.as_view(), name="bulk-operation"),
]

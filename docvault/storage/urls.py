"""URL configuration for the storage module."""

from django.urls import path

from . import views

urlpatterns = [
    path(
        "storage/dedup-stats/",
        views.DedupStatsView.as_view(),
        name="storage-dedup-stats",
    ),
    path(
        "storage/verify-integrity/",
        views.VerifyIntegrityView.as_view(),
        name="storage-verify-integrity",
    ),
]

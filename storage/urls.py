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
    path(
        "storage/config/",
        views.StorageConfigView.as_view(),
        name="storage-config",
    ),
    path(
        "storage/config/test/",
        views.StorageConnectionTestView.as_view(),
        name="storage-config-test",
    ),
    path(
        "storage/backends/",
        views.StorageBackendsView.as_view(),
        name="storage-backends",
    ),
]

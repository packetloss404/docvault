"""URL configuration for the processing module."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views
from .barcode_views import BarcodeConfigView, BulkAsnAssignView, NextAsnView

router = DefaultRouter()
router.register(r"tasks", views.ProcessingTaskViewSet, basename="processingtask")

urlpatterns = [
    path("asn/next/", NextAsnView.as_view(), name="asn-next"),
    path("asn/bulk-assign/", BulkAsnAssignView.as_view(), name="asn-bulk-assign"),
    path("barcode/config/", BarcodeConfigView.as_view(), name="barcode-config"),
    path("", include(router.urls)),
]

"""URL configuration for the Zone OCR module."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"zone-ocr-templates", views.ZoneOCRTemplateViewSet, basename="zone-ocr-template")

urlpatterns = [
    path(
        "zone-ocr-templates/<int:template_id>/fields/",
        views.ZoneOCRFieldListCreateView.as_view(),
        name="zone-ocr-field-list",
    ),
    path(
        "zone-ocr-templates/<int:template_id>/fields/<int:pk>/",
        views.ZoneOCRFieldDetailView.as_view(),
        name="zone-ocr-field-detail",
    ),
    path(
        "zone-ocr-templates/<int:template_id>/test/",
        views.TestTemplateView.as_view(),
        name="zone-ocr-test",
    ),
    path(
        "zone-ocr-results/",
        views.ZoneOCRResultListView.as_view(),
        name="zone-ocr-result-list",
    ),
    path(
        "zone-ocr-results/<int:pk>/",
        views.ZoneOCRResultCorrectionView.as_view(),
        name="zone-ocr-result-detail",
    ),
    path("", include(router.urls)),
]

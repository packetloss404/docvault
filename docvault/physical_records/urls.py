"""URL configuration for the physical_records module."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(
    r"physical-locations",
    views.PhysicalLocationViewSet,
    basename="physical-location",
)
router.register(
    r"physical-records",
    views.PhysicalRecordViewSet,
    basename="physical-record",
)

urlpatterns = [
    path(
        "documents/<int:document_id>/charge-out/",
        views.ChargeOutView.as_view(),
        name="charge-out",
    ),
    path(
        "documents/<int:document_id>/charge-in/",
        views.ChargeInView.as_view(),
        name="charge-in",
    ),
    path(
        "physical-records/<int:pk>/barcode-checkout/",
        views.BarcodeCheckoutView.as_view(),
        name="barcode-checkout",
    ),
    path(
        "charge-outs/",
        views.ChargeOutListView.as_view(),
        name="charge-out-list",
    ),
    path(
        "charge-outs/overdue/",
        views.OverdueChargeOutView.as_view(),
        name="overdue-charge-outs",
    ),
    path(
        "physical-records/<int:pk>/destruction-certificate/",
        views.DestructionCertificateView.as_view(),
        name="destruction-certificate",
    ),
    path("", include(router.urls)),
]

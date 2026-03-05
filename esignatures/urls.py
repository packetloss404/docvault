"""URL configuration for the e-signatures app."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(
    r"signature-requests",
    views.SignatureRequestViewSet,
    basename="signature-request",
)

urlpatterns = [
    # Authenticated
    path(
        "documents/<int:document_id>/signature-request/",
        views.DocumentSignatureRequestView.as_view(),
        name="document-signature-request",
    ),
    path(
        "signature-requests/<int:pk>/audit/",
        views.SignatureRequestAuditView.as_view(),
        name="signature-request-audit",
    ),
    # Public signing endpoints
    path(
        "sign/<uuid:token>/",
        views.PublicSigningView.as_view(),
        name="public-signing",
    ),
    path(
        "sign/<uuid:token>/view_page/",
        views.PublicViewPageView.as_view(),
        name="public-signing-view-page",
    ),
    path(
        "sign/<uuid:token>/complete/",
        views.PublicSigningCompleteView.as_view(),
        name="public-signing-complete",
    ),
    path(
        "sign/<uuid:token>/decline/",
        views.PublicSigningDeclineView.as_view(),
        name="public-signing-decline",
    ),
    path("", include(router.urls)),
]

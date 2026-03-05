"""URL configuration for the legal_hold module."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"legal-holds", views.LegalHoldViewSet, basename="legalhold")

urlpatterns = [
    path(
        "legal-holds/<int:hold_id>/acknowledge/",
        views.CustodianAcknowledgeView.as_view(),
        name="legalhold-acknowledge",
    ),
    path("", include(router.urls)),
]

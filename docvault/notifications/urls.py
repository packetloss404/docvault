"""URL configuration for the notifications module."""

from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"notifications", views.NotificationViewSet, basename="notification")
router.register(
    r"notification-preferences",
    views.NotificationPreferenceViewSet,
    basename="notification-preference",
)
router.register(r"quotas", views.QuotaViewSet, basename="quota")

urlpatterns = [
    path("quotas/usage/", views.QuotaUsageView.as_view(), name="quota-usage"),
    *router.urls,
]

"""URL configuration for the documents module."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"documents", views.DocumentViewSet, basename="document")
router.register(r"document-types", views.DocumentTypeViewSet, basename="documenttype")

urlpatterns = [
    path("documents/upload/", views.DocumentUploadView.as_view(), name="document-upload"),
    path("", include(router.urls)),
]

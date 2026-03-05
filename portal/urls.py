from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"portals", views.PortalConfigViewSet, basename="portal-config")
router.register(r"document-requests", views.DocumentRequestViewSet, basename="document-request")

urlpatterns = [
    # Admin endpoints
    path("portal-submissions/", views.PortalSubmissionListView.as_view(), name="portal-submission-list"),
    path("portal-submissions/<int:pk>/review/", views.PortalSubmissionReviewView.as_view(), name="portal-submission-review"),
    # Public endpoints (no auth)
    path("portal/<slug:slug>/", views.PublicPortalView.as_view(), name="public-portal"),
    path("portal/<slug:slug>/upload/", views.PublicPortalUploadView.as_view(), name="public-portal-upload"),
    path("request/<str:token>/", views.PublicRequestView.as_view(), name="public-request"),
    path("request/<str:token>/upload/", views.PublicRequestUploadView.as_view(), name="public-request-upload"),
    path("", include(router.urls)),
]

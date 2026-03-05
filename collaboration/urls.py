"""URL configuration for the collaboration module."""

from django.urls import path

from . import views

urlpatterns = [
    # Comments
    path(
        "documents/<int:pk>/comments/",
        views.DocumentCommentListView.as_view(),
        name="document-comments",
    ),
    path(
        "documents/<int:pk>/comments/<int:cid>/",
        views.DocumentCommentDetailView.as_view(),
        name="document-comment-detail",
    ),
    # Check-in / Check-out
    path(
        "documents/<int:pk>/checkout/",
        views.DocumentCheckoutView.as_view(),
        name="document-checkout",
    ),
    path(
        "documents/<int:pk>/checkin/",
        views.DocumentCheckinView.as_view(),
        name="document-checkin",
    ),
    path(
        "documents/<int:pk>/checkout_status/",
        views.DocumentCheckoutStatusView.as_view(),
        name="document-checkout-status",
    ),
    # Share Links
    path(
        "documents/<int:pk>/share/",
        views.DocumentShareCreateView.as_view(),
        name="document-share-create",
    ),
    path("share-links/", views.ShareLinkListView.as_view(), name="share-link-list"),
    path(
        "share-links/<int:pk>/",
        views.ShareLinkDeleteView.as_view(),
        name="share-link-delete",
    ),
    path(
        "share/<slug:slug>/",
        views.PublicShareAccessView.as_view(),
        name="share-public-access",
    ),
    # Activity Feed
    path(
        "documents/<int:pk>/activity/",
        views.DocumentActivityView.as_view(),
        name="document-activity",
    ),
    path("activity/", views.GlobalActivityView.as_view(), name="global-activity"),
]

"""URL configuration for the search module."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"saved-views", views.SavedViewViewSet, basename="savedview")
router.register(r"search/synonyms", views.SearchSynonymViewSet, basename="search-synonym")
router.register(r"search/curations", views.SearchCurationViewSet, basename="search-curation")

urlpatterns = [
    path("search/", views.SearchView.as_view(), name="search"),
    path(
        "search/autocomplete/",
        views.SearchAutocompleteView.as_view(),
        name="search-autocomplete",
    ),
    path(
        "search/similar/<int:pk>/",
        views.SimilarDocumentsView.as_view(),
        name="search-similar",
    ),
    path(
        "search/click/",
        views.SearchClickView.as_view(),
        name="search-click",
    ),
    path(
        "search/analytics/",
        views.SearchAnalyticsView.as_view(),
        name="search-analytics",
    ),
    path("", include(router.urls)),
]

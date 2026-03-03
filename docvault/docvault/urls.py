"""Root URL configuration for DocVault."""

from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from core.health import health_view, metrics_view, readiness_view

urlpatterns = [
    path("admin/", admin.site.urls),
    # Health / Observability (no auth)
    path("health/", health_view, name="health"),
    path("ready/", readiness_view, name="readiness"),
    path("metrics/", metrics_view, name="metrics"),
    # API v1
    path("api/v1/", include("security.urls")),
    path("api/v1/", include("documents.urls")),
    path("api/v1/", include("processing.urls")),
    path("api/v1/", include("organization.urls")),
    path("api/v1/", include("search.urls")),
    path("api/v1/", include("workflows.urls")),
    path("api/v1/", include("sources.urls")),
    path("api/v1/", include("notifications.urls")),
    path("api/v1/", include("ml.urls")),
    path("api/v1/", include("ai.urls")),
    path("api/v1/", include("collaboration.urls")),
    path("api/v1/", include("zone_ocr.urls")),
    path("api/v1/", include("entities.urls")),
    path("api/v1/", include("relationships.urls")),
    path("api/v1/", include("portal.urls")),
    path("api/v1/", include("esignatures.urls")),
    path("api/v1/", include("annotations.urls")),
    path("api/v1/", include("legal_hold.urls")),
    path("api/v1/", include("storage.urls")),
    path("api/v1/", include("physical_records.urls")),
    path("api/v1/", include("core.urls")),
    # OpenAPI
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]

# Debug toolbar URLs
if settings.DEBUG:
    try:
        import debug_toolbar

        urlpatterns = [
            path("__debug__/", debug_toolbar.urls),
        ] + urlpatterns
    except ImportError:
        pass

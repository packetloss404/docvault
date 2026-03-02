"""Root URL configuration for DocVault."""

from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    # API v1
    path("api/v1/", include("security.urls")),
    path("api/v1/", include("documents.urls")),
    path("api/v1/", include("processing.urls")),
    path("api/v1/", include("organization.urls")),
    path("api/v1/", include("search.urls")),
    path("api/v1/", include("workflows.urls")),
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

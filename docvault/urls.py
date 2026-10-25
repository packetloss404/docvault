"""Root URL configuration for DocVault."""

from django.conf import settings
from django.contrib import admin
from django.http import HttpResponse
from django.template import TemplateDoesNotExist, loader
from django.urls import include, path, re_path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from core.health import health_view, metrics_view, readiness_view

_FRONTEND_MISSING_MESSAGE = (
    "DocVault API is running, but the Angular frontend has not been built.\n"
    "Run `npm ci && npx ng build` in src-ui/ and point FRONTEND_DIR at the\n"
    "build output (defaults to STATIC_ROOT/frontend), or use the dev server on\n"
    "http://localhost:4200. API endpoints under /api/v1/ are unaffected.\n"
)


def spa_fallback(request, *args, **kwargs):
    """Serve the Angular SPA's index.html for deep links.

    The template is resolved eagerly so a missing frontend build degrades to a
    plain 503 with instructions instead of a TemplateDoesNotExist traceback.
    """
    try:
        template = loader.get_template("index.html")
    except TemplateDoesNotExist:
        return HttpResponse(_FRONTEND_MISSING_MESSAGE, status=503, content_type="text/plain")
    return HttpResponse(template.render({}, request))

urlpatterns = [
    re_path(r"^admin/(?:users|groups|roles|storage|permissions)/?$", spa_fallback, name="spa-admin"),
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
    # Allauth (SSO/OIDC)
    path("accounts/", include("allauth.urls")),
    # OpenAPI
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    # SPA deep-link fallback: serve index.html for all unmatched routes.
    # Hashed bundles and public assets (/fonts/*.woff2, /favicon.ico) are served
    # ahead of this by WhiteNoise from settings.FRONTEND_DIR at the URL root.
    re_path(
        r"^(?!api/|admin/|health/|ready/|metrics/|static/|media/|accounts/|__debug__/).*$",
        spa_fallback,
        name="spa-fallback",
    ),
]

# Debug toolbar URLs
if settings.DEBUG:
    try:
        import debug_toolbar

        # debug_toolbar.urls is a (urlpatterns, app_name) pair, so it has to be
        # wrapped in include(); passing it to path() directly raises
        # "not enough values to unpack" and breaks every management command.
        urlpatterns = [
            path("__debug__/", include(debug_toolbar.urls)),
        ] + urlpatterns
    except ImportError:
        pass

"""Health check, readiness, and metrics endpoints for DocVault."""

import logging
import time

from django.conf import settings
from django.db import connection
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

logger = logging.getLogger(__name__)

# In-memory metrics counters (lightweight, no external dependencies)
_metrics = {
    "http_requests_total": 0,
    "http_request_duration_seconds_sum": 0.0,
    "documents_processed_total": 0,
    "documents_uploaded_total": 0,
    "task_queue_depth": 0,
    "errors_total": 0,
}


def increment_metric(name, amount=1):
    """Increment a metric counter."""
    if name in _metrics:
        _metrics[name] += amount


def get_metrics():
    """Return a copy of current metrics."""
    return dict(_metrics)


def _check_database():
    """Check database connectivity."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


def _check_redis():
    """Check Redis connectivity."""
    try:
        import redis

        url = getattr(settings, "REDIS_URL", "redis://localhost:6379")
        client = redis.from_url(url, socket_timeout=2)
        client.ping()
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


def _check_elasticsearch():
    """Check Elasticsearch connectivity."""
    if not getattr(settings, "ELASTICSEARCH_ENABLED", False):
        return {"status": "disabled"}

    try:
        from search.client import get_client

        client = get_client()
        if client is None:
            return {"status": "disabled"}
        info = client.info()
        return {"status": "ok", "version": info.get("version", {}).get("number", "unknown")}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


def _check_celery():
    """Check Celery worker availability."""
    try:
        from docvault.celery import app as celery_app

        inspector = celery_app.control.inspect(timeout=2)
        active = inspector.active()
        if active:
            worker_count = len(active)
            return {"status": "ok", "workers": worker_count}
        return {"status": "warning", "detail": "No active workers"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@api_view(["GET"])
@permission_classes([AllowAny])
def health_view(request):
    """Basic health check — confirms the application is running.

    GET /health/
    Returns 200 if the app can respond, with DB status.
    """
    db = _check_database()
    healthy = db["status"] == "ok"

    return JsonResponse(
        {
            "status": "healthy" if healthy else "unhealthy",
            "database": db,
        },
        status=200 if healthy else 503,
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def readiness_view(request):
    """Readiness check — confirms all required services are connected.

    GET /ready/
    Returns 200 if all services are reachable.
    """
    checks = {
        "database": _check_database(),
        "redis": _check_redis(),
        "elasticsearch": _check_elasticsearch(),
        "celery": _check_celery(),
    }

    all_ok = all(
        c["status"] in ("ok", "disabled")
        for c in checks.values()
    )

    return JsonResponse(
        {
            "status": "ready" if all_ok else "not_ready",
            "checks": checks,
        },
        status=200 if all_ok else 503,
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def metrics_view(request):
    """Prometheus-compatible metrics endpoint.

    GET /metrics/
    Returns metrics in Prometheus text exposition format.
    """
    from django.contrib.auth.models import User

    lines = []

    # Application metrics
    for name, value in _metrics.items():
        metric_type = "counter" if "total" in name else "gauge"
        lines.append(f"# TYPE docvault_{name} {metric_type}")
        lines.append(f"docvault_{name} {value}")

    # Dynamic metrics
    try:
        from documents.models import Document
        doc_count = Document.objects.count()
        lines.append("# TYPE docvault_documents_count gauge")
        lines.append(f"docvault_documents_count {doc_count}")
    except Exception:
        pass

    try:
        user_count = User.objects.filter(is_active=True).count()
        lines.append("# TYPE docvault_active_users_count gauge")
        lines.append(f"docvault_active_users_count {user_count}")
    except Exception:
        pass

    from django.http import HttpResponse
    return HttpResponse(
        "\n".join(lines) + "\n",
        content_type="text/plain; version=0.0.4; charset=utf-8",
    )


class MetricsMiddleware:
    """Middleware to track HTTP request metrics."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.monotonic()
        response = self.get_response(request)
        duration = time.monotonic() - start

        _metrics["http_requests_total"] += 1
        _metrics["http_request_duration_seconds_sum"] += duration

        if response.status_code >= 500:
            _metrics["errors_total"] += 1

        return response

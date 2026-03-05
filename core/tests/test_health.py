"""Tests for health check, readiness, and metrics endpoints."""

import pytest
from rest_framework.test import APIClient


@pytest.fixture
def client():
    return APIClient()


class TestHealthEndpoint:
    """GET /health/ - no auth required."""

    @pytest.mark.django_db
    def test_health_returns_200_when_db_ok(self, client):
        response = client.get("/health/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"]["status"] == "ok"

    @pytest.mark.django_db
    def test_health_no_auth_required(self, client):
        # No force_authenticate - should still work
        response = client.get("/health/")
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_health_response_has_expected_keys(self, client):
        response = client.get("/health/")
        data = response.json()
        assert "status" in data
        assert "database" in data
        assert "status" in data["database"]


class TestReadinessEndpoint:
    """GET /ready/ - checks all services."""

    @pytest.mark.django_db
    def test_readiness_returns_response(self, client):
        response = client.get("/ready/")
        # May be 200 or 503 depending on Redis/Celery availability in test env
        assert response.status_code in (200, 503)
        data = response.json()
        assert "status" in data
        assert "checks" in data

    @pytest.mark.django_db
    def test_readiness_checks_include_database(self, client):
        response = client.get("/ready/")
        data = response.json()
        assert "database" in data["checks"]
        # Database should be ok since we're using in-memory sqlite
        assert data["checks"]["database"]["status"] == "ok"

    @pytest.mark.django_db
    def test_readiness_checks_include_redis(self, client):
        response = client.get("/ready/")
        data = response.json()
        assert "redis" in data["checks"]

    @pytest.mark.django_db
    def test_readiness_checks_include_elasticsearch(self, client):
        response = client.get("/ready/")
        data = response.json()
        assert "elasticsearch" in data["checks"]

    @pytest.mark.django_db
    def test_readiness_checks_include_celery(self, client):
        response = client.get("/ready/")
        data = response.json()
        assert "celery" in data["checks"]

    @pytest.mark.django_db
    def test_readiness_no_auth_required(self, client):
        response = client.get("/ready/")
        # Should not return 401 or 403
        assert response.status_code not in (401, 403)


class TestMetricsEndpoint:
    """GET /metrics/ - Prometheus format."""

    @pytest.mark.django_db
    def test_metrics_returns_200(self, client):
        response = client.get("/metrics/")
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_metrics_returns_prometheus_content_type(self, client):
        response = client.get("/metrics/")
        assert "text/plain" in response["Content-Type"]

    @pytest.mark.django_db
    def test_metrics_contains_http_requests_total(self, client):
        response = client.get("/metrics/")
        content = response.content.decode()
        assert "docvault_http_requests_total" in content

    @pytest.mark.django_db
    def test_metrics_contains_documents_count(self, client):
        response = client.get("/metrics/")
        content = response.content.decode()
        assert "docvault_documents_count" in content

    @pytest.mark.django_db
    def test_metrics_contains_active_users_count(self, client):
        response = client.get("/metrics/")
        content = response.content.decode()
        assert "docvault_active_users_count" in content

    @pytest.mark.django_db
    def test_metrics_contains_type_annotations(self, client):
        response = client.get("/metrics/")
        content = response.content.decode()
        assert "# TYPE docvault_http_requests_total counter" in content

    @pytest.mark.django_db
    def test_metrics_no_auth_required(self, client):
        response = client.get("/metrics/")
        assert response.status_code not in (401, 403)


class TestIncrementMetric:
    """Test the increment_metric helper function."""

    def test_increment_known_metric(self):
        from core.health import get_metrics, increment_metric

        initial = get_metrics()["documents_uploaded_total"]
        increment_metric("documents_uploaded_total")
        assert get_metrics()["documents_uploaded_total"] == initial + 1

    def test_increment_with_custom_amount(self):
        from core.health import get_metrics, increment_metric

        initial = get_metrics()["documents_processed_total"]
        increment_metric("documents_processed_total", amount=5)
        assert get_metrics()["documents_processed_total"] == initial + 5

    def test_increment_unknown_metric_does_not_raise(self):
        from core.health import increment_metric

        # Should silently ignore unknown metrics
        increment_metric("nonexistent_metric")

    def test_increment_unknown_metric_does_not_add_key(self):
        from core.health import get_metrics, increment_metric

        increment_metric("nonexistent_metric")
        assert "nonexistent_metric" not in get_metrics()


class TestGetMetrics:
    """Test the get_metrics helper function."""

    def test_get_metrics_returns_dict(self):
        from core.health import get_metrics

        metrics = get_metrics()
        assert isinstance(metrics, dict)

    def test_get_metrics_returns_copy(self):
        from core.health import get_metrics

        m1 = get_metrics()
        m2 = get_metrics()
        assert m1 is not m2

    def test_get_metrics_has_expected_keys(self):
        from core.health import get_metrics

        metrics = get_metrics()
        expected_keys = {
            "http_requests_total",
            "http_request_duration_seconds_sum",
            "documents_processed_total",
            "documents_uploaded_total",
            "task_queue_depth",
            "errors_total",
        }
        assert expected_keys == set(metrics.keys())

    def test_mutating_copy_does_not_affect_original(self):
        from core.health import get_metrics

        m1 = get_metrics()
        m1["errors_total"] = 999999
        m2 = get_metrics()
        assert m2["errors_total"] != 999999


class TestMetricsMiddleware:
    """Test the MetricsMiddleware class."""

    def test_middleware_increments_request_counter(self):
        from core.health import MetricsMiddleware, get_metrics

        initial = get_metrics()["http_requests_total"]

        # Create a simple mock get_response
        class FakeResponse:
            status_code = 200

        def get_response(request):
            return FakeResponse()

        middleware = MetricsMiddleware(get_response)
        middleware(object())  # Pass a dummy request

        assert get_metrics()["http_requests_total"] == initial + 1

    def test_middleware_tracks_duration(self):
        from core.health import MetricsMiddleware, get_metrics

        initial_duration = get_metrics()["http_request_duration_seconds_sum"]

        class FakeResponse:
            status_code = 200

        def get_response(request):
            return FakeResponse()

        middleware = MetricsMiddleware(get_response)
        middleware(object())

        assert get_metrics()["http_request_duration_seconds_sum"] > initial_duration

    def test_middleware_increments_errors_on_500(self):
        from core.health import MetricsMiddleware, get_metrics

        initial_errors = get_metrics()["errors_total"]

        class FakeResponse:
            status_code = 500

        def get_response(request):
            return FakeResponse()

        middleware = MetricsMiddleware(get_response)
        middleware(object())

        assert get_metrics()["errors_total"] == initial_errors + 1

    def test_middleware_does_not_increment_errors_on_4xx(self):
        from core.health import MetricsMiddleware, get_metrics

        initial_errors = get_metrics()["errors_total"]

        class FakeResponse:
            status_code = 404

        def get_response(request):
            return FakeResponse()

        middleware = MetricsMiddleware(get_response)
        middleware(object())

        assert get_metrics()["errors_total"] == initial_errors

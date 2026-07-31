"""Tests for the S3-compatible backend and its provider presets.

These cover the compatibility logic that differs between AWS S3, Backblaze B2,
MinIO and R2. They deliberately do not talk to a network: the client is stubbed,
because what is being asserted is which options we hand to boto3.
"""

from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from storage.backends.s3 import PROVIDER_PRESETS, S3StorageBackend, build_client_config
from storage.models import StorageConfig
from storage.utils import S3_COMPATIBLE, _resolve_config, get_storage_backend


class ClientConfigTest(TestCase):
    """The provider preset decides checksum and addressing behaviour."""

    def test_b2_disables_checksums(self):
        """Backblaze B2 rejects the checksum headers boto3 sends by default."""
        config = build_client_config("b2")
        self.assertEqual(config.request_checksum_calculation, "when_required")
        self.assertEqual(config.response_checksum_validation, "when_required")

    def test_minio_disables_checksums(self):
        config = build_client_config("minio")
        self.assertEqual(config.request_checksum_calculation, "when_required")

    def test_r2_disables_checksums(self):
        config = build_client_config("r2")
        self.assertEqual(config.request_checksum_calculation, "when_required")

    def test_aws_keeps_default_checksums(self):
        """Real S3 supports them, so we must not weaken integrity there."""
        config = build_client_config("s3")
        self.assertNotEqual(
            getattr(config, "request_checksum_calculation", None), "when_required"
        )

    def test_minio_uses_path_style(self):
        """Virtual-host style does not resolve for a bare MinIO host."""
        self.assertEqual(build_client_config("minio").s3["addressing_style"], "path")

    def test_b2_uses_virtual_style(self):
        self.assertEqual(build_client_config("b2").s3["addressing_style"], "virtual")

    def test_explicit_addressing_overrides_preset(self):
        config = build_client_config("b2", addressing_style="path")
        self.assertEqual(config.s3["addressing_style"], "path")

    def test_explicit_checksum_flag_overrides_preset(self):
        config = build_client_config("b2", disable_checksums=False)
        self.assertNotEqual(
            getattr(config, "request_checksum_calculation", None), "when_required"
        )

    def test_unknown_provider_falls_back_to_s3_preset(self):
        self.assertEqual(
            build_client_config("wasabi").s3["addressing_style"],
            PROVIDER_PRESETS["s3"]["addressing_style"],
        )

    def test_signature_version_is_v4(self):
        self.assertEqual(build_client_config("s3").signature_version, "s3v4")


class S3BackendKeyTest(TestCase):
    """Key namespacing and listing."""

    def _backend(self, **overrides):
        config = {
            "S3_PROVIDER": "b2",
            "S3_BUCKET_NAME": "vault",
            "S3_ACCESS_KEY": "k",
            "S3_SECRET_KEY": "s",
            "S3_REGION": "us-west-004",
            "S3_ENDPOINT_URL": "https://s3.us-west-004.backblazeb2.com",
            "S3_PREFIX": "documents",
            **overrides,
        }
        with patch("boto3.session.Session") as session:
            session.return_value.client.return_value = MagicMock()
            return S3StorageBackend(config=config)

    def test_prefixes_keys(self):
        self.assertEqual(self._backend()._key("a.pdf"), "documents/a.pdf")

    def test_does_not_double_prefix(self):
        backend = self._backend()
        self.assertEqual(backend._key("documents/a.pdf"), "documents/a.pdf")

    def test_custom_prefix(self):
        self.assertEqual(self._backend(S3_PREFIX="vault")._key("a.pdf"), "vault/a.pdf")

    def test_empty_prefix_leaves_key_alone(self):
        self.assertEqual(self._backend(S3_PREFIX="")._key("a.pdf"), "a.pdf")

    def test_strip_restores_local_style_name(self):
        self.assertEqual(self._backend()._strip("documents/a.pdf"), "a.pdf")

    def test_does_not_auto_create_bucket_by_default(self):
        """Scoped credentials usually cannot create buckets."""
        backend = self._backend()
        backend.client.create_bucket.assert_not_called()

    def test_config_overrides_django_settings(self):
        """A database configuration must win over the environment."""
        backend = self._backend(S3_BUCKET_NAME="from-db")
        self.assertEqual(backend.bucket_name, "from-db")


class BackendResolutionTest(TestCase):
    """Which backend `get_storage_backend()` returns."""

    def test_b2_is_s3_compatible(self):
        self.assertIn("b2", S3_COMPATIBLE)

    def test_local_is_not_s3_compatible(self):
        self.assertNotIn("local", S3_COMPATIBLE)

    @override_settings(STORAGE_BACKEND="local")
    def test_env_backend_used_when_no_db_config(self):
        backend, config = _resolve_config()
        self.assertEqual(backend, "local")
        self.assertIsNone(config)

    @override_settings(STORAGE_BACKEND="local")
    def test_disabled_db_config_is_ignored(self):
        StorageConfig.objects.create(enabled=False, backend="b2", bucket_name="x")
        backend, config = _resolve_config()
        self.assertEqual(backend, "local")
        self.assertIsNone(config)

    @override_settings(STORAGE_BACKEND="local")
    def test_enabled_db_config_wins(self):
        StorageConfig.objects.create(
            enabled=True, backend="b2", bucket_name="vault", access_key="k", secret_key="s"
        )
        backend, config = _resolve_config()
        self.assertEqual(backend, "b2")
        self.assertEqual(config["S3_BUCKET_NAME"], "vault")

    @override_settings(STORAGE_BACKEND="local", STORAGE_ENCRYPTION_ENABLED=False)
    def test_local_backend_instance(self):
        from storage.backends.local import LocalStorageBackend

        self.assertIsInstance(get_storage_backend(), LocalStorageBackend)


class StorageConfigModelTest(TestCase):
    """The configuration is a singleton."""

    def test_load_creates_a_row(self):
        config = StorageConfig.load()
        self.assertEqual(config.pk, 1)

    def test_saving_never_creates_a_second_row(self):
        StorageConfig.objects.create(backend="s3")
        StorageConfig.objects.create(backend="b2")
        self.assertEqual(StorageConfig.objects.count(), 1)

    def test_as_backend_config_maps_field_names(self):
        config = StorageConfig(
            backend="b2", bucket_name="vault", access_key="k", secret_key="s"
        )
        mapped = config.as_backend_config()
        self.assertEqual(mapped["S3_PROVIDER"], "b2")
        self.assertEqual(mapped["S3_BUCKET_NAME"], "vault")
        self.assertEqual(mapped["S3_SECRET_KEY"], "s")

    def test_blank_addressing_style_maps_to_none(self):
        """Blank means "use the provider preset", not "empty string"."""
        config = StorageConfig(backend="b2", addressing_style="")
        self.assertIsNone(config.as_backend_config()["S3_ADDRESSING_STYLE"])

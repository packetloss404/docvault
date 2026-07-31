"""Serializers for the storage module."""

from rest_framework import serializers

from .models import StorageConfig
from .utils import S3_COMPATIBLE


class StorageConfigSerializer(serializers.ModelSerializer):
    """Storage configuration.

    `secret_key` is write-only: it is accepted on save but never returned.
    Clients read `has_secret_key` to know whether one is stored, and omit the
    field entirely to leave the existing secret untouched.
    """

    secret_key = serializers.CharField(
        write_only=True, required=False, allow_blank=True, style={"input_type": "password"}
    )
    has_secret_key = serializers.SerializerMethodField()
    requires_endpoint = serializers.SerializerMethodField()

    class Meta:
        model = StorageConfig
        fields = [
            "enabled",
            "backend",
            "bucket_name",
            "endpoint_url",
            "region",
            "access_key",
            "secret_key",
            "has_secret_key",
            "prefix",
            "addressing_style",
            "disable_checksums",
            "auto_create_bucket",
            "requires_endpoint",
            "updated_at",
        ]
        read_only_fields = ["updated_at"]

    def get_has_secret_key(self, obj) -> bool:
        return bool(obj.secret_key)

    def get_requires_endpoint(self, obj) -> bool:
        return obj.backend in {"b2", "minio", "r2"}

    def validate(self, attrs):
        merged = {**{f: getattr(self.instance, f, None) for f in self.Meta.fields}, **attrs}
        backend = merged.get("backend")

        if not merged.get("enabled"):
            return attrs

        if backend in S3_COMPATIBLE:
            missing = [
                name
                for name, value in (
                    ("bucket_name", merged.get("bucket_name")),
                    ("access_key", merged.get("access_key")),
                )
                if not value
            ]
            # An existing stored secret counts as present.
            has_secret = bool(attrs.get("secret_key")) or bool(
                getattr(self.instance, "secret_key", "")
            )
            if not has_secret:
                missing.append("secret_key")
            if missing:
                raise serializers.ValidationError(
                    {name: "Required for object storage." for name in missing}
                )

            if backend in {"b2", "minio", "r2"} and not merged.get("endpoint_url"):
                raise serializers.ValidationError(
                    {"endpoint_url": f"Required for {backend}; it has no default endpoint."}
                )

        return attrs

    def update(self, instance, validated_data):
        # Omitting the field leaves the stored secret alone; sending "" clears it.
        if "secret_key" not in validated_data:
            validated_data.pop("secret_key", None)
        return super().update(instance, validated_data)


class StorageConnectionTestSerializer(serializers.Serializer):
    """Ad-hoc credentials to probe before committing them."""

    backend = serializers.ChoiceField(choices=StorageConfig.Backend.choices)
    bucket_name = serializers.CharField(required=False, allow_blank=True)
    endpoint_url = serializers.CharField(required=False, allow_blank=True)
    region = serializers.CharField(required=False, allow_blank=True)
    access_key = serializers.CharField(required=False, allow_blank=True)
    secret_key = serializers.CharField(required=False, allow_blank=True)
    prefix = serializers.CharField(required=False, allow_blank=True)
    addressing_style = serializers.CharField(required=False, allow_blank=True)
    disable_checksums = serializers.BooleanField(required=False, allow_null=True)

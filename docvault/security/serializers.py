"""Serializers for the security module."""

from django.contrib.auth import authenticate
from django.contrib.auth.models import Group, User
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import AuditLogEntry, OTPDevice, Permission, Role, Signature


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ["id", "namespace", "codename", "name"]
        read_only_fields = ["id"]


class RoleSerializer(serializers.ModelSerializer):
    permissions = PermissionSerializer(many=True, read_only=True)
    permission_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        write_only=True,
        queryset=Permission.objects.all(),
        source="permissions",
        required=False,
    )
    group_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        write_only=True,
        queryset=Group.objects.all(),
        source="groups",
        required=False,
    )

    class Meta:
        model = Role
        fields = [
            "id", "name", "description",
            "permissions", "permission_ids",
            "groups", "group_ids",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id", "username", "email", "first_name", "last_name",
            "is_active", "is_staff", "groups", "date_joined",
        ]
        read_only_fields = ["id", "date_joined"]


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ["id", "username", "email", "password", "first_name", "last_name"]
        read_only_fields = ["id"]

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class GroupSerializer(serializers.ModelSerializer):
    user_count = serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = ["id", "name", "user_count"]
        read_only_fields = ["id"]

    def get_user_count(self, obj):
        return obj.user_set.count()


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(username=data["username"], password=data["password"])
        if user is None:
            raise serializers.ValidationError("Invalid credentials.")
        if not user.is_active:
            raise serializers.ValidationError("User account is disabled.")
        data["user"] = user
        return data


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id", "username", "email", "first_name", "last_name",
            "is_active", "is_staff", "date_joined",
        ]
        read_only_fields = ["id", "username", "is_staff", "date_joined"]


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate_new_password(self, value):
        validate_password(value)
        return value


# --- Signature Serializers ---


class SignatureSerializer(serializers.ModelSerializer):
    signer_username = serializers.CharField(source="signer.username", read_only=True)

    class Meta:
        model = Signature
        fields = [
            "id", "document", "signer", "signer_username",
            "signature_data", "key_id", "algorithm",
            "verified", "verified_at", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class SignDocumentSerializer(serializers.Serializer):
    key_id = serializers.CharField(required=False, default="")


class VerifyDocumentSerializer(serializers.Serializer):
    signature_id = serializers.IntegerField(required=False, help_text="Verify a specific signature.")


# --- OTP Serializers ---


class OTPSetupSerializer(serializers.Serializer):
    """Response for OTP setup — contains secret, URI, and QR code."""
    secret = serializers.CharField(read_only=True)
    provisioning_uri = serializers.CharField(read_only=True)
    qr_code_base64 = serializers.CharField(read_only=True)


class OTPConfirmSerializer(serializers.Serializer):
    code = serializers.CharField(min_length=6, max_length=6)


class OTPVerifySerializer(serializers.Serializer):
    code = serializers.CharField(max_length=8, help_text="TOTP code or backup code.")


class OTPDisableSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True)


class OTPStatusSerializer(serializers.Serializer):
    enabled = serializers.BooleanField(read_only=True)
    confirmed = serializers.BooleanField(read_only=True)


# --- Audit Log Serializers ---


class AuditLogEntrySerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True, default="")

    class Meta:
        model = AuditLogEntry
        fields = [
            "id", "timestamp", "user", "username", "action",
            "model_type", "object_id", "detail",
            "ip_address", "user_agent",
        ]
        read_only_fields = fields


# --- Scanner Serializers ---


class ScannerDeviceSerializer(serializers.Serializer):
    id = serializers.CharField()
    vendor = serializers.CharField()
    model = serializers.CharField()
    type = serializers.CharField()
    label = serializers.CharField()


class ScanRequestSerializer(serializers.Serializer):
    dpi = serializers.IntegerField(default=300, min_value=75, max_value=1200)
    color_mode = serializers.ChoiceField(
        choices=["color", "gray", "lineart"],
        default="color",
    )
    paper_size = serializers.ChoiceField(
        choices=["a4", "letter", "legal", "auto"],
        default="a4",
    )


# --- GPG Key Serializers ---


class GPGKeySerializer(serializers.Serializer):
    key_id = serializers.CharField()
    fingerprint = serializers.CharField()
    uids = serializers.ListField(child=serializers.CharField())
    expires = serializers.CharField()
    length = serializers.CharField()


class GPGKeyImportSerializer(serializers.Serializer):
    key_data = serializers.CharField(help_text="ASCII-armored GPG public key.")

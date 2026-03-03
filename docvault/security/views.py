"""Views for the security module."""

import base64
import csv
import io
import logging

from django.contrib.auth.models import Group, User
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import generics, permissions, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AuditLogEntry, OTPDevice, Permission, Role, Signature, log_audit_event
from .serializers import (
    AuditLogEntrySerializer,
    ChangePasswordSerializer,
    GPGKeyImportSerializer,
    GPGKeySerializer,
    GroupSerializer,
    LoginSerializer,
    OTPConfirmSerializer,
    OTPDisableSerializer,
    OTPStatusSerializer,
    OTPVerifySerializer,
    PermissionSerializer,
    ProfileSerializer,
    RoleSerializer,
    ScannerDeviceSerializer,
    ScanRequestSerializer,
    SignatureSerializer,
    SignDocumentSerializer,
    UserCreateSerializer,
    UserSerializer,
    VerifyDocumentSerializer,
)

logger = logging.getLogger(__name__)


# --- Auth Views ---


class LoginView(APIView):
    """Authenticate and return a token."""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            "token": token.key,
            "user_id": user.pk,
            "username": user.username,
            "email": user.email,
        })


class LogoutView(APIView):
    """Invalidate the current token."""

    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class RegisterView(APIView):
    """Register a new user and return a token."""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = UserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token = Token.objects.create(user=user)
        return Response(
            {
                "token": token.key,
                "user_id": user.pk,
                "username": user.username,
            },
            status=status.HTTP_201_CREATED,
        )


class ProfileView(generics.RetrieveUpdateAPIView):
    """Get or update the current user's profile."""

    serializer_class = ProfileSerializer

    def get_object(self):
        return self.request.user


class ChangePasswordView(APIView):
    """Change the current user's password."""

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if not request.user.check_password(serializer.validated_data["old_password"]):
            return Response(
                {"old_password": "Wrong password."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save()

        # Invalidate existing token and create new one
        Token.objects.filter(user=request.user).delete()
        token = Token.objects.create(user=request.user)

        return Response({"token": token.key})


class GenerateTokenView(APIView):
    """Generate (or regenerate) an API token for the current user."""

    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        token = Token.objects.create(user=request.user)
        return Response({"token": token.key}, status=status.HTTP_201_CREATED)


# --- Management Views ---


class UserViewSet(viewsets.ModelViewSet):
    """CRUD for users (admin only)."""

    queryset = User.objects.all().order_by("username")
    permission_classes = [permissions.IsAdminUser]

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        return UserSerializer


class GroupViewSet(viewsets.ModelViewSet):
    """CRUD for groups (admin only)."""

    queryset = Group.objects.all().order_by("name")
    serializer_class = GroupSerializer
    permission_classes = [permissions.IsAdminUser]


class RoleViewSet(viewsets.ModelViewSet):
    """CRUD for roles (admin only)."""

    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [permissions.IsAdminUser]


class PermissionListView(generics.ListAPIView):
    """List all system permissions (admin only)."""

    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = [permissions.IsAdminUser]
    pagination_class = None


# --- Document Signing Views ---


class DocumentSignView(APIView):
    """Sign a document with GPG."""

    def post(self, request, document_id):
        from documents.models import Document
        from storage.utils import get_storage_backend
        from .signing import sign_data

        try:
            document = Document.objects.get(pk=document_id)
        except Document.DoesNotExist:
            return Response({"error": "Document not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = SignDocumentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            backend = get_storage_backend()
            file_handle = backend.open(document.filename)
            file_data = file_handle.read()
            if hasattr(file_handle, "close"):
                file_handle.close()
        except Exception:
            return Response(
                {"error": "Could not read document file."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        try:
            result = sign_data(file_data, key_id=serializer.validated_data.get("key_id", ""))
        except (ValueError, RuntimeError) as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        sig = Signature.objects.create(
            document=document,
            signer=request.user,
            signature_data=result["signature"],
            key_id=result["key_id"],
            algorithm=result["algorithm"],
            verified=True,
            verified_at=timezone.now(),
        )

        log_audit_event(
            user=request.user,
            action=AuditLogEntry.ACTION_SIGN,
            model_type="Document",
            object_id=document.pk,
            detail=f"Signed with key {result['key_id']}",
        )

        return Response(SignatureSerializer(sig).data, status=status.HTTP_201_CREATED)


class DocumentSignatureListView(APIView):
    """List signatures for a document."""

    def get(self, request, document_id):
        signatures = Signature.objects.filter(document_id=document_id).select_related("signer")
        serializer = SignatureSerializer(signatures, many=True)
        return Response(serializer.data)


class DocumentVerifyView(APIView):
    """Verify document signatures."""

    def post(self, request, document_id):
        from documents.models import Document
        from storage.utils import get_storage_backend
        from .signing import verify_signature

        try:
            document = Document.objects.get(pk=document_id)
        except Document.DoesNotExist:
            return Response({"error": "Document not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = VerifyDocumentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            backend = get_storage_backend()
            file_handle = backend.open(document.filename)
            file_data = file_handle.read()
            if hasattr(file_handle, "close"):
                file_handle.close()
        except Exception:
            return Response(
                {"error": "Could not read document file."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        sig_id = serializer.validated_data.get("signature_id")
        if sig_id:
            sigs = Signature.objects.filter(pk=sig_id, document=document)
        else:
            sigs = Signature.objects.filter(document=document)

        results = []
        for sig in sigs:
            try:
                result = verify_signature(file_data, sig.signature_data)
                sig.verified = result["valid"]
                sig.verified_at = timezone.now()
                sig.save(update_fields=["verified", "verified_at"])
                results.append({
                    "signature_id": sig.pk,
                    "valid": result["valid"],
                    "key_id": result.get("key_id", ""),
                })
            except Exception as e:
                results.append({
                    "signature_id": sig.pk,
                    "valid": False,
                    "error": str(e),
                })

        log_audit_event(
            user=request.user,
            action=AuditLogEntry.ACTION_VERIFY,
            model_type="Document",
            object_id=document.pk,
        )

        return Response({"results": results})


# --- GPG Key Management ---


class GPGKeyListView(APIView):
    """List available GPG keys."""

    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        from .signing import list_keys
        keys = list_keys()
        serializer = GPGKeySerializer(keys, many=True)
        return Response(serializer.data)


class GPGKeyImportView(APIView):
    """Import a GPG key."""

    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        from .signing import import_key

        serializer = GPGKeyImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = import_key(serializer.validated_data["key_data"])
        return Response(result, status=status.HTTP_201_CREATED)


class GPGKeyDeleteView(APIView):
    """Delete a GPG key by fingerprint."""

    permission_classes = [permissions.IsAdminUser]

    def delete(self, request, fingerprint):
        from .signing import delete_key

        success = delete_key(fingerprint)
        if success:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response({"error": "Failed to delete key."}, status=status.HTTP_400_BAD_REQUEST)


# --- OTP Views ---


class OTPSetupView(APIView):
    """Begin OTP setup: generate secret and QR code."""

    def post(self, request):
        from .otp import generate_totp_secret, get_provisioning_uri, generate_qr_code

        # Delete existing unconfirmed device
        OTPDevice.objects.filter(user=request.user, confirmed=False).delete()

        # Check if already confirmed
        if OTPDevice.objects.filter(user=request.user, confirmed=True).exists():
            return Response(
                {"error": "OTP is already enabled. Disable it first."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        secret = generate_totp_secret()
        uri = get_provisioning_uri(secret, request.user.username)
        qr_bytes = generate_qr_code(uri)
        qr_b64 = base64.b64encode(qr_bytes).decode()

        OTPDevice.objects.create(user=request.user, secret=secret, confirmed=False)

        log_audit_event(
            user=request.user,
            action=AuditLogEntry.ACTION_OTP_SETUP,
            model_type="OTPDevice",
            detail="OTP setup initiated",
        )

        return Response({
            "secret": secret,
            "provisioning_uri": uri,
            "qr_code_base64": qr_b64,
        })


class OTPConfirmView(APIView):
    """Confirm OTP setup by verifying the first code."""

    def post(self, request):
        from .otp import verify_totp, hash_backup_code

        serializer = OTPConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            device = OTPDevice.objects.get(user=request.user, confirmed=False)
        except OTPDevice.DoesNotExist:
            return Response(
                {"error": "No pending OTP setup found."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not verify_totp(device.secret, serializer.validated_data["code"]):
            return Response(
                {"error": "Invalid OTP code."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Generate and store backup codes
        backup_codes = OTPDevice.generate_backup_codes()
        device.backup_codes = [hash_backup_code(c) for c in backup_codes]
        device.confirmed = True
        device.save()

        return Response({
            "confirmed": True,
            "backup_codes": backup_codes,
        })


class OTPDisableView(APIView):
    """Disable OTP for the current user."""

    def post(self, request):
        serializer = OTPDisableSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if not request.user.check_password(serializer.validated_data["password"]):
            return Response(
                {"error": "Wrong password."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        deleted = OTPDevice.objects.filter(user=request.user).delete()[0]
        if not deleted:
            return Response(
                {"error": "OTP is not enabled."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        log_audit_event(
            user=request.user,
            action=AuditLogEntry.ACTION_OTP_DISABLE,
            model_type="OTPDevice",
            detail="OTP disabled",
        )

        return Response({"disabled": True})


class OTPVerifyView(APIView):
    """Verify an OTP code during login flow."""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        from .otp import verify_totp, verify_backup_code

        serializer = OTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        code = serializer.validated_data["code"]

        # The user must be identified — either already authenticated or via a temp token
        user = request.user
        if not user or not user.is_authenticated:
            return Response(
                {"error": "Authentication required."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            device = OTPDevice.objects.get(user=user, confirmed=True)
        except OTPDevice.DoesNotExist:
            return Response(
                {"error": "OTP is not enabled for this user."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Try TOTP first
        if verify_totp(device.secret, code):
            return Response({"verified": True})

        # Try backup code
        idx = verify_backup_code(code, device.backup_codes)
        if idx >= 0:
            # Consume the backup code
            device.backup_codes.pop(idx)
            device.save(update_fields=["backup_codes"])
            return Response({"verified": True, "backup_code_used": True})

        return Response(
            {"error": "Invalid OTP code."},
            status=status.HTTP_400_BAD_REQUEST,
        )


class OTPStatusView(APIView):
    """Check OTP status for current user."""

    def get(self, request):
        try:
            device = OTPDevice.objects.get(user=request.user)
            return Response({"enabled": True, "confirmed": device.confirmed})
        except OTPDevice.DoesNotExist:
            return Response({"enabled": False, "confirmed": False})


# --- Audit Log Views ---


class AuditLogListView(generics.ListAPIView):
    """List audit log entries (admin only, paginated, filterable)."""

    serializer_class = AuditLogEntrySerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        qs = AuditLogEntry.objects.select_related("user").all()

        # Filter by user
        user_id = self.request.query_params.get("user")
        if user_id:
            qs = qs.filter(user_id=user_id)

        # Filter by action
        action_type = self.request.query_params.get("action")
        if action_type:
            qs = qs.filter(action=action_type)

        # Filter by model type
        model_type = self.request.query_params.get("model_type")
        if model_type:
            qs = qs.filter(model_type=model_type)

        # Filter by date range
        date_from = self.request.query_params.get("date_from")
        if date_from:
            qs = qs.filter(timestamp__gte=date_from)

        date_to = self.request.query_params.get("date_to")
        if date_to:
            qs = qs.filter(timestamp__lte=date_to)

        return qs


class AuditLogExportView(APIView):
    """Export audit log as CSV or JSON."""

    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        export_format = request.query_params.get("export_format", "json")
        qs = AuditLogEntry.objects.select_related("user").order_by("-timestamp")[:10000]

        if export_format == "csv":
            response = HttpResponse(content_type="text/csv")
            response["Content-Disposition"] = 'attachment; filename="audit_log.csv"'
            writer = csv.writer(response)
            writer.writerow(["timestamp", "username", "action", "model_type", "object_id", "detail", "ip_address"])
            for entry in qs:
                writer.writerow([
                    entry.timestamp.isoformat(),
                    entry.user.username if entry.user else "",
                    entry.action,
                    entry.model_type,
                    entry.object_id or "",
                    entry.detail,
                    entry.ip_address or "",
                ])
            return response

        # Default: JSON
        serializer = AuditLogEntrySerializer(qs, many=True)
        return Response(serializer.data)


# --- Scanner Views ---


class ScannerListView(APIView):
    """List available SANE scanners."""

    def get(self, request):
        from sources.scanner import discover_scanners
        scanners = discover_scanners()
        serializer = ScannerDeviceSerializer(scanners, many=True)
        return Response(serializer.data)


class ScannerScanView(APIView):
    """Trigger a scan on a SANE scanner."""

    def post(self, request, device_id):
        from sources.scanner import scan_document

        serializer = ScanRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            image_data = scan_document(
                device_id=device_id,
                dpi=serializer.validated_data["dpi"],
                color_mode=serializer.validated_data["color_mode"],
                paper_size=serializer.validated_data["paper_size"],
            )
        except RuntimeError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Return base64-encoded image
        image_b64 = base64.b64encode(image_data).decode()
        return Response({
            "image_base64": image_b64,
            "format": "png",
            "size": len(image_data),
        })

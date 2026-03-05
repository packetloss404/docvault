"""URL configuration for the security module."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"users", views.UserViewSet, basename="user")
router.register(r"groups", views.GroupViewSet, basename="group")
router.register(r"roles", views.RoleViewSet, basename="role")

urlpatterns = [
    # Auth endpoints
    path("auth/login/", views.LoginView.as_view(), name="auth-login"),
    path("auth/logout/", views.LogoutView.as_view(), name="auth-logout"),
    path("auth/register/", views.RegisterView.as_view(), name="auth-register"),
    path("auth/profile/", views.ProfileView.as_view(), name="auth-profile"),
    path("auth/change-password/", views.ChangePasswordView.as_view(), name="auth-change-password"),
    path("auth/token/", views.GenerateTokenView.as_view(), name="auth-token"),
    # OTP endpoints
    path("auth/otp/setup/", views.OTPSetupView.as_view(), name="otp-setup"),
    path("auth/otp/confirm/", views.OTPConfirmView.as_view(), name="otp-confirm"),
    path("auth/otp/disable/", views.OTPDisableView.as_view(), name="otp-disable"),
    path("auth/otp/verify/", views.OTPVerifyView.as_view(), name="otp-verify"),
    path("auth/otp/status/", views.OTPStatusView.as_view(), name="otp-status"),
    # Document signing
    path("documents/<int:document_id>/sign/", views.DocumentSignView.as_view(), name="document-sign"),
    path("documents/<int:document_id>/signatures/", views.DocumentSignatureListView.as_view(), name="document-signatures"),
    path("documents/<int:document_id>/verify/", views.DocumentVerifyView.as_view(), name="document-verify"),
    # GPG key management
    path("gpg-keys/", views.GPGKeyListView.as_view(), name="gpg-key-list"),
    path("gpg-keys/import/", views.GPGKeyImportView.as_view(), name="gpg-key-import"),
    path("gpg-keys/<str:fingerprint>/", views.GPGKeyDeleteView.as_view(), name="gpg-key-delete"),
    # Audit log
    path("audit-log/", views.AuditLogListView.as_view(), name="audit-log-list"),
    path("audit-log/export/", views.AuditLogExportView.as_view(), name="audit-log-export"),
    # Scanner
    path("sources/scanners/", views.ScannerListView.as_view(), name="scanner-list"),
    path("sources/scanners/<str:device_id>/scan/", views.ScannerScanView.as_view(), name="scanner-scan"),
    # Permission listing
    path("permissions/", views.PermissionListView.as_view(), name="permission-list"),
    # Management ViewSets
    path("", include(router.urls)),
]

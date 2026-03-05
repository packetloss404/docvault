# Sprint 17: Security Hardening & Enterprise Features

## Phase: 6 - Collaboration & Polish
## Duration: 2 weeks
## Prerequisites: Sprint 16 (Collaboration Features)

---

## Sprint Goal
Implement enterprise security features: AES-256 storage encryption, document signing (GPG), OpenID Connect authentication, two-factor OTP, scanner source (SANE), audit log viewer, and security hardening.

---

## Context for Agents

### Read Before Starting
- `/doc/product-spec.md` - Section 2.6 (Security Module)
- `/doc/architecture.md` - Section 5 (Security Architecture)
- `/doc/research/mayan-edms-analysis.md` - Section 4 (Encryption, Document Signing, LDAP/OIDC/OTP)

---

## Tasks

### Task 17.1: AES-256 Storage Encryption Backend
- EncryptedStorageBackend extending StorageBackend
- AES-256-CBC encryption via PyCryptodome
- PBKDF2 key derivation with configurable iterations (default: 100,000)
- Random IV per file (stored as file prefix)
- Chunked encryption/decryption for memory efficiency
- Configuration: `STORAGE_ENCRYPTION_ENABLED`, `STORAGE_ENCRYPTION_KEY`
- Transparent to rest of application (encrypt on save, decrypt on read)
- Migration path: encrypt existing unencrypted files (management command)

### Task 17.2: Document Signing (GPG/PGP)
- GPG integration via python-gnupg
- Sign documents with server key or user key
- Verify document signatures
- Signature model: document (FK), signer (FK), signature_data, algorithm, verified, timestamp
- API:
  - POST `/api/v1/documents/{id}/sign/`
  - GET `/api/v1/documents/{id}/signatures/`
  - POST `/api/v1/documents/{id}/verify/`
- GPG key management: import, list, delete keys

### Task 17.3: OpenID Connect Authentication
- mozilla-django-oidc integration
- Configuration via environment variables:
  - `OIDC_ENABLED`, `OIDC_RP_CLIENT_ID`, `OIDC_RP_CLIENT_SECRET`
  - `OIDC_OP_AUTHORIZATION_ENDPOINT`, `OIDC_OP_TOKEN_ENDPOINT`, `OIDC_OP_USER_ENDPOINT`
- Auto-create users on first OIDC login
- Group mapping from OIDC claims
- Frontend: "Login with SSO" button on login page

### Task 17.4: Two-Factor OTP Authentication
- pyotp integration (TOTP/HOTP)
- OTPDevice model: user (FK), secret, confirmed, created_at
- Setup flow: generate secret -> display QR code -> verify first code -> confirm
- Login flow: username/password -> OTP verification (if enabled)
- Backup codes generation and storage
- API:
  - POST `/api/v1/auth/otp/setup/` (generate secret, return QR code)
  - POST `/api/v1/auth/otp/confirm/` (verify and activate)
  - POST `/api/v1/auth/otp/disable/` (deactivate, requires password)
  - POST `/api/v1/auth/otp/verify/` (verify OTP during login)
- Frontend: OTP setup page with QR code display

### Task 17.5: Scanner Source (SANE)
- SANE scanner source backend (source_sane)
- Device discovery and listing
- Scan configuration: DPI, color mode, paper size
- Direct scan-to-document pipeline
- Web-based scan interface (trigger scan from browser)
- API:
  - GET `/api/v1/sources/scanners/` (list available scanners)
  - POST `/api/v1/sources/scanners/{id}/scan/` (trigger scan)

### Task 17.6: Audit Log Viewer & Security Hardening
- Audit log API: GET `/api/v1/audit_log/` (admin only, paginated, filterable)
- Filters: user, action_type, model_type, date range
- Export: CSV/JSON download
- Frontend: audit log viewer page (admin)
- Security hardening:
  - CSRF protection on all forms
  - XSS prevention (Content-Security-Policy headers)
  - SQL injection prevention (ORM-only queries, validated)
  - Rate limiting on auth endpoints
  - Password complexity requirements (configurable)
  - Session timeout configuration
  - IP-based access control (optional whitelist/blacklist)

---

## Dependencies

### New Python Packages
```
pycryptodome>=3.23
python-gnupg>=0.5
mozilla-django-oidc>=5.0
pyotp>=2.9
qrcode>=8.0
```

---

## Definition of Done
- [ ] AES-256 encrypted storage backend works
- [ ] Encrypted files transparent to application
- [ ] Document signing with GPG works
- [ ] OpenID Connect login works
- [ ] Two-factor OTP setup and verification works
- [ ] SANE scanner integration works (if SANE available)
- [ ] Audit log viewer shows all system events
- [ ] Security headers configured
- [ ] Password policies enforced
- [ ] All features have unit tests

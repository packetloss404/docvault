"""
Base Django settings for DocVault.

All sensitive values come from environment variables.
See .env.example for required configuration.
"""

from pathlib import Path

import environ

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DJANGO_SECRET_KEY=(str, "insecure-dev-key-change-in-production"),
    DJANGO_ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    DATABASE_URL=(str, f"sqlite:///{BASE_DIR / 'db.sqlite3'}"),
    REDIS_URL=(str, "redis://localhost:6379"),
    MEDIA_ROOT=(str, str(BASE_DIR / "media")),
    STATIC_ROOT=(str, str(BASE_DIR / "staticfiles")),
    DJANGO_LOG_LEVEL=(str, "INFO"),
    CORS_ALLOWED_ORIGINS=(list, ["http://localhost:4200"]),
    LDAP_ENABLED=(bool, False),
    STORAGE_BACKEND=(str, "local"),
    S3_ENDPOINT_URL=(str, ""),
    S3_ACCESS_KEY=(str, ""),
    S3_SECRET_KEY=(str, ""),
    S3_BUCKET_NAME=(str, "docvault"),
    S3_REGION=(str, "us-east-1"),
)

# Read .env file if it exists
env_file = BASE_DIR / ".env"
if env_file.exists():
    environ.Env.read_env(str(env_file))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env("DJANGO_SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env("DJANGO_DEBUG")

ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS")

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    # Third-party
    "rest_framework",
    "rest_framework.authtoken",
    "guardian",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "channels",
    "storages",
    "mptt",
    # DocVault apps
    "core.apps.CoreConfig",
    "documents.apps.DocumentsConfig",
    "organization.apps.OrganizationConfig",
    "search.apps.SearchConfig",
    "security.apps.SecurityConfig",
    "storage.apps.StorageConfig",
    "processing.apps.ProcessingConfig",
    "workflows.apps.WorkflowsConfig",
    "sources.apps.SourcesConfig",
    "notifications.apps.NotificationsConfig",
    "ml.apps.MlConfig",
    "ai.apps.AiConfig",
    "collaboration.apps.CollaborationConfig",
    "zone_ocr.apps.ZoneOcrConfig",
    "entities.apps.EntitiesConfig",
    "relationships.apps.RelationshipsConfig",
    "portal.apps.PortalConfig",
    "esignatures.apps.EsignaturesConfig",
    "annotations.apps.AnnotationsConfig",
    "legal_hold.apps.LegalHoldConfig",
    "physical_records.apps.PhysicalRecordsConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.middleware.CurrentUserMiddleware",
    "security.middleware.SecurityHeadersMiddleware",
    "security.middleware.IPAccessControlMiddleware",
    "core.health.MetricsMiddleware",
]

ROOT_URLCONF = "docvault.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "docvault.wsgi.application"

# Database
DATABASES = {
    "default": env.db("DATABASE_URL"),
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = "static/"
STATIC_ROOT = env("STATIC_ROOT")

# Media files (user uploads)
MEDIA_URL = "media/"
MEDIA_ROOT = env("MEDIA_ROOT")

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Redis
REDIS_URL = env("REDIS_URL")

# Sites framework (required by allauth)
SITE_ID = 1

# Authentication backends
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "guardian.backends.ObjectPermissionBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

# Django REST Framework
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "core.pagination.StandardPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "20/minute",
        "user": "120/minute",
    },
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

# drf-spectacular
SPECTACULAR_SETTINGS = {
    "TITLE": "DocVault API",
    "DESCRIPTION": "The Ultimate Open-Source Document Management System API",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# django-allauth
ACCOUNT_LOGIN_METHODS = {"username", "email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "username*", "password1*", "password2*"]
ACCOUNT_EMAIL_VERIFICATION = "optional"

# django-guardian
ANONYMOUS_USER_NAME = None
GUARDIAN_RAISE_403 = True

# CORS
CORS_ALLOWED_ORIGINS = env("CORS_ALLOWED_ORIGINS")
CORS_ALLOW_CREDENTIALS = True

# Whitenoise
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# LDAP (optional, configured via env vars)
LDAP_ENABLED = env("LDAP_ENABLED")

# Celery
CELERY_BROKER_URL = env("REDIS_URL") + "/0"
CELERY_RESULT_BACKEND = env("REDIS_URL") + "/0"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 1800  # 30 minutes max
CELERY_TASK_SOFT_TIME_LIMIT = 1500  # 25 minutes soft limit
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

# Django Channels
ASGI_APPLICATION = "docvault.asgi.application"
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}

# DocVault storage
STORAGE_BACKEND = env("STORAGE_BACKEND")
STORAGE_DIR = Path(env("MEDIA_ROOT")) / "documents"

# Content-Addressable Storage
STORAGE_CONTENT_ADDRESSED = env.bool("STORAGE_CONTENT_ADDRESSED", default=False)
STORAGE_CONTENT_ADDRESSED_BACKEND = env.str("STORAGE_CONTENT_ADDRESSED_BACKEND", default="local")

# S3 settings (for S3 storage backend)
S3_ENDPOINT_URL = env("S3_ENDPOINT_URL")
S3_ACCESS_KEY = env("S3_ACCESS_KEY")
S3_SECRET_KEY = env("S3_SECRET_KEY")
S3_BUCKET_NAME = env("S3_BUCKET_NAME")
S3_REGION = env("S3_REGION")

# OCR settings
OCR_LANGUAGE = env.str("OCR_LANGUAGE", default="eng")
OCR_MODE = env.str("OCR_MODE", default="skip")  # 'skip', 'redo', 'force'
OCR_OUTPUT_TYPE = env.str("OCR_OUTPUT_TYPE", default="pdfa")
OCR_IMAGE_DPI = env.int("OCR_IMAGE_DPI", default=300)
OCR_DESKEW = env.bool("OCR_DESKEW", default=True)
OCR_ROTATE = env.bool("OCR_ROTATE", default=True)
OCR_CLEAN = env.str("OCR_CLEAN", default="clean")  # 'none', 'clean', 'finalize'

# Thumbnail settings
THUMBNAIL_WIDTH = env.int("THUMBNAIL_WIDTH", default=400)
THUMBNAIL_HEIGHT = env.int("THUMBNAIL_HEIGHT", default=560)

# Non-destructive mode (originals never modified)
NON_DESTRUCTIVE_MODE = env.bool("NON_DESTRUCTIVE_MODE", default=True)

# Pre/post-consume scripts
PRE_CONSUME_SCRIPT = env.str("PRE_CONSUME_SCRIPT", default="")
POST_CONSUME_SCRIPT = env.str("POST_CONSUME_SCRIPT", default="")
CONSUME_SCRIPT_TIMEOUT = env.int("CONSUME_SCRIPT_TIMEOUT", default=30)

# Barcode detection
BARCODE_ENABLED = env.bool("BARCODE_ENABLED", default=True)
BARCODE_SEPARATOR = env.str("BARCODE_SEPARATOR", default="PATCH T")
BARCODE_ASN_PREFIX = env.str("BARCODE_ASN_PREFIX", default="ASN")
BARCODE_DPI = env.int("BARCODE_DPI", default=300)
BARCODE_MAX_PAGES = env.int("BARCODE_MAX_PAGES", default=5)
BARCODE_UPSCALE = env.float("BARCODE_UPSCALE", default=2.0)
BARCODE_TAG_MAPPING = {}  # Dict of regex pattern -> tag name
BARCODE_RETAIN_SEPARATOR_PAGES = env.bool("BARCODE_RETAIN_SEPARATOR_PAGES", default=False)

# Elasticsearch
ELASTICSEARCH_URL = env.str("ELASTICSEARCH_URL", default="http://localhost:9200")
ELASTICSEARCH_INDEX = env.str("ELASTICSEARCH_INDEX", default="docvault")
ELASTICSEARCH_ENABLED = env.bool("ELASTICSEARCH_ENABLED", default=False)

# LLM / AI
LLM_ENABLED = env.bool("LLM_ENABLED", default=False)
LLM_PROVIDER = env.str("LLM_PROVIDER", default="disabled")  # 'openai', 'ollama', 'disabled'
LLM_MODEL = env.str("LLM_MODEL", default="gpt-4o-mini")
LLM_API_KEY = env.str("LLM_API_KEY", default="")
LLM_API_ENDPOINT = env.str("LLM_API_ENDPOINT", default="")
EMBEDDING_MODEL = env.str("EMBEDDING_MODEL", default="text-embedding-3-small")
EMBEDDING_DIM = env.int("EMBEDDING_DIM", default=1536)

# Storage Encryption
STORAGE_ENCRYPTION_ENABLED = env.bool("STORAGE_ENCRYPTION_ENABLED", default=False)
STORAGE_ENCRYPTION_KEY = env.str("STORAGE_ENCRYPTION_KEY", default="")
STORAGE_ENCRYPTION_KDF_ITERATIONS = env.int("STORAGE_ENCRYPTION_KDF_ITERATIONS", default=100000)

# GPG / Document Signing
GPG_HOME = env.str("GPG_HOME", default="")
GPG_KEY_ID = env.str("GPG_KEY_ID", default="")

# OpenID Connect
OIDC_ENABLED = env.bool("OIDC_ENABLED", default=False)
OIDC_RP_CLIENT_ID = env.str("OIDC_RP_CLIENT_ID", default="")
OIDC_RP_CLIENT_SECRET = env.str("OIDC_RP_CLIENT_SECRET", default="")
OIDC_OP_AUTHORIZATION_ENDPOINT = env.str("OIDC_OP_AUTHORIZATION_ENDPOINT", default="")
OIDC_OP_TOKEN_ENDPOINT = env.str("OIDC_OP_TOKEN_ENDPOINT", default="")
OIDC_OP_USER_ENDPOINT = env.str("OIDC_OP_USER_ENDPOINT", default="")
OIDC_OP_JWKS_ENDPOINT = env.str("OIDC_OP_JWKS_ENDPOINT", default="")
OIDC_CREATE_USER = env.bool("OIDC_CREATE_USER", default=True)

# Two-Factor OTP
OTP_ISSUER_NAME = env.str("OTP_ISSUER_NAME", default="DocVault")

# Zone OCR
ZONE_OCR_MATCH_THRESHOLD = env.float("ZONE_OCR_MATCH_THRESHOLD", default=0.7)
ZONE_OCR_CONFIDENCE_THRESHOLD = env.float("ZONE_OCR_CONFIDENCE_THRESHOLD", default=0.8)

# Named Entity Recognition
NER_ENABLED = env.bool("NER_ENABLED", default=False)
NER_SPACY_MODEL = env.str("NER_SPACY_MODEL", default="en_core_web_sm")

# Contributor Portal
PORTAL_UPLOAD_RATE_LIMIT = env.int("PORTAL_UPLOAD_RATE_LIMIT", default=10)  # per hour per IP
PORTAL_REQUEST_REMINDER_DAYS = env.int("PORTAL_REQUEST_REMINDER_DAYS", default=3)
PORTAL_FROM_EMAIL = env.str("PORTAL_FROM_EMAIL", default="noreply@docvault.local")

# Security Hardening
SESSION_COOKIE_AGE = env.int("SESSION_COOKIE_AGE", default=3600)
SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE", default=False)
CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE", default=False)
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = "DENY"
IP_WHITELIST = env.list("IP_WHITELIST", default=[])
IP_BLACKLIST = env.list("IP_BLACKLIST", default=[])

# Sentry (optional)
SENTRY_DSN = env.str("SENTRY_DSN", default="")
if SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.django import DjangoIntegration
        from sentry_sdk.integrations.celery import CeleryIntegration

        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=[DjangoIntegration(), CeleryIntegration()],
            traces_sample_rate=env.float("SENTRY_TRACES_SAMPLE_RATE", default=0.1),
            send_default_pii=False,
        )
    except ImportError:
        pass

# Logging — structured JSON in production, readable in dev
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "django.utils.log.ServerFormatter",
            "format": '{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}',
        },
        "verbose": {
            "format": "%(asctime)s %(levelname)-8s %(name)s %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json" if not DEBUG else "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": env("DJANGO_LOG_LEVEL"),
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": env("DJANGO_LOG_LEVEL"),
            "propagate": False,
        },
        "docvault": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}

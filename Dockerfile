# =============================================================================
# DocVault Production Dockerfile — Multi-stage optimized build
# =============================================================================
# Stage 1: Angular frontend build
# Stage 2: Python backend dependencies
# Stage 3: Final production image
# =============================================================================

# ---------------------------------------------------------------------------
# Stage 1 — Angular Frontend Build
# ---------------------------------------------------------------------------
FROM node:22-alpine AS frontend

WORKDIR /build

# Install dependencies first (layer caching)
COPY src-ui/package.json src-ui/package-lock.json ./
RUN npm ci --no-audit --no-fund

# Copy source and build
COPY src-ui/ .
RUN npx ng build --configuration production

# ---------------------------------------------------------------------------
# Stage 2 — Python Backend Dependencies
# ---------------------------------------------------------------------------
FROM python:3.13-slim AS backend-deps

# Install build-time system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages into an isolated prefix
COPY requirements/base.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --prefix=/install -r /tmp/requirements.txt

# ---------------------------------------------------------------------------
# Stage 3 — Final Production Image
# ---------------------------------------------------------------------------
FROM python:3.13-slim

LABEL maintainer="DocVault <dev@docvault.io>"
LABEL org.opencontainers.image.title="DocVault"
LABEL org.opencontainers.image.description="The Ultimate Open-Source Document Management System"
LABEL org.opencontainers.image.version="1.0.0"

# Runtime system dependencies only — no compilers
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libmagic1 \
    gnupg \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-eng \
    libreoffice-nogui \
    curl \
    media-types \
    && rm -rf /var/lib/apt/lists/*

# Create non-root application user
RUN groupadd --gid 1000 docvault \
    && useradd --uid 1000 --gid 1000 --create-home --shell /bin/bash docvault

# Copy Python dependencies from builder stage
COPY --from=backend-deps /install /usr/local

WORKDIR /app

# Copy application code
COPY manage.py pyproject.toml ./
COPY deploy/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh
COPY docvault/ docvault/
COPY core/ core/
COPY documents/ documents/
COPY organization/ organization/
COPY processing/ processing/
COPY search/ search/
COPY security/ security/
COPY storage/ storage/
COPY workflows/ workflows/
COPY sources/ sources/
COPY notifications/ notifications/
COPY ml/ ml/
COPY ai/ ai/
COPY collaboration/ collaboration/
COPY annotations/ annotations/
COPY entities/ entities/
COPY esignatures/ esignatures/
COPY legal_hold/ legal_hold/
COPY physical_records/ physical_records/
COPY portal/ portal/
COPY relationships/ relationships/
COPY zone_ocr/ zone_ocr/

# Copy Angular frontend build output into static files directory
# Angular 21 with application builder outputs to dist/<project>/browser/
COPY --from=frontend /build/dist/src-ui/browser/ /app/staticfiles/frontend/

# Create volume mount points with correct ownership
RUN mkdir -p /data/media /data/consume /data/export /app/staticfiles \
    && chown -R docvault:docvault /app /data

# Set environment for production
ENV DJANGO_SETTINGS_MODULE=docvault.settings.production \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    MEDIA_ROOT=/data/media \
    STATIC_ROOT=/app/staticfiles

# Collect static files (Django admin, DRF, etc.)
RUN DJANGO_SECRET_KEY=build-time-secret-for-static-collection-only \
    DATABASE_URL=sqlite:////tmp/db.sqlite3 \
    python manage.py collectstatic --noinput

# Fix final ownership after collectstatic
RUN chown -R docvault:docvault /app/staticfiles

# NOTE: no VOLUME instruction here on purpose.
#
# Railway rejects the whole Dockerfile at validation time if it sees one
# ("dockerfile invalid: docker VOLUME ... is not supported, use Railway
# Volumes") — the build fails before a single step runs. VOLUME is only a hint
# anyway: it declares mount points and creates anonymous volumes, but every
# platform that matters mounts these paths explicitly.
#
# The directories are still created and owned by the app user above. Mount
# persistent storage at them as needed:
#   docker run  -v docvault-media:/data/media ...
#   compose     volumes: in docker-compose.yml
#   Railway     a Railway Volume, or better, object storage via STORAGE_BACKEND
#               (a Railway volume attaches to one service, but web and worker
#               both need the documents — see docs/storage-backends.md)

# Health check against the /health/ endpoint. Shell form so ${PORT} is expanded
# at runtime by the container's shell — the app binds $PORT, not always 8000.
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f "http://localhost:${PORT:-8000}/health/" || exit 1

EXPOSE 8000

# Drop to non-root user
USER docvault

# The entrypoint migrates and then runs ASGI (HTTP + WebSockets) on $PORT.
# Override the command to run the other services off this same image:
#   worker  -> celery worker      beat -> celery beat scheduler
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["web"]

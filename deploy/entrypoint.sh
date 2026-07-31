#!/bin/sh
# =============================================================================
# DocVault container entrypoint
# =============================================================================
# One image runs several services. Pick which one with the first argument or
# the DOCVAULT_ROLE env var (argument wins):
#
#   web     migrate, then serve HTTP + WebSockets with daphne on $PORT (default)
#   worker  Celery worker
#   beat    Celery beat scheduler
#
# Anything else is exec'd verbatim, so `docker run <image> python manage.py shell`
# still works.
# =============================================================================
set -eu

# DOCVAULT_ROLE wins over the argument. The Dockerfile's CMD is ["web"], so an
# argument is ALWAYS present; if the argument took precedence, setting
# DOCVAULT_ROLE=worker would be silently ignored and every service would start
# the web server. Platforms that set env vars but not the command (Railway among
# them) need the env var to be authoritative.
# With DOCVAULT_ROLE unset, the argument still works, so
# `docker run <image> python manage.py shell` behaves as expected.
ROLE="${DOCVAULT_ROLE:-${1:-web}}"
[ "$#" -gt 0 ] && shift || true

run_migrations() {
    # Only the web role migrates: workers and beat start from the same image and
    # would otherwise race each other on deploy.
    if [ "${DOCVAULT_SKIP_MIGRATIONS:-0}" = "1" ]; then
        echo "entrypoint: DOCVAULT_SKIP_MIGRATIONS=1, skipping migrations"
        return 0
    fi
    echo "entrypoint: applying database migrations"
    python manage.py migrate --noinput
}

case "$ROLE" in
    web)
        run_migrations
        echo "entrypoint: starting daphne on 0.0.0.0:${PORT:-8000}"
        exec daphne -b 0.0.0.0 -p "${PORT:-8000}" docvault.asgi:application
        ;;
    worker)
        echo "entrypoint: starting celery worker"
        exec celery -A docvault worker \
            --loglevel="${CELERY_LOG_LEVEL:-info}" \
            -Q "${CELERY_QUEUES:-default,processing}" \
            --concurrency="${CELERY_CONCURRENCY:-2}" "$@"
        ;;
    beat)
        echo "entrypoint: starting celery beat"
        exec celery -A docvault beat \
            --loglevel="${CELERY_LOG_LEVEL:-info}" \
            --schedule="${CELERY_BEAT_SCHEDULE_FILE:-/tmp/celerybeat-schedule}" "$@"
        ;;
    *)
        exec "$ROLE" "$@"
        ;;
esac

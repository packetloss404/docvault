#!/usr/bin/env bash
# =============================================================================
# DocVault — idempotent Railway deployment
# =============================================================================
# Safe to re-run: every step checks for the resource before creating it, so a
# failed deploy can be fixed and the script run again without duplicating
# services or clobbering variables that are already correct.
#
#   ./deploy/railway-deploy.sh provision   # project, Postgres, Redis, variables
#   ./deploy/railway-deploy.sh deploy      # push the current tree, all services
#   ./deploy/railway-deploy.sh status      # what exists and whether it is healthy
#   ./deploy/railway-deploy.sh logs [svc]  # recent logs for a service
#   ./deploy/railway-deploy.sh all         # provision + deploy + status
#
# Requires: railway CLI, logged in (`railway whoami`).
# =============================================================================
set -uo pipefail

PROJECT_NAME="${RAILWAY_PROJECT_NAME:-docvault}"
WEB_SERVICE="${WEB_SERVICE:-web}"
WORKER_SERVICE="${WORKER_SERVICE:-worker}"
BEAT_SERVICE="${BEAT_SERVICE:-beat}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$REPO_ROOT"

log()  { printf '\n\033[1m==> %s\033[0m\n' "$*"; }
warn() { printf '\033[33m[warn]\033[0m %s\n' "$*"; }
die()  { printf '\033[31m[fail]\033[0m %s\n' "$*" >&2; exit 1; }

require_cli() {
  command -v railway >/dev/null 2>&1 || die "railway CLI not found"
  railway whoami >/dev/null 2>&1 || die "not logged in — run: railway login"
}

# --- project ---------------------------------------------------------------

is_linked() { railway status >/dev/null 2>&1; }

ensure_project() {
  if is_linked; then
    log "Already linked to a Railway project"
    railway status 2>/dev/null | head -5
    return
  fi
  log "Linking or creating project '$PROJECT_NAME'"
  # `link` fails when the project does not exist yet; then create it.
  railway link --project "$PROJECT_NAME" >/dev/null 2>&1 \
    || railway init --name "$PROJECT_NAME" \
    || die "could not link or create project '$PROJECT_NAME'"
}

# --- managed dependencies --------------------------------------------------

has_service() {
  railway status --json 2>/dev/null | grep -qi "\"name\"[[:space:]]*:[[:space:]]*\"$1\""
}

ensure_addon() {
  local name="$1" image="$2"
  if has_service "$name"; then
    log "$name already provisioned"
    return
  fi
  log "Provisioning $name"
  railway add --database "$image" >/dev/null 2>&1 \
    || warn "could not add $name automatically — add it in the Railway dashboard"
}

# --- variables -------------------------------------------------------------
# Postgres and Redis are referenced with Railway's variable interpolation so the
# app always follows the managed instance, even if its credentials rotate.

set_var() {
  local service="$1" key="$2" value="$3"
  railway variables --service "$service" --set "$key=$value" --skip-deploys >/dev/null 2>&1 \
    || warn "could not set $key on $service"
}

secret_key() {
  python3 -c 'import secrets;print(secrets.token_urlsafe(64))' 2>/dev/null \
    || head -c 64 /dev/urandom | base64 | tr -d '\n/+='
}

configure_service() {
  local service="$1" role="$2"

  set_var "$service" DJANGO_SETTINGS_MODULE docvault.settings.production
  set_var "$service" DATABASE_URL '${{Postgres.DATABASE_URL}}'
  set_var "$service" REDIS_URL '${{Redis.REDIS_URL}}'
  set_var "$service" DJANGO_SECRET_KEY "$DJANGO_SECRET_KEY"
  # deploy/entrypoint.sh selects the process from this; one image, three roles.
  set_var "$service" DOCVAULT_ROLE "$role"
  # Only the web service migrates, so worker and beat cannot race it on deploy.
  [ "$role" = "web" ] || set_var "$service" DOCVAULT_SKIP_MIGRATIONS 1

  if [ "$role" = "web" ]; then
    # RAILWAY_PUBLIC_DOMAIN is injected once a domain exists; Django needs it in
    # ALLOWED_HOSTS, and CSRF needs it with a scheme. healthcheck.railway.app is
    # the Host header Railway's own probe sends — without it every health check
    # gets a 400 DisallowedHost and the deploy never goes live.
    set_var "$service" DJANGO_ALLOWED_HOSTS '${{RAILWAY_PUBLIC_DOMAIN}},healthcheck.railway.app'
    set_var "$service" CSRF_TRUSTED_ORIGINS 'https://${{RAILWAY_PUBLIC_DOMAIN}}'
  fi
}

ensure_variables() {
  log "Configuring environment variables"
  DJANGO_SECRET_KEY="${DJANGO_SECRET_KEY:-$(secret_key)}"
  configure_service "$WEB_SERVICE" web
  configure_service "$WORKER_SERVICE" worker
  configure_service "$BEAT_SERVICE" beat
  cat <<'NOTE'

Object storage is NOT configured by this script. Railway volumes attach to a
single service, but web and worker both need the documents, so local disk is
not viable across services. Set these on every service (B2 shown):

  STORAGE_BACKEND=b2
  S3_BUCKET_NAME=<bucket>
  S3_ENDPOINT_URL=https://s3.<region>.backblazeb2.com
  S3_REGION=<region>            e.g. us-west-004
  S3_ACCESS_KEY=<keyID>
  S3_SECRET_KEY=<applicationKey>

or configure it in the admin UI at /admin/storage once the app is up.
NOTE
}

# --- deploy ----------------------------------------------------------------

# `railway up` tars the working directory and uploads it. Doing that from a
# Windows drive mounted into WSL (/mnt/...) produced corrupted file contents —
# NUL bytes inside source files — which surfaced only as a baffling Angular
# build error on the remote builder:
#     TS1127: Invalid character  /  Unexpected "\x00" in JSON
# The local build was fine, so the corruption was introduced in transit.
# Exporting a clean `git archive` onto the Linux filesystem first avoids it, and
# has the side benefit of deploying exactly HEAD rather than the dirty tree.
STAGE_DIR=""

stage_tree() {
  [ -n "$STAGE_DIR" ] && return 0
  STAGE_DIR="$(mktemp -d "${TMPDIR:-/tmp}/docvault-deploy.XXXXXX")"
  log "Staging HEAD at $STAGE_DIR (avoids upload corruption from drive mounts)"
  git archive HEAD | tar -x -C "$STAGE_DIR" || die "could not export HEAD"
  [ -f .railwayignore ] && cp .railwayignore "$STAGE_DIR/"
  trap 'rm -rf "$STAGE_DIR"' EXIT
}

deploy_service() {
  local service="$1"
  stage_tree
  log "Deploying $service"
  ( cd "$STAGE_DIR" \
      && railway link --project "$PROJECT_NAME" --service "$service" \
           --environment "${RAILWAY_ENVIRONMENT_NAME:-production}" >/dev/null 2>&1
    cd "$STAGE_DIR" && railway up --service "$service" --ci 2>&1 | tail -25 )
  local rc=$?
  [ "$rc" -eq 0 ] || warn "deploy of $service exited $rc"
  return "$rc"
}

# --- status ----------------------------------------------------------------

public_url() {
  railway domain --service "$WEB_SERVICE" --json 2>/dev/null \
    | grep -oE 'https?://[^"]+' | head -1
}

check_health() {
  local url; url="$(public_url)"
  [ -n "$url" ] || { warn "no public domain yet"; return 1; }
  log "Health check: ${url}/health/"
  local code
  code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 20 "${url}/health/" || echo 000)"
  echo "HTTP $code"
  [ "$code" = "200" ]
}

cmd_status() {
  railway status 2>&1 | head -20
  echo
  check_health && echo "HEALTHY" || echo "NOT HEALTHY"
}

# --- entry -----------------------------------------------------------------

require_cli
case "${1:-all}" in
  provision)
    ensure_project
    ensure_addon Postgres postgres
    ensure_addon Redis redis
    ensure_variables
    ;;
  deploy)
    ensure_project
    deploy_service "$WEB_SERVICE"
    deploy_service "$WORKER_SERVICE"
    deploy_service "$BEAT_SERVICE"
    ;;
  # Read-only commands must never provision as a side effect.
  status)  is_linked || die "not linked — run: $0 provision"; cmd_status ;;
  logs)    is_linked || die "not linked — run: $0 provision"
           railway logs --service "${2:-$WEB_SERVICE}" 2>&1 | tail -60 ;;
  all)
    ensure_project
    ensure_addon Postgres postgres
    ensure_addon Redis redis
    ensure_variables
    deploy_service "$WEB_SERVICE"
    cmd_status
    ;;
  *) die "unknown command: $1" ;;
esac

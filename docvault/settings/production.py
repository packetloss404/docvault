"""Production settings for DocVault."""

from .base import *  # noqa: F401, F403
from .validators import validate_secret_key_for_production

DEBUG = False

validate_secret_key_for_production(SECRET_KEY)  # noqa: F405

# Security
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)  # noqa: F405

# DO NOT REMOVE: platforms that terminate TLS at the edge (Railway, Heroku,
# Fly.io, any ALB/ingress) forward plain HTTP to the app and record the original
# scheme in X-Forwarded-Proto. Without this, request.is_secure() is always False,
# so SECURE_SSL_REDIRECT above 301-redirects every already-HTTPS request back to
# HTTPS — an infinite redirect loop. Only safe because the app is never reached
# except through that proxy; if you expose the container directly, drop this AND
# the proxy in front of it, not just this line.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Origins allowed to POST with a CSRF token (scheme required). Needed for the
# Django admin login and any browser POST over HTTPS behind the proxy above, e.g.
# CSRF_TRUSTED_ORIGINS=https://docvault.up.railway.app,https://docs.example.com
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])  # noqa: F405

# ALLOWED_HOSTS comes from DJANGO_ALLOWED_HOSTS (see settings/base.py) and must
# list the deployed domain — on Railway that is the service's generated
# *.up.railway.app host plus any custom domain, e.g.
# DJANGO_ALLOWED_HOSTS=docvault.up.railway.app,docs.example.com

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
# HSTS is deliberately tunable. A one-year max-age is right for a domain you
# control and serve only over HTTPS, but it is sticky: browsers remember it long
# after the header stops being sent, so a mistake here locks users out of a
# plain-HTTP host until the max-age expires. `preload` additionally asserts an
# intent to be added to browser preload lists, which is not yours to assert on a
# platform-provided domain such as *.up.railway.app — hence the default of off.
SECURE_HSTS_SECONDS = env.int("DJANGO_HSTS_SECONDS", default=31536000)  # noqa: F405
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool(  # noqa: F405
    "DJANGO_HSTS_INCLUDE_SUBDOMAINS", default=True
)
SECURE_HSTS_PRELOAD = env.bool("DJANGO_HSTS_PRELOAD", default=False)  # noqa: F405

if not SECURE_HSTS_PRELOAD:
    # security.W021 advises turning preload on. Leaving it off is the deliberate
    # choice explained above, not an oversight, so silence the advice rather
    # than leave a permanent warning in `check --deploy`. Set
    # DJANGO_HSTS_PRELOAD=true once serving a domain you own over HTTPS only.
    SILENCED_SYSTEM_CHECKS = [
        *globals().get("SILENCED_SYSTEM_CHECKS", []),
        "security.W021",
    ]

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [REDIS_URL],  # noqa: F405
        },
    },
}

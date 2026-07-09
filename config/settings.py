"""
Django settings for the MUST-GSL EMR project.

Stack decisions here follow AGENTS.md §2 exactly - do not add packages or
patterns not already on ALLOWED_PACKAGES.md without a sign-off entry there.
"""
import sys
from pathlib import Path
from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent

_INSECURE_DEFAULT_KEY = "dev-only-insecure-key-change-me"

SECRET_KEY = config("DJANGO_SECRET_KEY", default=_INSECURE_DEFAULT_KEY)
DEBUG = config("DEBUG", default=False, cast=bool)  # secure-by-default; local dev sets DEBUG=True via .env
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # third-party (all on ALLOWED_PACKAGES.md)
    "rest_framework",
    "drf_spectacular",
    "simple_history",
    "axes",
    # local apps
    "core",
    "accounts",
    "patients",
    "encounters",
    "vitals",
    "laboratory",
    "imaging",
    "pharmacy",
    "reporting",
    "billing",
    "syncapi",
    "interop",
    "emergency",
    "dialysis",
    "inpatient",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",
    "axes.middleware.AxesMiddleware",
    "config.middleware.PermissionDeniedMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# --- Database: PostgreSQL 16 per AGENTS.md. Never swap this for sqlite in
# committed settings - use DATABASE_URL env override for CI/local dev if
# Postgres isn't reachable, see README "Local dev without Postgres".
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME", default="must_emr"),
        "USER": config("DB_USER", default="must_emr"),
        "PASSWORD": config("DB_PASSWORD", default="must_emr"),
        "HOST": config("DB_HOST", default="localhost"),
        "PORT": config("DB_PORT", default="5432"),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Blantyre"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]  # cant believe i missed this part .. but we are past that
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "accounts:dashboard"
LOGOUT_REDIRECT_URL = "accounts:login"

# --- Security baseline, AGENTS.md §7 / brief §9.4 ---
SESSION_COOKIE_AGE = config("SESSION_COOKIE_AGE", default=15 * 60, cast=int)  # 15 min idle, clinical roles
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
CSRF_COOKIE_HTTPONLY = True
# Secure flags default True (browsers only enforce "Secure" over HTTPS, so this
# is a no-op for local HTTP dev and only matters if a real deployment forgets TLS).
SESSION_COOKIE_SECURE = config("SESSION_COOKIE_SECURE", default=True, cast=bool)
CSRF_COOKIE_SECURE = config("CSRF_COOKIE_SECURE", default=True, cast=bool)
SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=False, cast=bool)  # False for local Docker fallback only
SECURE_HSTS_SECONDS = config("SECURE_HSTS_SECONDS", default=0, cast=int)

# --- django-axes: lock after 5 failed logins for 15 minutes (brief §9.4) ---
AXES_FAILURE_LIMIT = config("AXES_FAILURE_LIMIT", default=5, cast=int)  # AGENTS.md §7: 5 failed logins -> 15 min lock
AXES_COOLOFF_TIME = 0.25  # hours = 15 minutes
AXES_LOCKOUT_PARAMETERS = [["username", "ip_address"]]

# --- django-cryptography: field-level encryption key, MUST be set via env
# in any real deployment. Never commit a real key. ---
CRYPTOGRAPHY_KEY = config("CRYPTOGRAPHY_KEY", default=SECRET_KEY)

# Refuse to boot outside DEBUG if PHI would be encrypted (or the app would
# run) with the well-known placeholder key/secret committed in this repo -
# a forgotten env var must not silently downgrade PHI encryption to
# "anyone with this source code can decrypt it".
if not DEBUG:
    if SECRET_KEY == _INSECURE_DEFAULT_KEY:
        sys.exit("DJANGO_SECRET_KEY must be set to a real secret in production.")
    if CRYPTOGRAPHY_KEY in (_INSECURE_DEFAULT_KEY, SECRET_KEY) and not config("CRYPTOGRAPHY_KEY", default=""):
        sys.exit("CRYPTOGRAPHY_KEY must be explicitly set in production - refusing to encrypt PHI with a default key.")

# --- Email: console backend for demo (password reset) ---
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# --- DRF / drf-spectacular: used ONLY for offline-sync, FHIR-lite export,
# dashboard JSON per AGENTS.md §2 - not a parallel API for the whole app. ---
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}
SPECTACULAR_SETTINGS = {
    "TITLE": "MUST-GSL EMR API",
    "DESCRIPTION": "Offline-sync, FHIR-lite interop, and dashboard JSON endpoints only.",
    "VERSION": "0.1.0",
}

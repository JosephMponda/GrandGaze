"""Test-only settings: SQLite in-memory by default, PostgreSQL via DATABASE_URL."""
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

SECRET_KEY = "test-secret-key-not-for-production"
DEBUG = True

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "axes",
    "core",
    "simple_history",
    "django_filters",
    "django_otp",
    "django_otp.plugins.otp_totp",
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
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "axes.middleware.AxesMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
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

# Use PostgreSQL if DATABASE_URL is set (CI), otherwise SQLite in-memory (local)
_database_url = os.environ.get("DATABASE_URL")
if _database_url:
    import re
    _m = re.match(r"postgres://(\w+):(\w+)@([\w.]+):(\d+)/(\w+)", _database_url)
    if _m:
        DATABASES = {
            "default": {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": _m.group(5),
                "USER": _m.group(1),
                "PASSWORD": _m.group(2),
                "HOST": _m.group(3),
                "PORT": _m.group(4),
            }
        }
    else:
        raise ValueError(f"Unsupported DATABASE_URL format: {_database_url}")
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    }

AUTH_PASSWORD_VALIDATORS = []
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
STATIC_URL = "/static/"
STATICFILES_DIRS = [os.path.join(BASE_DIR, "static")]
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "accounts:dashboard"

# Session - 15 min idle timeout
SESSION_COOKIE_AGE = 900
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# django-axes
AXES_ENABLED = False  # disable in tests to not interfere
AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
]

# DRF
REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

# Encrypted fields
ENCRYPTION_KEY = "dGhpcyBpcyBhIHRlc3Qga2V5IGZvciBlbmNyeXB0aW9uID0="

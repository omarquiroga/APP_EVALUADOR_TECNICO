import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "test-secret-key-not-for-production")
DEBUG = False
USE_TZ = True
TIME_ZONE = os.getenv("DJANGO_TIME_ZONE", "America/Bogota")
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

ROOT_URLCONF = "urls_test"

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "procurement",
    "normative",
    "rules",
    "bidders",
    "documents",
    "rup",
    "experience",
    "finance",
    "external_checks",
    "evaluation",
    "causals",
    "consolidation",
    "audit",
    "review",
]

MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB", "evaluador_test"),
        "USER": os.getenv("POSTGRES_USER", "postgres"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", "postgres"),
        "HOST": os.getenv("POSTGRES_HOST", "localhost"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
        "TEST": {
            "NAME": os.getenv("POSTGRES_TEST_DB", "test_evaluador_test"),
        },
        "CONN_MAX_AGE": 0,
        "ATOMIC_REQUESTS": False,
    }
}

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = "es-co"

MEDIA_ROOT = BASE_DIR / "_test_media"
MEDIA_URL = "/media/"
LOGIN_URL = "/admin/login/"

MIGRATION_MODULES = {}

LOGGING_CONFIG = None

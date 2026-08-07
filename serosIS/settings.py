from pathlib import Path
from dotenv import load_dotenv
import os
import sys

load_dotenv()

# pymysql must be patched before Django loads the MySQL backend
try:
    import pymysql
    pymysql.install_as_MySQLdb()
except ImportError:
    pass

from chatbot.db.config import get_django_db_config, get_chat_db_config  # noqa: E402

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-secret-key-change-in-production")
DEBUG = os.getenv("DEBUG", "True") == "True"
TESTING = "test" in sys.argv or "PYTEST_VERSION" in os.environ
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "chatbot",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "serosIS.middleware.LoginRequiredMiddleware",
]

AUTHENTICATION_BACKENDS = [
    "chatbot.auth_backend.SerosAuthBackend",
]

ROOT_URLCONF = "serosIS.urls"

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
                "chatbot.context_processors.seros_nav",
            ],
        },
    },
]

WSGI_APPLICATION = "serosIS.wsgi.application"

DATABASES = {
    "default":     get_django_db_config(),   # operational data (read-only in phase 1)
    "chathistory": get_chat_db_config(),      # chat conversations & messages
}

DATABASE_ROUTERS = ["serosIS.db_router.ChatHistoryRouter"]

LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/login/"

STATIC_URL = "/static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

INTERNAL_IPS = ["127.0.0.1"]

if DEBUG and not TESTING:
    INSTALLED_APPS += ["debug_toolbar"]
    MIDDLEWARE.insert(1, "debug_toolbar.middleware.DebugToolbarMiddleware")

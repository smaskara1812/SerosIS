from pathlib import Path
from dotenv import load_dotenv
import os

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
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "chatbot",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
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

STATIC_URL = "/static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

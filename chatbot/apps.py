from django.apps import AppConfig


class ChatbotConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "chatbot"

    def ready(self):
        # Register audit signal receivers (login / logout / failed login).
        from . import signals  # noqa: F401

"""Audit hooks for Django's auth signals — login / logout / failed login.
Registered from ChatbotConfig.ready()."""
from django.contrib.auth.signals import (
    user_logged_in, user_logged_out, user_login_failed,
)
from django.dispatch import receiver

from . import audit


@receiver(user_logged_in)
def _on_login(sender, request, user, **kwargs):
    audit.log_auth("login", user.get_username(), request)


@receiver(user_logged_out)
def _on_logout(sender, request, user, **kwargs):
    audit.log_auth("logout", user.get_username() if user else "", request)


@receiver(user_login_failed)
def _on_login_failed(sender, credentials, request=None, **kwargs):
    # Never log the password — only the attempted username.
    username = (credentials or {}).get("username", "") or ""
    audit.log_auth("login_failed", username, request)

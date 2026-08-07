from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class SerosAuthBackend(ModelBackend):
    """
    Authentication backend with a stable verify_credentials() contract.

    Swap-point for AD integration: when the company Active Directory API is
    ready, replace verify_credentials() with a call to that API.  The login
    view, session handling, and role forwarding all stay unchanged.

    Contract:
        verify_credentials(username, password) → {
            "is_success": bool,
            "user":       User | None,
            "roles":      list[str],   # group names; empty until RBAC is wired
        }
    """

    def verify_credentials(self, username: str, password: str) -> dict:
        """
        Phase 1 — local DB check.

        Replace this body with an AD API call in phase 2:
            response = requests.post(AD_URL, json={"username": username, "password": password})
            data = response.json()          # expects {"isSuccess": bool, "roles": [...]}
            if not data["isSuccess"]:
                return {"is_success": False, "user": None, "roles": []}
            user, _ = User.objects.using("chathistory").get_or_create(username=username)
            return {"is_success": True, "user": user, "roles": data.get("roles", [])}
        """
        User = get_user_model()
        try:
            user = User.objects.using("chathistory").get(username=username)
        except User.DoesNotExist:
            return {"is_success": False, "user": None, "roles": []}

        if not user.check_password(password) or not user.is_active:
            return {"is_success": False, "user": None, "roles": []}

        roles = list(user.groups.values_list("name", flat=True))
        return {"is_success": True, "user": user, "roles": roles}

    # ── Django auth hooks ────────────────────────────────────────────────────

    def authenticate(self, request, username=None, password=None, **kwargs):
        result = self.verify_credentials(username or "", password or "")
        if result["is_success"]:
            result["user"]._seros_roles = result["roles"]
            return result["user"]
        return None

    def get_user(self, user_id):
        User = get_user_model()
        try:
            return User.objects.using("chathistory").get(pk=user_id)
        except User.DoesNotExist:
            return None

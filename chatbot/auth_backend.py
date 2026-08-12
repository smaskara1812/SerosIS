import base64
import hashlib
import logging

import requests
from django.contrib.auth import get_user_model
from django.db import connections, OperationalError

logger = logging.getLogger(__name__)

AD_AUTH_URL = "https://mobileservices.essar.com/prod/web/ldap/api/AuthAPI/IsAccountAuthorized/"
AD_TIMEOUT  = 10  # seconds


# ── Mst_user lookup ───────────────────────────────────────────────────────────

def _fetch_mst_users(login_id: str):
    """
    Returns (active_row, inactive_row) for a given login_id.
    Uses fetchall() to handle the rare case of duplicate login_ids in Mst_user.
    """
    try:
        with connections["default"].cursor() as cursor:
            cursor.execute(
                "SELECT USER_ID, USER_LOGIN_ID, USER_NAME, USER_EMAIL, USER_ACTIVE "
                "FROM Mst_user WHERE UPPER(USER_LOGIN_ID) = UPPER(%s)",
                [login_id],
            )
            rows = cursor.fetchall()
    except OperationalError:
        return None, None

    active_row = inactive_row = None
    for row in rows:
        d = {
            "user_id":  row[0],
            "login_id": row[1],
            "name":     row[2] or "",
            "email":    row[3] or "",
        }
        if row[4] == "Y":
            active_row = d
        else:
            inactive_row = d

    return active_row, inactive_row


# ── Local password check (cb_mst_user_password) ───────────────────────────────

def _sha256(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def _check_local_password(user_id: int, password: str) -> bool | None:
    """
    Returns True  — local password exists and matches
            False — local password exists but does NOT match
            None  — no local password row found (caller should try AD)
    """
    try:
        from .models import CbMstUserPassword
        row = CbMstUserPassword.objects.using("chathistory").filter(user_id=user_id).first()
    except Exception:
        return None

    if row is None:
        return None

    return row.password_hash == _sha256(password)


# ── AD authentication ─────────────────────────────────────────────────────────

def _authenticate_ad(login_id: str, password: str) -> bool:
    """
    Calls the Essar AD REST API.
    Returns True if isSuccess, False otherwise (including network errors).
    """
    try:
        headers = {
            "UserID":   base64.b64encode(login_id.encode()).decode(),
            "Password": base64.b64encode(password.encode()).decode(),
        }
        resp = requests.get(AD_AUTH_URL, headers=headers, timeout=AD_TIMEOUT)
        if resp.status_code == 200:
            return bool(resp.json().get("isSuccess", False))
    except Exception as exc:
        logger.warning("AD auth request failed for %s: %s", login_id, exc)
    return False


# ── Main backend ──────────────────────────────────────────────────────────────

class SerosAuthBackend:
    """
    Authentication order for an active Mst_user:
      1. cb_mst_user_password row exists → SHA-256 compare → allow or reject
      2. No local password row           → AD REST API     → allow or reject

    Inactive users surface Django's built-in 'inactive' error.
    Users not in Mst_user fall through to ModelBackend (superusers).
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None

        active, inactive = _fetch_mst_users(username)

        if active is not None:
            mst = active
            is_active = True
        elif inactive is not None:
            # Surface "This account is inactive" via Django's form validation.
            mst = inactive
            is_active = False
        else:
            return None  # not in Mst_user → try ModelBackend

        if is_active:
            local = _check_local_password(mst["user_id"], password)
            if local is True:
                pass  # authenticated locally
            elif local is False:
                return None  # wrong password
            else:
                # No local password → try AD
                if not _authenticate_ad(mst["login_id"], password):
                    return None

        User = get_user_model()
        display = mst["name"][:30]
        user, created = User.objects.using("chathistory").get_or_create(
            username=mst["login_id"],
            defaults={
                "first_name": display,
                "email":      mst["email"],
                "is_active":  is_active,
            },
        )
        if not created:
            changed = False
            for attr, val in [("first_name", display), ("email", mst["email"]), ("is_active", is_active)]:
                if getattr(user, attr) != val:
                    setattr(user, attr, val)
                    changed = True
            if changed:
                user.save(using="chathistory")

        if is_active and mst.get("user_id"):
            from .models import UserProfile
            UserProfile.objects.using("chathistory").update_or_create(
                user_id=mst["user_id"],
                defaults={"user_login_id": mst["login_id"]},
            )

        return user

    def get_user(self, user_id):
        User = get_user_model()
        try:
            return User.objects.using("chathistory").get(pk=user_id)
        except User.DoesNotExist:
            return None

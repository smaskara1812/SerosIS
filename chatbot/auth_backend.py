from django.contrib.auth import get_user_model
from django.db import connections, OperationalError

DEFAULT_PASSWORD = "seros2026"


def _fetch_mst_users(login_id: str):
    """
    Returns (active_row, inactive_row) for a given login_id.
    When the same login_id has both an active and an inactive USER_ID,
    active_row takes priority.
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


class SerosAuthBackend:
    """
    Auth backend that validates against Mst_user + hardcoded default password.

    Lookup order:
      1. Active Mst_user row   → allow login (if password correct)
      2. Inactive Mst_user row → return Django user with is_active=False
                                  (Django shows "This account is inactive")
      3. Not in Mst_user at all → return None (ModelBackend handles superusers)
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username:
            return None

        active, inactive = _fetch_mst_users(username)

        if active is not None:
            # Active Mst_user found — check password
            if password != DEFAULT_PASSWORD:
                return None
            mst = active
            is_active = True

        elif inactive is not None:
            # Only an inactive row exists — surface "account inactive" error.
            # Return the Django user with is_active=False so AuthenticationForm
            # raises its built-in 'inactive' validation error.
            mst = inactive
            is_active = False

        else:
            # Not in Mst_user at all → fall through to ModelBackend
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
            if user.first_name != display:
                user.first_name = display
                changed = True
            if user.email != mst["email"]:
                user.email = mst["email"]
                changed = True
            if user.is_active != is_active:
                user.is_active = is_active
                changed = True
            if changed:
                user.save(using="chathistory")

        return user

    def get_user(self, user_id):
        User = get_user_model()
        try:
            return User.objects.using("chathistory").get(pk=user_id)
        except User.DoesNotExist:
            return None

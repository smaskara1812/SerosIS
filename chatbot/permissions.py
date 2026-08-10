
def get_menu_registry():
    """
    Load active menu definitions from cb_menu (ordered by menu_order).
    Returns an OrderedDict keyed by menu_key with the same shape as the
    old MENU_REGISTRY so all callers continue to work unchanged.
    """
    from collections import OrderedDict
    from .models import CbMenu

    registry = OrderedDict()
    for m in CbMenu.objects.filter(is_active=True).order_by("group_order", "menu_order"):
        registry[m.menu_key] = {
            "label":   m.menu_label,
            "group":   m.menu_group,
            "actions": m.get_actions(),
        }
    return registry


def get_user_access(request):
    """
    Returns {"is_admin": bool, "perms": {menu_key: {action: bool, ...}}}
    for the current authenticated user. Result is cached in the session.

    is_admin=True means bypass all permission checks (see everything).
    Django superusers are also treated as app admin.
    """
    if not request.user.is_authenticated:
        return {"is_admin": False, "perms": {}}

    cache_key = f"_seros_access_{request.user.pk}"
    cached = request.session.get(cache_key)
    if cached is not None:
        return cached

    if request.user.is_superuser:
        result = {"is_admin": True, "perms": {}}
        request.session[cache_key] = result
        return result

    from .models import UserProfile, UserPermission
    login_id = request.user.username

    try:
        profile = UserProfile.objects.get(user_login_id=login_id)
        is_admin = profile.is_app_admin
    except UserProfile.DoesNotExist:
        is_admin = False

    perms = {}
    if not is_admin:
        for p in UserPermission.objects.filter(user_login_id=login_id):
            perms[p.menu_key] = {
                "view":   p.can_view,
                "add":    p.can_add,
                "edit":   p.can_edit,
                "delete": p.can_delete,
                "export": p.can_export,
            }

    result = {"is_admin": is_admin, "perms": perms}
    request.session[cache_key] = result
    return result


def invalidate_user_access_cache(request):
    cache_key = f"_seros_access_{request.user.pk}"
    request.session.pop(cache_key, None)


def can_view(access: dict, menu_key: str) -> bool:
    if access["is_admin"]:
        return True
    p = access["perms"].get(menu_key, {})
    return bool(p.get("view"))



def require_permission(menu_key: str, action: str = "view"):
    """Decorator that returns 403 if the authenticated user lacks the given permission."""
    from functools import wraps

    def decorator(view_fn):
        @wraps(view_fn)
        def _wrapped(request, *args, **kwargs):
            access = get_user_access(request)
            if access["is_admin"]:
                return view_fn(request, *args, **kwargs)
            p = access["perms"].get(menu_key, {})
            if not p.get(action):
                from django.shortcuts import render as _render
                return _render(
                    request,
                    "chatbot/403.html",
                    {"required_permission": menu_key, "required_action": action},
                    status=403,
                )
            return view_fn(request, *args, **kwargs)
        return _wrapped
    return decorator

import copy

# ── Icon SVGs (inline, 20×20 viewport) ────────────────────────────────────────

_ICONS = {
    "dashboard": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>',
    "chat":      '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>',
    "rigs":      '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>',
    "listings":  '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>',
    "masters":   '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></svg>',
    "manuals":   '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>',
    "health":    '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>',
    "admin":     '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>',
}

# ── Nav definition ─────────────────────────────────────────────────────────────
# Each item's "id" matches its cb_menu key exactly.
# Parent items (listings, masters) have no cb_menu key — their visibility is
# derived from whichever children are accessible.

_NAV_ITEMS = [
    {
        "id": "dashboard",
        "label": "Dashboard",
        "url": "/",
        "exact": True,
        "icon": _ICONS["dashboard"],
    },
    {
        "id": "rigs",
        "label": "Rigs 360",
        "url": "/rigs/",
        "icon": _ICONS["rigs"],
    },
    {
        "id": "listings",
        "label": "Listings",
        "url": "/listings/",
        "icon": _ICONS["listings"],
        "children": [
            {"id": "listings.incidents",      "label": "Incidents",      "url": "/listings/incidents/"},
            {"id": "listings.hazard_cards",   "label": "Hazard Cards",   "url": "/listings/hazard-cards/"},
            {"id": "listings.employees",      "label": "Employees",      "url": "/listings/employees/"},
            {"id": "listings.staff",          "label": "Staff",          "url": "/listings/staff/"},
            {"id": "listings.crew_rotations", "label": "Crew Rotations", "url": "/listings/crew-rotations/"},
            {"id": "listings.invoices",       "label": "Invoices",       "url": "/listings/invoices/"},
            {"id": "listings.certificates",   "label": "Certificates",   "url": "/listings/certificates/"},
            {"id": "listings.users",          "label": "System Users",   "url": "/listings/users/"},
        ],
    },
    {
        "id": "masters",
        "label": "Masters",
        "url": "/masters/",
        "icon": _ICONS["masters"],
        # children populated from masters_registry at runtime (see below)
        "children": [],
    },
    {
        "id": "manuals",
        "label": "Manuals",
        "url": "/manuals/",
        "icon": _ICONS["manuals"],
    },
    {
        "id": "chat",
        "label": "AI Chat",
        "url": "/chat/",
        "icon": _ICONS["chat"],
    },
    {
        "id": "health",
        "label": "Health",
        "url": "/health/",
        "icon": _ICONS["health"],
    },
]

_ADMIN_NAV_ITEM = {
    "id": "admin",
    "label": "Admin",
    "url": "/admin-panel/",
    "icon": _ICONS["admin"],
    "children": [
        {"id": "admin.user_rights",     "label": "User Rights",     "url": "/admin-panel/user-rights/"},
        {"id": "admin.user_management", "label": "User Management", "url": "/admin-panel/user-management/"},
    ],
}


def seros_nav(request):
    if not request.user.is_authenticated:
        return {}

    from .permissions import get_user_access, can_view
    from .masters_registry import all_items

    access = get_user_access(request)
    path = request.path

    base_items = copy.deepcopy(_NAV_ITEMS)
    if access["is_admin"]:
        base_items.append(copy.deepcopy(_ADMIN_NAV_ITEM))

    # Populate the Masters nav children from the registry (single source of truth).
    for it in base_items:
        if it["id"] == "masters":
            it["children"] = [
                {"id": m["key"], "label": m["label"], "url": m["url"]}
                for m in all_items()
            ]
            break

    items = []
    for item in base_items:
        if item.get("children"):
            # Parent nav item (listings / masters / admin): show only accessible children.
            # Admins see everything; for others, child id == cb_menu key.
            visible_children = [
                {**child, "is_active": path.startswith(child["url"])}
                for child in item["children"]
                if access["is_admin"] or can_view(access, child["id"])
            ]
            if not visible_children:
                continue
            item = {**item, "children": visible_children}
        else:
            # Leaf nav item: id is the cb_menu key — check directly.
            if not access["is_admin"] and not can_view(access, item["id"]):
                continue

        item["is_active"] = (path == item["url"]) if item.get("exact") else path.startswith(item["url"])
        items.append(item)

    active_section = next((i for i in items if i.get("is_active")), None)

    # Masters section — everything derived from the single registry.
    from .masters_registry import build_masters_nav
    _mv = lambda key: access["is_admin"] or can_view(access, key)
    masters_nav = build_masters_nav(_mv)

    return {
        "nav_items":      items,
        "active_section": active_section,
        "user_access":    access,
        "masters_nav":    masters_nav,
    }

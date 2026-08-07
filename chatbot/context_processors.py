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
}

# ── Nav definition ─────────────────────────────────────────────────────────────
# Each item: id, label, url, icon, exact (bool), children (list, optional)
# Children: id, label, url
# Future RBAC: add perm field to each item/child, filter by request.user's roles here.

_NAV_ITEMS = [
    {
        "id": "dashboard",
        "label": "Dashboard",
        "url": "/",
        "exact": True,
        "icon": _ICONS["dashboard"],
    },
    # {
    #     "id": "chat",
    #     "label": "AI Chat",
    #     "url": "/chat/",
    #     "icon": _ICONS["chat"],
    # },
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
            {"id": "incidents",      "label": "Incidents",      "url": "/listings/incidents/"},
            {"id": "hazard_cards",   "label": "Hazard Cards",   "url": "/listings/hazard-cards/"},
            {"id": "employees",      "label": "Employees",      "url": "/listings/employees/"},
            {"id": "staff",          "label": "Staff",          "url": "/listings/staff/"},
            {"id": "crew_rotations", "label": "Crew Rotations", "url": "/listings/crew-rotations/"},
            {"id": "invoices",       "label": "Invoices",       "url": "/listings/invoices/"},
            {"id": "certificates",   "label": "Certificates",   "url": "/listings/certificates/"},
        ],
    },
    {
        "id": "masters",
        "label": "Masters",
        "url": "/masters/",
        "icon": _ICONS["masters"],
        "children": [
            {"id": "rig_master",        "label": "Rigs",               "url": "/masters/rigs/"},
            {"id": "operator_master",   "label": "Operators",          "url": "/masters/operator/"},
            {"id": "contractor_master", "label": "Contractors",        "url": "/masters/contractor/"},
            {"id": "cost_centre",       "label": "Cost Centres",       "url": "/masters/cost-centre/"},
            {"id": "cost_centre_type",  "label": "Cost Centre Types",  "url": "/masters/cost-centre-type/"},
        ],
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


def seros_nav(request):
    if not request.user.is_authenticated:
        return {}

    path = request.path
    items = copy.deepcopy(_NAV_ITEMS)
    active_section = None

    for item in items:
        if item.get("exact"):
            item["is_active"] = (path == item["url"])
        else:
            item["is_active"] = path.startswith(item["url"])

        if item["is_active"]:
            active_section = item

        for child in item.get("children", []):
            child["is_active"] = path.startswith(child["url"])

    return {
        "nav_items": items,
        "active_section": active_section,
    }

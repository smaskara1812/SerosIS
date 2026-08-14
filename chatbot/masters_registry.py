"""
Single source of truth for the Masters section.

To add a new master, add ONE item entry to the appropriate group below (and, of
course, its view/urls.py/template + cb_menu row). Everything else — the Masters
index cards, the Masters secondary sidebar, the left dark-sidebar nav children,
the per-group counts, and the per-master view flags — is derived from this list.
Nothing about the master list should be hardcoded anywhere else.

Fields per item:
  key       cb_menu permission key (e.g. "masters.rigs")
  slug      short identifier used in template dict lookups (e.g. "rigs")
  label     display name
  url       page URL
  sub       small uppercase subtitle on the index card
  meta      table + actions line on the index card
  card_bg   card icon background colour
  icon      raw <svg> for the card icon (stroke colour baked in)
"""

# ── Card icons (16×16) ────────────────────────────────────────────────────────
_I = {
    "rigs":        '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="2"><path d="M2 20h20M4 20V8l8-4 8 4v12"/><path d="M10 20v-6h4v6"/></svg>',
    "cost_centre": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#16a34a" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="16"/><line x1="8" y1="12" x2="16" y2="12"/></svg>',
    "cc_type":     '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#d97706" stroke-width="2"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>',
    "operator":    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#9333ea" stroke-width="2"><circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/></svg>',
    "contractor":  '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#e11d48" stroke-width="2"><rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2"/></svg>',
    "cert":        '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="2"><circle cx="12" cy="8" r="6"/><path d="M15.477 12.89L17 22l-5-3-5 3 1.523-9.11"/></svg>',
    "email":       '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#16a34a" stroke-width="2"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>',
    "travel":      '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#16a34a" stroke-width="2"><path d="M17 8h2a2 2 0 0 1 2 2v6a2 2 0 0 1-2 2h-2v4l-4-4H9a2 2 0 0 1-2-2v-1"/><path d="M3 4h10a2 2 0 0 1 2 2v6a2 2 0 0 1-2 2H7l-4 4V6a2 2 0 0 1 2-2z"/></svg>',
    "reporting":   '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>',
    "jobdesc":     '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#d97706" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>',
    "competency":  '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#9333ea" stroke-width="2"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>',
}

# ── Group header icons (14×14) ─────────────────────────────────────────────────
_GI = {
    "general":  '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M12 1v4M12 19v4M4.22 4.22l2.83 2.83M16.95 16.95l2.83 2.83M1 12h4M19 12h4M4.22 19.78l2.83-2.83M16.95 7.05l2.83-2.83"/></svg>',
    "hr":       '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#16a34a" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>',
    "qhse":     '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#d97706" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>',
    "projects": '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#9333ea" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M9 21V9"/></svg>',
}

MASTER_GROUPS = [
    {
        "id": "general", "label": "General", "icon_bg": "#eff6ff", "icon": _GI["general"],
        "items": [
            {"key": "masters.rigs",                    "slug": "rigs",                     "label": "Rigs",                     "url": "/masters/rigs/",                     "sub": "RIG MASTER",                    "meta": "eos_Mst_Rig · Add / Edit",                              "card_bg": "#eff6ff", "icon": _I["rigs"]},
            {"key": "masters.cost_centres",            "slug": "cost_centres",             "label": "Cost Centres",             "url": "/masters/cost-centre/",              "sub": "COST CENTRE MASTER",            "meta": "eos_Mst_Cost_Centre · Add / Edit / Deactivate",         "card_bg": "#f0fdf4", "icon": _I["cost_centre"]},
            {"key": "masters.cost_centre_types",       "slug": "cost_centre_types",        "label": "Cost Centre Types",        "url": "/masters/cost-centre-type/",         "sub": "COST CENTRE TYPE MASTER",       "meta": "eos_Mst_Cost_Centre_Type · Add / Edit / Deactivate",    "card_bg": "#fff7ed", "icon": _I["cc_type"]},
            {"key": "masters.operators",               "slug": "operators",                "label": "Operators",                "url": "/masters/operator/",                 "sub": "OPERATOR MASTER",               "meta": "eos_Mst_Operator · Add / Edit / Deactivate",            "card_bg": "#fdf4ff", "icon": _I["operator"]},
            {"key": "masters.contractors",             "slug": "contractors",              "label": "Contractors",              "url": "/masters/contractor/",               "sub": "CONTRACTOR MASTER",             "meta": "eos_Mst_Contractor · Add / Edit / Delete",              "card_bg": "#fff1f2", "icon": _I["contractor"]},
            {"key": "masters.cert_institutes",         "slug": "cert_institutes",          "label": "Cert Institutes",          "url": "/masters/cert-institutes/",          "sub": "CERTIFICATION INSTITUTE MASTER","meta": "eos_Mst_Cert_Institute · Add / Edit / Delete",          "card_bg": "#eff6ff", "icon": _I["cert"]},
            {"key": "masters.email_notification_types","slug": "email_notification_types", "label": "Email Notification Types", "url": "/masters/email-notification-types/", "sub": "EMAIL NOTIFICATION TYPE",       "meta": "eos_Email_Notification_Type · Add / Edit / Deactivate", "card_bg": "#f0fdf4", "icon": _I["email"]},
        ],
    },
    {
        "id": "hr", "label": "HR", "icon_bg": "#f0fdf4", "icon": _GI["hr"],
        "items": [
            {"key": "masters.travel_eligibility",  "slug": "travel_eligibility",  "label": "Travel Eligibility",  "url": "/masters/travel-eligibility/",  "sub": "HR MASTER", "meta": "eos_Travel_Eligibility · Add / Edit / Delete",           "card_bg": "#f0fdf4", "icon": _I["travel"]},
            {"key": "masters.reporting_structure", "slug": "reporting_structure", "label": "Reporting Structure", "url": "/masters/reporting-structure/", "sub": "HR MASTER", "meta": "eos_Reporting_Structure · Add / Edit / Delete",          "card_bg": "#eff6ff", "icon": _I["reporting"]},
            {"key": "masters.job_descriptions",    "slug": "job_descriptions",    "label": "Job Descriptions",    "url": "/masters/job-descriptions/",    "sub": "HR MASTER", "meta": "eos_Job_Description_Hdr / Dtl · Add / Edit / Delete",    "card_bg": "#fff7ed", "icon": _I["jobdesc"]},
            {"key": "masters.competency",          "slug": "competency",          "label": "Competency",          "url": "/masters/competency/",          "sub": "HR MASTER", "meta": "eos_Mst_Competency · Add / Edit / Delete",               "card_bg": "#fdf4ff", "icon": _I["competency"]},
        ],
    },
    # Placeholder groups (no masters built yet) — kept here so the section list is
    # fully data-driven. Add items above when their masters are built.
    {"id": "qhse",     "label": "QHSE",     "icon_bg": "#fff7ed", "icon": _GI["qhse"],     "items": []},
    {"id": "projects", "label": "Projects", "icon_bg": "#fdf4ff", "icon": _GI["projects"], "items": []},
]


def all_items():
    """Flat list of every master item across all groups."""
    return [it for g in MASTER_GROUPS for it in g["items"]]


def build_masters_nav(can_view):
    """
    Return the group list annotated with per-item `can_view` and per-group
    `visible_count`, given a `can_view(perm_key) -> bool` callable. Templates
    loop over this to render cards and sidebar entries.
    """
    groups = []
    for g in MASTER_GROUPS:
        items = [{**it, "can_view": bool(can_view(it["key"]))} for it in g["items"]]
        groups.append({
            **{k: v for k, v in g.items() if k != "items"},
            "items": items,
            "visible_count": sum(1 for it in items if it["can_view"]),
        })
    return groups

"""
Deterministic intent router for analytics queries.
Maps user messages to tool functions + parameters. No LLM involved.
"""

import re
from datetime import datetime
from .tools import (
    count_rigs,
    list_rigs,
    get_headcount,
    get_incident_summary,
    list_incidents,
    get_hazard_card_trend,
    list_hazard_cards,
    get_material_cost,
    get_drilling_hours,
    get_rig_utilisation,
    get_drilling_performance,
    get_rig_locations,
    get_npt_analysis,
    get_hse_dashboard,
    list_overdue_hazard_cards,
    list_corrective_actions,
)

_CURRENT_YEAR = datetime.now().year

# Rig names are loaded from the DB once and cached in memory.
# Call _refresh_rig_cache() to reload (e.g. after a rig is added/renamed).
_rig_cache: list[dict] = []


def _refresh_rig_cache() -> None:
    """Load all rig names and short names from the DB into memory."""
    global _rig_cache
    from .tools import _query
    _rig_cache = _query(
        "SELECT Rig_Id, Rig_Name, Rig_Short_Name FROM eos_Mst_Rig ORDER BY Rig_Active DESC, Rig_Name"
    )


def _get_rig_cache() -> list[dict]:
    if not _rig_cache:
        _refresh_rig_cache()
    return _rig_cache


def _extract_rig(text: str) -> str | None:
    """Find a rig name or short name in the user message (case-insensitive)."""
    lower = text.lower()
    rigs = _get_rig_cache()
    # Try longest names first to avoid partial collisions (e.g. "SK1" vs "SK01")
    candidates = sorted(
        [(r["Rig_Name"], r["Rig_Short_Name"]) for r in rigs],
        key=lambda x: len(x[0]),
        reverse=True,
    )
    for full_name, short_name in candidates:
        if full_name.lower() in lower:
            return full_name
        if short_name and short_name.lower() in lower:
            return short_name
    return None


def _extract_year(text: str) -> int | None:
    m = re.search(r'\b(20\d{2})\b', text)
    if m:
        return int(m.group(1))
    lower = text.lower()
    if "this year" in lower or "current year" in lower:
        return _CURRENT_YEAR
    if "last year" in lower or "previous year" in lower:
        return _CURRENT_YEAR - 1
    return None


def _extract_limit(text: str, default: int = 5) -> int:
    """Extract a requested count/limit from the message."""
    # "show 10 incidents", "last 5", "top 20", "recent 3"
    m = re.search(r'\b(top|last|recent|show|give me|first)?\s*(\d+)\b', text, re.IGNORECASE)
    if m:
        n = int(m.group(2))
        if 1 <= n <= 50:
            return n
    return default


def _extract_haz_status(text: str) -> str | None:
    lower = text.lower()
    if "open" in lower:
        return "open"
    if "closed" in lower or "close" in lower:
        return "closed"
    return None


def _extract_rig_status(text: str) -> str:
    lower = text.lower()
    if "active" in lower and "inactive" not in lower:
        return "active"
    if "inactive" in lower:
        return "inactive"
    return "all"


_MONTH_MAP = {
    "january": 1, "jan": 1,
    "february": 2, "feb": 2,
    "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "may": 5,
    "june": 6, "jun": 6,
    "july": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}


def _extract_month(text: str) -> int | None:
    lower = text.lower()
    for name, num in _MONTH_MAP.items():
        if name in lower:
            return num
    m = re.search(r'\bmonth\s+(\d{1,2})\b', lower)
    if m:
        n = int(m.group(1))
        if 1 <= n <= 12:
            return n
    return None


def route(user_message: str, context: dict | None = None) -> dict | None:
    """
    Match the user message to an analytics tool and return its result.
    Returns None if no analytics intent is detected → falls through to RAG.
    context: optional dict with 'rig' and 'year' extracted from prior messages.
    """
    msg   = user_message.lower().strip()
    rig   = _extract_rig(msg)   or (context or {}).get("rig")
    year  = _extract_year(msg)  or (context or {}).get("year")
    limit = _extract_limit(msg)

    # ── Rig count ──────────────────────────────────────────────────────────────
    if any(p in msg for p in [
        "how many rigs", "count of rigs", "number of rigs",
        "rig count", "total rigs",
    ]):
        return count_rigs()

    # ── Rig listing ────────────────────────────────────────────────────────────
    if any(p in msg for p in [
        "list rigs", "list all rigs", "show rigs", "show all rigs",
        "which rigs", "what rigs", "our rigs", "available rigs",
        "all rigs", "name the rigs",
        "list active rigs", "list inactive rigs",
        "show active rigs", "show inactive rigs",
        "active rigs", "inactive rigs",
    ]):
        status = _extract_rig_status(msg)
        return list_rigs(status=status)

    # ── Headcount ──────────────────────────────────────────────────────────────
    if any(p in msg for p in [
        "headcount", "head count", "how many employee", "how many staff",
        "how many crew", "number of employee", "number of crew",
        "total employee", "total staff", "total crew",
        "employees on", "crew on", "staff on", "people on",
        "how many people",
    ]):
        dept = None
        dept_kw = re.search(
            r'(?:in|for|from|of)\s+(?:the\s+)?([a-z &]+?)\s+(?:department|dept)\b',
            msg
        )
        if dept_kw:
            dept = dept_kw.group(1).strip()
        return get_headcount(rig=rig, dept=dept)

    # ── NPT analysis (must be before incident summary — both share "npt" keyword)
    _npt_direct = any(p in msg for p in [
        "non productive", "non-productive", "npt analysis", "npt breakdown",
        "npt hours", "npt trend", "lost time", "downtime analysis",
        "downtime reason", "what caused npt", "npt by rig",
        "non productive time analysis", "npt %", "npt percent",
        "npt for", "npt on", "npt this year", "npt last year",
        "npt reason", "npt cause", "frequent npt", "common npt",
        "top npt", "most npt", "npt category", "npt categories",
        "what is causing", "what's causing", "why npt", "npt summary",
    ])
    _npt_followup = (context or {}).get("tool") == "get_npt_analysis" and any(p in msg for p in [
        "breakdown", "more", "detail", "monthly", "trend", "reason", "cause", "rig",
    ])
    if _npt_direct or _npt_followup:
        return get_npt_analysis(rig=rig, year=year)

    # ── Incident listing (recent records) ─────────────────────────────────────
    if any(p in msg for p in [
        "show incident", "list incident", "recent incident",
        "latest incident", "last incident", "show accident",
        "list accident",
    ]):
        return list_incidents(rig=rig, year=year, limit=limit)

    # ── Incident summary (counts/stats) ───────────────────────────────────────
    if any(p in msg for p in [
        "incident", "accident", "injuries", "injury",
        "near miss", "severity", "person injured",
    ]):
        return get_incident_summary(rig=rig, year=year)

    # ── Oldest / overdue open hazard cards (specific records) ─────────────────
    if any(p in msg for p in [
        "oldest open card", "oldest hazard card", "oldest card",
        "which card is oldest", "which is the oldest",
        "overdue hazard card", "overdue open card", "overdue card",
        "long overdue card", "cards overdue", "outstanding card",
        "unresolved card", "aged card", "card ageing list",
    ]):
        return list_overdue_hazard_cards(rig=rig, limit=limit)

    # ── Corrective actions from incident investigations ────────────────────────
    _ca_direct = any(p in msg for p in [
        "corrective action", "corrective measure", "action recommended",
        "action taken", "incident action", "investigation action",
        "what action was taken", "action status", "pending action",
        "overdue action", "action closure", "open action",
        "who is responsible", "action party", "responsible party",
    ])
    _ca_followup = (context or {}).get("tool") == "list_corrective_actions" and any(p in msg for p in [
        "more", "show more", "overdue", "open", "closed",
    ])
    if _ca_direct or _ca_followup:
        ca_status = None
        lower = msg.lower()
        if "overdue" in lower:
            ca_status = "overdue"
        elif "open" in lower or "pending" in lower:
            ca_status = "open"
        elif "closed" in lower or "completed" in lower:
            ca_status = "closed"
        return list_corrective_actions(rig=rig, year=year, status=ca_status, limit=limit)

    # ── HSE dashboard overview (comprehensive — before individual hazard blocks) ─
    if any(p in msg for p in [
        "hse dashboard", "hse overview", "hse summary", "hse kpi",
        "hse performance", "hse report", "hse metrics",
        "card submission rate", "card close rate", "card closure rate",
        "action closure rate", "corrective action closure",
        "card ageing", "overdue card", "overdue hazard card",
        "incident to hazard", "inc to haz", "incident hazard ratio",
        "positive recognition", "hazard type breakdown", "hazard type split",
        "safety card submission", "hse statistics", "safety overview",
    ]):
        return get_hse_dashboard(rig=rig, year=year)

    # ── Hazard card listing (recent records) ──────────────────────────────────
    if any(p in msg for p in [
        "show hazard", "list hazard", "recent hazard",
        "show haz card", "list haz card",
        "open hazard", "closed hazard",
    ]):
        haz_status = _extract_haz_status(msg)
        return list_hazard_cards(rig=rig, year=year, status=haz_status, limit=limit)

    # ── Hazard card summary ────────────────────────────────────────────────────
    if any(p in msg for p in [
        "hazard", "haz card", "hazard card", "hid card",
        "unsafe act", "unsafe condition", "timeout for safety",
        "near miss card", "safety card",
    ]):
        return get_hazard_card_trend(rig=rig, year=year)

    # ── Material cost ──────────────────────────────────────────────────────────
    if any(p in msg for p in [
        "material cost", "material expense", "material spend",
        "procurement cost", "opc cost", "opc material",
        "spare parts cost", "spare parts expenditure", "spares cost",
        "parts cost", "material expenditure",
    ]):
        return get_material_cost(rig=rig, year=year)

    # ── Rig utilisation ────────────────────────────────────────────────────────
    _util_direct = any(p in msg for p in [
        "utilisation", "utilization", "rig utilisation", "rig utilization",
        "uptime", "productive time", "operating hours", "operating time",
        "standby hours", "zero rate", "rig efficiency",
    ])
    _util_followup = (context or {}).get("tool") == "get_rig_utilisation" and any(p in msg for p in [
        "breakdown", "month wise", "monthly breakdown", "month-wise",
        "show breakdown", "give breakdown", "more detail", "hours",
        "operating", "standby", "repair", "rig move",
    ])
    if _util_direct or _util_followup:
        month = _extract_month(msg)
        return get_rig_utilisation(rig=rig, year=year, month=month)

    # ── Drilling performance (ROP) ─────────────────────────────────────────────
    _dp_direct = any(p in msg for p in [
        "rate of penetration", "rop", "metres drilled", "meters drilled",
        "drilling performance", "drill performance",
        "metres per hour", "meters per hour", "m/hr", "m per hour",
        "hole section", "drill depth", "depth drilled",
    ])
    _dp_followup = (context or {}).get("tool") == "get_drilling_performance" and any(p in msg for p in [
        "breakdown", "section", "year over year", "yoy", "trend", "operation",
    ])
    if _dp_direct or _dp_followup:
        return get_drilling_performance(rig=rig, year=year)

    # ── Rig locations / well history ───────────────────────────────────────────
    _loc_direct = any(p in msg for p in [
        "drilling location", "drilled at", "drill location", "drill site",
        "which location", "which well", "well location", "where did", "where has",
        "where is the rig", "where is.*drilling", "location of rig",
        "currently drilling", "active well", "ongoing well",
        "coordinates", "latitude", "longitude",
    ])
    _loc_followup = (context or {}).get("tool") == "get_rig_locations" and any(p in msg for p in [
        "more", "detail", "all", "show", "list",
    ])
    if _loc_direct or _loc_followup:
        return get_rig_locations(rig=rig, year=year)

    # ── Drilling hours ─────────────────────────────────────────────────────────
    if any(p in msg for p in [
        "drilling hour", "drilling ops", "drilling operation",
        "hours drilled", "total hours", "drilling time",
    ]):
        return get_drilling_hours(rig=rig, year=year)

    return None

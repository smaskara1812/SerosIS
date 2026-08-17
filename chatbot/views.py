import json
import threading
import uuid as _uuid_mod
from datetime import datetime
from pathlib import Path

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import logout as auth_logout
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET, require_http_methods
from langchain_core.messages import HumanMessage, AIMessage

from .models import Conversation, Message
from .rag.chain import get_rag_chain
from .health import run_all as run_health_checks
from .analytics.router import route as analytics_route
from .permissions import require_permission, get_user_access as _get_access
from . import audit as _audit
from .db.sql import dbq


def _invalidate_user_perm_cache(user_id):
    """Remove cached permission data from all live sessions for a given user_id."""
    from django.contrib.sessions.backends.db import SessionStore
    from django.contrib.sessions.models import Session
    from django.utils import timezone
    target_key = f"_seros_access_{user_id}"
    for session in Session.objects.filter(expire_date__gt=timezone.now()):
        try:
            store = SessionStore(session.session_key)
            if target_key in store:
                del store[target_key]
                store.save()
        except Exception:
            pass

_chain = None


def logout_view(request):
    auth_logout(request)
    return redirect("/login/")


def forbidden_view(request, exception=None):
    return render(request, "chatbot/403.html", status=403)


# ── Manual ingest background runner ───────────────────────────────────────────

_ingest_lock = threading.Lock()
_ingest_status: dict = {
    "running": False,
    "last_run": None,
    "last_result": None,   # "success" | "error" | None
    "last_message": "Not yet run",
}

_ALLOWED_EXTENSIONS = {".pdf", ".docx"}
_MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB


def _run_ingest_thread():
    global _chain
    try:
        from chatbot.rag.ingest import ingest
        ingest()
        _ingest_status.update({
            "running": False,
            "last_result": "success",
            "last_message": "Completed successfully",
            "last_run": datetime.now().isoformat(),
        })
    except Exception as exc:
        _ingest_status.update({
            "running": False,
            "last_result": "error",
            "last_message": str(exc),
            "last_run": datetime.now().isoformat(),
        })
    finally:
        _chain = None  # force chain rebuild with new vectorstore


def _get_chain():
    global _chain
    if _chain is None:
        _chain = get_rag_chain()
    return _chain


def _build_lc_history(messages):
    """Convert DB Message rows to LangChain message objects for the chain."""
    history = []
    for msg in messages:
        if msg.role == Message.ROLE_USER:
            history.append(HumanMessage(content=msg.content))
        else:
            history.append(AIMessage(content=msg.content))
    return history


def _auto_title(text: str, max_len: int = 45) -> str:
    text = text.strip()
    return text if len(text) <= max_len else text[:max_len].rsplit(" ", 1)[0] + "…"


# ── Pages ──────────────────────────────────────────────────────────────────────

@require_permission("chat", "view")
def chat_page(request):
    return render(request, "chatbot/chat.html")


@require_permission("health", "view")
def health_page(request):
    # Render the shell instantly — checks are fetched client-side via /api/health/
    return render(request, "chatbot/health.html")


@require_http_methods(["GET"])
def health_api(request):
    checks = run_health_checks()
    overall_ok = all(v["ok"] for v in checks.values())
    return JsonResponse({"overall_ok": overall_ok, **checks})


# ── Conversation API ───────────────────────────────────────────────────────────

@require_http_methods(["GET"])
def conversation_list(request):
    convos = Conversation.objects.using("chathistory").values(
        "id", "title", "updated_at"
    )
    return JsonResponse({"conversations": list(convos)}, encoder=_UUIDDateEncoder)


@csrf_exempt
@require_POST
def conversation_create(request):
    convo = Conversation.objects.using("chathistory").create()
    return JsonResponse({"id": str(convo.id), "title": convo.title}, status=201)


@require_http_methods(["GET"])
def conversation_detail(request, conversation_id):
    """Return a page of messages (cursor-based, newest-first pagination).

    Query params:
      before=<message-uuid>  — return messages older than this message
      limit=<int>            — page size (default 50, max 100)
    """
    convo = get_object_or_404(Conversation.objects.using("chathistory"), id=conversation_id)

    limit = min(int(request.GET.get("limit", 50)), 100)
    before_id = request.GET.get("before")

    qs = convo.messages.using("chathistory")
    if before_id:
        try:
            pivot = Message.objects.using("chathistory").get(id=before_id)
            qs = qs.filter(created_at__lt=pivot.created_at)
        except Message.DoesNotExist:
            pass

    # Fetch one extra to detect has_more
    rows = list(qs.order_by("-created_at")[: limit + 1])
    has_more = len(rows) > limit
    rows = rows[:limit]
    rows.reverse()  # chronological order for the client

    messages = [
        {
            "id": str(m.id),
            "role": m.role,
            "content": m.content,
            "sources": m.sources,
            "created_at": m.created_at,
        }
        for m in rows
    ]

    return JsonResponse(
        {
            "id": str(convo.id),
            "title": convo.title,
            "messages": messages,
            "has_more": has_more,
            "oldest_message_id": str(rows[0].id) if rows else None,
        },
        encoder=_UUIDDateEncoder,
    )


@csrf_exempt
@require_http_methods(["DELETE"])
def conversation_delete(request, conversation_id):
    convo = get_object_or_404(Conversation.objects.using("chathistory"), id=conversation_id)
    convo.delete()
    return JsonResponse({"ok": True})


@csrf_exempt
@require_http_methods(["PATCH"])
def conversation_rename(request, conversation_id):
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    title = body.get("title", "").strip()
    if not title:
        return JsonResponse({"error": "Title cannot be empty"}, status=400)

    convo = get_object_or_404(Conversation.objects.using("chathistory"), id=conversation_id)
    convo.title = title
    convo.save(using="chathistory", update_fields=["title"])
    return JsonResponse({"id": str(convo.id), "title": convo.title})


# ── Conversation Search ────────────────────────────────────────────────────────

@require_http_methods(["GET"])
def conversation_search(request):
    q = request.GET.get("q", "").strip()
    if not q:
        return JsonResponse({"conversations": [], "query": ""})

    results = {}  # id → result dict, deduplicated

    # Title matches
    title_hits = (
        Conversation.objects.using("chathistory")
        .filter(title__icontains=q)
        .order_by("-updated_at")[:30]
    )
    for c in title_hits:
        results[str(c.id)] = {
            "id": str(c.id),
            "title": c.title,
            "updated_at": c.updated_at,
            "match_in": "title",
            "snippet": None,
        }

    # Message content matches — pick one representative message per conversation
    msg_hits = (
        Message.objects.using("chathistory")
        .filter(content__icontains=q)
        .select_related("conversation")
        .order_by("-created_at")[:100]
    )
    for m in msg_hits:
        cid = str(m.conversation_id)
        if cid in results:
            continue  # already listed via title match
        results[cid] = {
            "id": cid,
            "title": m.conversation.title,
            "updated_at": m.conversation.updated_at,
            "match_in": "message",
            "snippet": _make_snippet(m.content, q),
        }

    # Sort by updated_at descending and cap at 30
    ordered = sorted(results.values(), key=lambda x: x["updated_at"], reverse=True)[:30]
    return JsonResponse({"conversations": ordered, "query": q}, encoder=_UUIDDateEncoder)


def _make_snippet(text: str, query: str, context: int = 60) -> str:
    idx = text.lower().find(query.lower())
    if idx == -1:
        return text[:context] + ("…" if len(text) > context else "")
    start = max(0, idx - 30)
    end = min(len(text), idx + len(query) + context - 30)
    snippet = text[start:end]
    if start > 0:
        snippet = "…" + snippet
    if end < len(text):
        snippet += "…"
    return snippet


# ── Manual Management ─────────────────────────────────────────────────────────

@require_permission("manuals", "view")
def manuals_page(request):
    return render(request, "chatbot/manuals.html")


@require_http_methods(["GET"])
def manual_list(request):
    from chatbot.rag.config import MANUALS_DIR
    files = []
    if MANUALS_DIR.exists():
        for f in sorted(MANUALS_DIR.iterdir()):
            if f.is_file() and f.suffix.lower() in _ALLOWED_EXTENSIONS:
                stat = f.stat()
                files.append({
                    "name": f.name,
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                })
    return JsonResponse({"files": files})


@csrf_exempt
@require_POST
def manual_upload(request):
    from chatbot.rag.config import MANUALS_DIR
    uploaded = request.FILES.getlist("files")
    if not uploaded:
        return JsonResponse({"error": "No files provided"}, status=400)

    MANUALS_DIR.mkdir(parents=True, exist_ok=True)
    saved, errors = [], []

    for f in uploaded:
        ext = Path(f.name).suffix.lower()
        safe_name = Path(f.name).name  # strip any directory component

        if ext not in _ALLOWED_EXTENSIONS:
            errors.append({"name": f.name, "error": "Only PDF and DOCX files are allowed"})
            continue
        if f.size > _MAX_UPLOAD_BYTES:
            errors.append({"name": f.name, "error": "File exceeds 50 MB limit"})
            continue

        dest = MANUALS_DIR / safe_name
        with open(dest, "wb") as out:
            for chunk in f.chunks():
                out.write(chunk)
        saved.append(safe_name)

    status = 201 if saved else 400
    return JsonResponse({"saved": saved, "errors": errors}, status=status)


@csrf_exempt
@require_http_methods(["DELETE"])
@csrf_exempt
@require_http_methods(["DELETE"])
def manual_delete(request, filename):
    from chatbot.rag.config import MANUALS_DIR
    safe_name = Path(filename).name
    if safe_name != filename:
        return JsonResponse({"error": "Invalid filename"}, status=400)

    target = MANUALS_DIR / safe_name
    if not target.exists():
        return JsonResponse({"error": "File not found"}, status=404)
    if target.suffix.lower() not in _ALLOWED_EXTENSIONS:
        return JsonResponse({"error": "Not a manual file"}, status=403)

    target.unlink()
    return JsonResponse({"ok": True})


@csrf_exempt
@require_POST
def manual_ingest_start(request):
    with _ingest_lock:
        if _ingest_status["running"]:
            return JsonResponse({"error": "Ingestion already in progress"}, status=409)
        _ingest_status.update({
            "running": True,
            "last_result": None,
            "last_message": "Running…",
            "last_run": None,
        })

    t = threading.Thread(target=_run_ingest_thread, daemon=True)
    t.start()
    return JsonResponse({"ok": True})


@require_http_methods(["GET"])
def manual_ingest_status(request):
    return JsonResponse(dict(_ingest_status))


_ALL_RIGS_PHRASES = {
    "all rigs", "all rig", "overall", "across all", "every rig",
    "all of them", "all rigs combined", "total overall", "for all",
    "no rig", "any rig", "company wide", "company-wide",
}


def _extract_analytics_context(messages) -> dict:
    """
    Scan the last few user messages and the last bot analytics result
    to recover rig/year/tool context for follow-up questions.
    """
    from .analytics.router import _extract_rig, _extract_year

    # Check if the last assistant message was an analytics response (no sources → analytics)
    last_tool = None
    for msg in reversed(messages[-10:]):
        if msg.role == Message.ROLE_ASSISTANT and not msg.sources:
            content = msg.content.lower()
            if "utilisation" in content or "utilization" in content or "operating hours" in content:
                last_tool = "get_rig_utilisation"
            elif "incident" in content or "accident" in content:
                last_tool = "get_incident_summary"
            elif "hazard" in content or "haz card" in content:
                last_tool = "get_hazard_card_trend"
            elif "material cost" in content or "spare parts" in content:
                last_tool = "get_material_cost"
            elif "rate of penetration" in content or "rop" in content or "metres drilled" in content or "m/hr" in content:
                last_tool = "get_drilling_performance"
            elif "location" in content and ("spud" in content or "drilled" in content or "ongoing" in content or "completed" in content):
                last_tool = "get_rig_locations"
            elif "non-productive" in content or "npt" in content and ("downtime" in content or "events" in content or "lost" in content):
                last_tool = "get_npt_analysis"
            elif "drilling hour" in content:
                last_tool = "get_drilling_hours"
            break

    # The current (most recent) user message — used to detect "all rigs" intent
    current_msg = ""
    for msg in reversed(messages):
        if msg.role == Message.ROLE_USER:
            current_msg = msg.content.lower()
            break

    # If the user is explicitly asking for all rigs, don't inherit a rig from context
    wants_all = any(phrase in current_msg for phrase in _ALL_RIGS_PHRASES)

    # Only inherit rig from history if the current message is a short follow-up
    # (no rig name of its own AND short enough to be a follow-up, not a fresh question)
    current_rig  = _extract_rig(current_msg)
    current_year = _extract_year(current_msg)

    if wants_all or current_rig:
        # User named a specific rig or explicitly asked for all — don't inherit history
        rig = None if wants_all else current_rig
    else:
        # Inherit rig from recent history only for short follow-up messages
        is_followup = len(current_msg.split()) <= 10
        if is_followup:
            recent_user_text = " ".join(
                msg.content for msg in messages[-8:] if msg.role == Message.ROLE_USER
            )
            rig = _extract_rig(recent_user_text)
        else:
            rig = None  # fresh question with no rig mentioned → all rigs

    year = current_year or _extract_year(" ".join(
        msg.content for msg in messages[-8:] if msg.role == Message.ROLE_USER
    ))

    return {"tool": last_tool, "rig": rig, "year": year}


# ── Dashboard ─────────────────────────────────────────────────────────────────

@require_permission("dashboard", "view")
def dashboard_page(request):
    return render(request, "chatbot/dashboard.html")


@require_http_methods(["GET"])
def dashboard_meta(request):
    """Returns available years and full rig list for dashboard filters."""
    from .analytics.tools import _query
    years = _query("""
        SELECT DISTINCT YEAR(Drilling_Dtl_Dt) AS yr
        FROM eos_Drilling_Dtl
        WHERE Drilling_Dtl_Dt IS NOT NULL
        ORDER BY yr DESC
    """)
    rigs = _query("""
        SELECT Rig_Id, Rig_Name, Rig_Short_Name, Rig_Active
        FROM eos_Mst_Rig
        WHERE Rig_Type_Id IN (1,2)
        ORDER BY Rig_Active DESC, Rig_Name
    """)
    return JsonResponse({
        "years": [r["yr"] for r in years if r["yr"]],
        "rigs":  rigs,
    })


@require_http_methods(["GET"])
def dashboard_api(request):
    from .analytics.tools import count_rigs, get_headcount, get_incident_summary, get_rig_utilisation, get_drilling_performance, get_npt_analysis, _query

    year_param  = request.GET.get("year")
    year        = int(year_param) if year_param and year_param.isdigit() else None
    rig_filter  = request.GET.getlist("rig")  # zero or more rig names

    rig_counts  = count_rigs()
    headcount   = get_headcount()
    incidents   = get_incident_summary(year=year)

    # Build utilisation data with optional rig filter
    # Call once per selected rig (or once for all if none selected)
    if rig_filter:
        all_monthly = []
        for rn in rig_filter:
            r = get_rig_utilisation(rig=rn, year=year)
            all_monthly.extend(r.get("monthly", []))
        # Aggregate summary from combined data
        util_summary = {}
        if all_monthly:
            total_op = sum(r.get("operating_hrs", 0) or 0 for r in all_monthly)
            total_sb = sum(r.get("standby_hrs",   0) or 0 for r in all_monthly)
            total_rp = sum(r.get("repair_hrs",    0) or 0 for r in all_monthly)
            total_zr = sum(r.get("zero_rate_hrs", 0) or 0 for r in all_monthly)
            total_rm = sum(r.get("rig_move_hrs",  0) or 0 for r in all_monthly)
            total_all = total_op + total_sb + total_rp + total_zr + total_rm
            util_summary = {
                "avg_utilisation_pct": round(total_op / total_all * 100, 1) if total_all else None,
                "total_operating_hrs": round(total_op, 1),
                "total_standby_hrs":   round(total_sb, 1),
                "total_repair_hrs":    round(total_rp, 1),
                "total_zero_rate_hrs": round(total_zr, 1),
                "total_rig_move_hrs":  round(total_rm, 1),
                "rigs_covered": len(rig_filter),
            }
    else:
        utilisation  = get_rig_utilisation(year=year)
        all_monthly  = utilisation.get("monthly", [])
        util_summary = utilisation.get("summary", {})

    monthly_raw = all_monthly
    months_set  = sorted({r["month"] for r in monthly_raw})
    rigs_set    = sorted({r["Rig_Name"] for r in monthly_raw})
    lookup      = {(r["Rig_Name"], r["month"]): r for r in monthly_raw}

    util_series = [
        {
            "name": rig,
            "data": [
                lookup.get((rig, m), {}).get("utilisation_pct")
                for m in months_set
            ],
        }
        for rig in rigs_set
    ]

    hours_breakdown = {
        "months": months_set,
        "operating":  [round(sum((lookup.get((r, m), {}).get("operating_hrs",  0) or 0) for r in rigs_set), 1) for m in months_set],
        "standby":    [round(sum((lookup.get((r, m), {}).get("standby_hrs",    0) or 0) for r in rigs_set), 1) for m in months_set],
        "repair":     [round(sum((lookup.get((r, m), {}).get("repair_hrs",     0) or 0) for r in rigs_set), 1) for m in months_set],
        "zero_rate":  [round(sum((lookup.get((r, m), {}).get("zero_rate_hrs",  0) or 0) for r in rigs_set), 1) for m in months_set],
        "rig_move":   [round(sum((lookup.get((r, m), {}).get("rig_move_hrs",   0) or 0) for r in rigs_set), 1) for m in months_set],
    }

    inc_trend   = incidents.get("by_year", [])
    inc_by_rig  = incidents.get("by_rig", [])
    inc_summary = incidents.get("summary", {})

    # Extra incident detail for drill-downs (not filtered by year so drilldown works across years)
    year_cond = f"AND YEAR(i.Incident_Date) = {year}" if year else ""
    inc_monthly_detail = _query(f"""
        SELECT
            YEAR(i.Incident_Date)                                              AS yr,
            DATE_FORMAT(i.Incident_Date, '%%Y-%%m')                           AS month,
            COUNT(*)                                                            AS total,
            SUM(CASE WHEN i.Incident_Severity = 'H' THEN 1 ELSE 0 END)        AS high,
            SUM(CASE WHEN i.Incident_Severity = 'M' THEN 1 ELSE 0 END)        AS medium,
            SUM(CASE WHEN i.Incident_Severity = 'L' THEN 1 ELSE 0 END)        AS low_sev,
            SUM(CASE WHEN COALESCE(i.Person_Injured,'') = 'Y' THEN 1 ELSE 0 END) AS injuries,
            ROUND(COALESCE(SUM(i.NPT_Hrs_Loss), 0), 1)                        AS npt_hours
        FROM eos_Incident_Details i
        WHERE COALESCE(i.Marked_As_Deleted, '') != 'Y' {year_cond}
        GROUP BY YEAR(i.Incident_Date), DATE_FORMAT(i.Incident_Date, '%%Y-%%m')
        ORDER BY DATE_FORMAT(i.Incident_Date, '%%Y-%%m')
    """)
    inc_rig_year_detail = _query("""
        SELECT r.Rig_Name, YEAR(i.Incident_Date) AS yr, COUNT(*) AS total,
               SUM(CASE WHEN i.Incident_Severity = 'H' THEN 1 ELSE 0 END) AS high,
               SUM(CASE WHEN i.Incident_Severity = 'M' THEN 1 ELSE 0 END) AS medium,
               SUM(CASE WHEN i.Incident_Severity = 'L' THEN 1 ELSE 0 END) AS low_sev
        FROM eos_Incident_Details i
        JOIN eos_Mst_Rig r ON i.Rig_Id = r.Rig_Id AND r.Rig_Type_Id IN (1,2)
        WHERE COALESCE(i.Marked_As_Deleted, '') != 'Y'
        GROUP BY r.Rig_Name, YEAR(i.Incident_Date)
        ORDER BY r.Rig_Name, YEAR(i.Incident_Date)
    """)
    crew_by_rig = headcount.get("crew_by_rig", [])

    # Per-rig per-month detail for drill-down (pass raw monthly data)
    def _f(v):
        return float(v) if v is not None else 0.0

    monthly_detail = [
        {
            "rig":         r.get("Rig_Name"),
            "month":       r.get("month"),
            "operating":   _f(r.get("operating_hrs")),
            "standby":     _f(r.get("standby_hrs")),
            "repair":      _f(r.get("repair_hrs")),
            "zero_rate":   _f(r.get("zero_rate_hrs")),
            "rig_move":    _f(r.get("rig_move_hrs")),
            "utilisation": _f(r.get("utilisation_pct")),
        }
        for r in monthly_raw
    ]

    return JsonResponse({
        "year": year or "all",
        "monthly_detail": monthly_detail,
        "kpi": {
            "avg_utilisation_pct": util_summary.get("avg_utilisation_pct"),
            "total_rigs":          rig_counts.get("total"),
            "active_rigs":         rig_counts.get("active"),
            "total_employees":     headcount.get("total_active_employees"),
            "active_rig_crew":     headcount.get("active_rig_crew"),
            "total_incidents":     inc_summary.get("total_incidents"),
            "total_npt_hours":     inc_summary.get("total_npt_hours"),
        },
        "utilisation": {
            "months": months_set,
            "series": util_series,
        },
        "hours_breakdown": hours_breakdown,
        "incidents": {
            "years":       [r.get("year")      for r in reversed(inc_trend)],
            "counts":      [r.get("incidents") for r in reversed(inc_trend)],
            "by_rig_names":  [r.get("Rig_Name")  for r in inc_by_rig],
            "by_rig_counts": [r.get("incidents")  for r in inc_by_rig],
            "monthly_detail":   [
                {"yr": r["yr"], "month": r["month"], "total": int(r["total"]),
                 "high": int(r["high"]), "medium": int(r["medium"]), "low_sev": int(r["low_sev"]),
                 "injuries": int(r["injuries"]), "npt_hours": float(r["npt_hours"] or 0)}
                for r in inc_monthly_detail
            ],
            "rig_year_detail": [
                {"rig": r["Rig_Name"], "yr": int(r["yr"]), "total": int(r["total"]),
                 "high": int(r["high"]), "medium": int(r["medium"]), "low_sev": int(r["low_sev"])}
                for r in inc_rig_year_detail
            ],
        },
        "headcount": {
            "rigs":   [r.get("Rig_Name") for r in crew_by_rig],
            "counts": [r.get("crew")     for r in crew_by_rig],
        },
        "drilling_performance": _build_drill_perf(year, rig_filter),
        "npt": _build_npt(year, rig_filter),
    })


def _build_drill_perf(year, rig_filter):
    from .analytics.tools import get_drilling_performance
    if rig_filter:
        combined = {"total_metres": 0, "total_drill_hrs": 0}
        for rn in rig_filter:
            r = get_drilling_performance(rig=rn, year=year)
            s = r.get("summary", {})
            combined["total_metres"]    += float(s.get("total_metres") or 0)
            combined["total_drill_hrs"] += float(s.get("total_drill_hrs") or 0)
        rop = round(combined["total_metres"] / combined["total_drill_hrs"], 2) if combined["total_drill_hrs"] else None
        # Use first rig's breakdown data; rop_by_rig always uses all rigs from the unfiltered call
        first    = get_drilling_performance(rig=rig_filter[0], year=year)
        all_rigs = get_drilling_performance(year=year)
        return _format_drill_perf({
            "summary":       {"total_metres": combined["total_metres"], "total_drill_hrs": combined["total_drill_hrs"], "rop_mhr": rop},
            "by_section":    first.get("by_section", []),
            "ops_breakdown": first.get("ops_breakdown", []),
            "flat_time":            first.get("flat_time", []),
            "flat_time_total_hrs":  first.get("flat_time_total_hrs", 0),
            "flat_time_rig_detail": first.get("flat_time_rig_detail", []),
            "locations_by_rig":    all_rigs.get("locations_by_rig", []),
            "rop_by_rig":          all_rigs.get("rop_by_rig", []),
            "yoy":           first.get("yoy", []),
        })
    else:
        return _format_drill_perf(get_drilling_performance(year=year))


def _format_drill_perf(data):
    def _f(v):
        return float(v) if v is not None else 0.0
    s = data.get("summary", {})
    return {
        "summary": {
            "rop_mhr":               _f(s.get("rop_mhr")),
            "total_metres":          _f(s.get("total_metres")),
            "total_drill_hrs":       _f(s.get("total_drill_hrs")),
            "drill_operations":      int(s.get("drill_operations") or 0),
        },
        "yoy": [
            {"yr": int(r["yr"]), "rop_mhr": _f(r.get("rop_mhr")), "total_metres": _f(r.get("total_metres")), "drill_hrs": _f(r.get("drill_hrs"))}
            for r in data.get("yoy", [])
        ],
        "by_section": [
            {"section": r["section"], "metres": _f(r.get("metres")), "drill_hrs": _f(r.get("drill_hrs")), "rop_mhr": _f(r.get("rop_mhr"))}
            for r in data.get("by_section", [])
        ],
        "ops_breakdown": [
            {"operation": r["operation"], "hours": _f(r.get("hours")), "pct": _f(r.get("pct"))}
            for r in data.get("ops_breakdown", [])
        ],
        "flat_time": [
            {"operation": r["operation"], "hours": _f(r.get("hours")), "pct": _f(r.get("pct"))}
            for r in data.get("flat_time", [])
        ],
        "flat_time_total_hrs": _f(data.get("flat_time_total_hrs", 0)),
        "flat_time_rig_detail": [
            {"operation": r["operation"], "rig": r["Rig_Name"], "hours": _f(r.get("hours"))}
            for r in data.get("flat_time_rig_detail", [])
        ],
        "locations_by_rig": [
            {
                "rig":           r["Rig_Name"],
                "location":      r["Location"],
                "latitude":      r.get("Latitude") or "",
                "longitude":     r.get("Longitude") or "",
                "spud_dt":       r.get("spud_dt") or "",
                "completion_dt": r.get("completion_dt") or "",
                "metres":        _f(r.get("metres")),
                "drill_hrs":     _f(r.get("drill_hrs")),
                "rop_mhr":       _f(r.get("rop_mhr")),
            }
            for r in data.get("locations_by_rig", [])
        ],
        "rop_by_rig": [
            {"rig": r["Rig_Name"], "metres": _f(r.get("metres")), "drill_hrs": _f(r.get("drill_hrs")), "rop_mhr": _f(r.get("rop_mhr"))}
            for r in data.get("rop_by_rig", [])
        ],
    }


def _build_npt(year, rig_filter):
    from .analytics.tools import get_npt_analysis
    def _f(v): return float(v) if v is not None else 0.0
    if rig_filter:
        # Aggregate summary across selected rigs; use first rig for breakdown charts
        combined_npt = 0.0; combined_total = 0.0; combined_events = 0
        for rn in rig_filter:
            r = get_npt_analysis(rig=rn, year=year)
            combined_npt    += r["summary"]["total_npt_hrs"]
            combined_total  += r["summary"]["total_logged_hrs"]
            combined_events += r["summary"]["npt_events"]
        npt_pct = round(combined_npt / combined_total * 100, 2) if combined_total else None
        first = get_npt_analysis(rig=rig_filter[0], year=year)
        data = {**first, "summary": {**first["summary"], "total_npt_hrs": combined_npt, "total_logged_hrs": combined_total, "npt_events": combined_events, "npt_pct": npt_pct}}
    else:
        data = get_npt_analysis(year=year)
    s = data["summary"]
    return {
        "summary": {
            "total_npt_hrs":    _f(s.get("total_npt_hrs")),
            "npt_events":       int(s.get("npt_events") or 0),
            "avg_event_hrs":    _f(s.get("avg_event_hrs")),
            "npt_pct":          _f(s.get("npt_pct")) if s.get("npt_pct") is not None else None,
            "total_logged_hrs": _f(s.get("total_logged_hrs")),
        },
        "monthly":             data["monthly"],
        "npt_by_rig":          data["npt_by_rig"],
        "top_reasons":         data["top_reasons"],
        "incident_npt":        data["incident_npt"],
        "yoy":                 data["yoy"],
        "monthly_rig_detail":  data.get("monthly_rig_detail", []),
        "reason_rig_detail":   data.get("reason_rig_detail", []),
        "reason_rig_monthly":  data.get("reason_rig_monthly", []),
    }




def _build_hse(year, rig_filter):
    from .analytics.tools import get_hse_dashboard
    rig = rig_filter[0] if rig_filter else None
    data = get_hse_dashboard(rig=rig, year=year)
    return data



@require_GET
def dashboard_hse_api(request):
    year_param = request.GET.get("year")
    year       = int(year_param) if year_param and year_param.isdigit() else None
    rig_filter = request.GET.getlist("rig")
    return JsonResponse(_build_hse(year, rig_filter))


@require_GET
def dashboard_hse_hotspot_api(request):
    from .analytics.hse import get_haz_hotspot_data
    return JsonResponse(get_haz_hotspot_data())


@require_GET
def dashboard_hse_correlation_api(request):
    from .analytics.hse import get_haz_downtime_correlation
    return JsonResponse(get_haz_downtime_correlation())


def _build_workforce(year, rig_filter):
    from .analytics.tools import get_workforce_dashboard
    rig = rig_filter[0] if rig_filter else None
    data = get_workforce_dashboard(rig=rig, year=year)
    return data


@require_GET
def dashboard_workforce_api(request):
    year_param = request.GET.get("year")
    year       = int(year_param) if year_param and year_param.isdigit() else None
    rig_filter = request.GET.getlist("rig")
    return JsonResponse(_build_workforce(year, rig_filter))


# ── Finance dashboard ─────────────────────────────────────────────────────────


@require_http_methods(["GET"])
def dashboard_finance_meta(request):
    from .analytics.tools import _query
    years = _query("""
        SELECT DISTINCT YEAR(Invoice_Dt) AS yr FROM eos_Invoice_Hdr
        WHERE Invoice_Dt IS NOT NULL
        UNION
        SELECT DISTINCT YEAR(MR_Dt) FROM eos_Material_Requisition_Hdr
        WHERE MR_Dt IS NOT NULL
        ORDER BY yr DESC
    """)
    return JsonResponse({"years": [r["yr"] for r in years if r["yr"]]})


@require_http_methods(["GET"])
def dashboard_finance_api(request):
    from .analytics.tools import get_finance_dashboard
    year_param = request.GET.get("year")
    year = int(year_param) if year_param and year_param.isdigit() else None
    return JsonResponse(get_finance_dashboard(year=year))


# ── Rigs 360 ─────────────────────────────────────────────────────────────────

@require_permission("rigs", "view")
def rigs_page(request):
    return render(request, "chatbot/rigs/index.html")


@require_permission("rigs", "view")
def rig_detail_page(request, rig_id):
    return render(request, "chatbot/rigs/detail.html", {"rig_id": rig_id})


# ── Masters ───────────────────────────────────────────────────────────────────

def masters_page(request):
    from .masters_registry import build_masters_nav
    access = _get_access(request)
    is_admin = access["is_admin"]
    p = access["perms"]
    cv = lambda key: is_admin or p.get(key, {}).get("view", False)
    # masters_nav is also provided globally by the context processor, but pass it
    # explicitly so the index template's meaning is self-contained.
    return render(request, "chatbot/masters/index.html",
                  {"masters_nav": build_masters_nav(cv)})

# ── Cost Centre Type Master ───────────────────────────────────────────────────

@require_permission("masters.cost_centre_types", "view")
def cost_centre_type_page(request):
    return render(request, "chatbot/masters/cost_centre_type.html")

@require_GET
def cost_centre_type_list_api(request):
    from django.db import connections
    with connections["default"].cursor() as cursor:
        dbq(cursor, """
            SELECT Cost_Centre_Type_Id, Cost_Centre_Type_Name,
                   Cost_Centre_Type_Shortname, Cost_Centre_Type_Active
            FROM eos_Mst_Cost_Centre_Type
            ORDER BY Cost_Centre_Type_Name
        """)
        cols = [c[0] for c in cursor.description]
        rows = [dict(zip(cols, row)) for row in cursor.fetchall()]
    return JsonResponse({"results": rows})

@require_GET
def cost_centre_type_get_api(request, type_id):
    from django.db import connections
    with connections["default"].cursor() as cursor:
        dbq(cursor, """
            SELECT Cost_Centre_Type_Id, Cost_Centre_Type_Name,
                   Cost_Centre_Type_Shortname, Cost_Centre_Type_Active
            FROM eos_Mst_Cost_Centre_Type
            WHERE Cost_Centre_Type_Id = %s
        """, [type_id])
        cols = [c[0] for c in cursor.description]
        row = cursor.fetchone()
    if not row:
        return JsonResponse({"error": "Not found"}, status=404)
    return JsonResponse(dict(zip(cols, row)))

@csrf_exempt
def cost_centre_type_save_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    _a = _get_access(request)
    if not _a["is_admin"]:
        try:
            _bpk = json.loads(request.body)
            _has_id = bool(_bpk.get("Cost_Centre_Type_Id"))
        except Exception:
            _has_id = False
        _pact = "edit" if _has_id else "add"
        if not _a["perms"].get("masters.cost_centre_types", {}).get(_pact):
            return JsonResponse({"error": "Permission denied"}, status=403)
    from django.db import connections
    body = json.loads(request.body)
    type_id  = body.get("Cost_Centre_Type_Id") or None
    name     = (body.get("Cost_Centre_Type_Name") or "").strip()
    short    = (body.get("Cost_Centre_Type_Shortname") or "").strip()
    active   = body.get("Cost_Centre_Type_Active", "Y")
    if not name or not short:
        return JsonResponse({"error": "Type Name and Short Name are required"}, status=400)
    now = datetime.now()
    cr_user_id = _audit.ops_user_id(request)
    with connections["default"].cursor() as cursor:
        _before = _audit.snap(cursor, "masters.cost_centre_types", type_id)
        if type_id:
            dbq(cursor, """
                UPDATE eos_Mst_Cost_Centre_Type
                SET Cost_Centre_Type_Name=%s, Cost_Centre_Type_Shortname=%s,
                    Cost_Centre_Type_Active=%s, Mod_User_Id=%s, Mod_Dt=%s
                WHERE Cost_Centre_Type_Id=%s
            """, [name, short, active, cr_user_id, now, type_id])
            _audit.record_save(request, cursor, "masters.cost_centre_types", type_id, _before)
            return JsonResponse({"success": True, "Cost_Centre_Type_Id": type_id, "action": "updated"})
        else:
            dbq(cursor, "SELECT COALESCE(MAX(Cost_Centre_Type_Id), 0) + 1 FROM eos_Mst_Cost_Centre_Type")
            new_id = cursor.fetchone()[0]
            dbq(cursor, """
                INSERT INTO eos_Mst_Cost_Centre_Type
                    (Cost_Centre_Type_Id, Cost_Centre_Type_Name, Cost_Centre_Type_Shortname,
                     Cost_Centre_Type_Active, Cr_User_Id, Cr_Dt)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, [new_id, name, short, "Y", cr_user_id, now])
            _audit.record_save(request, cursor, "masters.cost_centre_types", new_id, _before)
            return JsonResponse({"success": True, "Cost_Centre_Type_Id": new_id, "action": "inserted"})

@csrf_exempt
def cost_centre_type_deactivate_api(request, type_id):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    _a = _get_access(request)
    if not _a["is_admin"] and not _a["perms"].get("masters.cost_centre_types", {}).get("delete"):
        return JsonResponse({"error": "Permission denied"}, status=403)
    from django.db import connections
    with connections["default"].cursor() as cursor:
        _before = _audit.snap(cursor, "masters.cost_centre_types", type_id)
        dbq(cursor, """
            UPDATE eos_Mst_Cost_Centre_Type
            SET Cost_Centre_Type_Active='N', Mod_User_Id=%s, Mod_Dt=%s
            WHERE Cost_Centre_Type_Id=%s
        """, [_audit.ops_user_id(request), datetime.now(), type_id])
    _audit.record_deactivate(request, "masters.cost_centre_types", type_id, _before)
    return JsonResponse({"success": True})

# ── Cost Centre Master ────────────────────────────────────────────────────────

@require_permission("masters.cost_centres", "view")
def cost_centre_page(request):
    return render(request, "chatbot/masters/cost_centre.html")

@require_GET
def cost_centre_meta_api(request):
    from django.db import connections
    with connections["default"].cursor() as cursor:
        dbq(cursor, """
            SELECT Cost_Centre_Type_Id, Cost_Centre_Type_Name
            FROM eos_Mst_Cost_Centre_Type
            WHERE Cost_Centre_Type_Active = 'Y'
            ORDER BY Cost_Centre_Type_Name
        """)
        cols = [c[0] for c in cursor.description]
        types = [dict(zip(cols, row)) for row in cursor.fetchall()]
    return JsonResponse({"types": types})

@require_GET
def cost_centre_locations_search_api(request):
    from django.db import connections
    q          = request.GET.get("q", "").strip()
    offset     = max(0, int(request.GET.get("offset", 0)))
    limit      = min(50, max(1, int(request.GET.get("limit", 20))))
    country_id = request.GET.get("country_id") or None
    with connections["default"].cursor() as cursor:
        params = [f"%{q}%"]
        sql = "SELECT Location_Id, Location_Name FROM Mst_Location WHERE location_active = 'Y' AND Location_Name LIKE %s"
        if country_id:
            sql += " AND Country_Id = %s"
            params.append(country_id)
        sql += " ORDER BY Location_Name LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        dbq(cursor, sql, params)
        cols = [c[0] for c in cursor.description]
        rows = [dict(zip(cols, row)) for row in cursor.fetchall()]
    return JsonResponse({"results": rows})

@require_GET
def cost_centre_list_api(request):
    from django.db import connections
    with connections["default"].cursor() as cursor:
        dbq(cursor, """
            SELECT cc.Cost_Centre_Id, cc.Cost_Centre_Name, cc.Old_Cost_Centre_Name,
                   cc.Cost_Centre_Type_Id, cct.Cost_Centre_Type_Name,
                   cc.Rig_Id, r.Rig_Name,
                   cc.Location_Id, l.Location_Name,
                   cc.Cost_Centre_Active
            FROM eos_Mst_Cost_Centre cc
            LEFT JOIN eos_Mst_Cost_Centre_Type cct ON cc.Cost_Centre_Type_Id = cct.Cost_Centre_Type_Id
            LEFT JOIN eos_Mst_Rig r ON cc.Rig_Id = r.Rig_Id
            LEFT JOIN Mst_Location l ON cc.Location_Id = l.Location_Id
            ORDER BY cc.Cost_Centre_Name
        """)
        cols = [c[0] for c in cursor.description]
        rows = [dict(zip(cols, row)) for row in cursor.fetchall()]
    return JsonResponse({"results": rows})

@require_GET
def cost_centre_get_api(request, cc_id):
    from django.db import connections
    with connections["default"].cursor() as cursor:
        dbq(cursor, """
            SELECT cc.Cost_Centre_Id, cc.Cost_Centre_Name, cc.Old_Cost_Centre_Name,
                   cc.Cost_Centre_Type_Id, cct.Cost_Centre_Type_Name,
                   cc.Rig_Id, r.Rig_Name,
                   cc.Location_Id, l.Location_Name,
                   cc.Cost_Centre_Active
            FROM eos_Mst_Cost_Centre cc
            LEFT JOIN eos_Mst_Cost_Centre_Type cct ON cc.Cost_Centre_Type_Id = cct.Cost_Centre_Type_Id
            LEFT JOIN eos_Mst_Rig r ON cc.Rig_Id = r.Rig_Id
            LEFT JOIN Mst_Location l ON cc.Location_Id = l.Location_Id
            WHERE cc.Cost_Centre_Id = %s
        """, [cc_id])
        cols = [c[0] for c in cursor.description]
        row = cursor.fetchone()
    if not row:
        return JsonResponse({"error": "Not found"}, status=404)
    return JsonResponse(dict(zip(cols, row)))

@csrf_exempt
def cost_centre_save_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    _a = _get_access(request)
    if not _a["is_admin"]:
        try:
            _bpk = json.loads(request.body)
            _has_id = bool(_bpk.get("Cost_Centre_Id"))
        except Exception:
            _has_id = False
        _pact = "edit" if _has_id else "add"
        if not _a["perms"].get("masters.cost_centres", {}).get(_pact):
            return JsonResponse({"error": "Permission denied"}, status=403)
    from django.db import connections
    body = json.loads(request.body)
    cc_id    = body.get("Cost_Centre_Id") or None
    name     = (body.get("Cost_Centre_Name") or "").strip()
    old_name = (body.get("Old_Cost_Centre_Name") or "").strip()
    type_id  = body.get("Cost_Centre_Type_Id") or None
    rig_id   = body.get("Rig_Id") or None
    loc_id   = body.get("Location_Id") or None
    active   = body.get("Cost_Centre_Active", "Y")
    if not name or not old_name or not type_id:
        return JsonResponse({"error": "Name, Old Name and Type are required"}, status=400)
    now = datetime.now()
    cr_user_id = _audit.ops_user_id(request)
    with connections["default"].cursor() as cursor:
        _before = _audit.snap(cursor, "masters.cost_centres", cc_id)
        if cc_id:
            dbq(cursor, """
                UPDATE eos_Mst_Cost_Centre
                SET Cost_Centre_Name=%s, Old_Cost_Centre_Name=%s, Cost_Centre_Type_Id=%s,
                    Rig_Id=%s, Location_Id=%s, Cost_Centre_Active=%s,
                    Mod_User_Id=%s, Mod_Dt=%s
                WHERE Cost_Centre_Id=%s
            """, [name, old_name, type_id, rig_id, loc_id, active, cr_user_id, now, cc_id])
            _audit.record_save(request, cursor, "masters.cost_centres", cc_id, _before)
            return JsonResponse({"success": True, "Cost_Centre_Id": cc_id, "action": "updated"})
        else:
            dbq(cursor, "SELECT COALESCE(MAX(Cost_Centre_Id), 0) + 1 FROM eos_Mst_Cost_Centre")
            new_id = cursor.fetchone()[0]
            dbq(cursor, """
                INSERT INTO eos_Mst_Cost_Centre
                    (Cost_Centre_Id, Cost_Centre_Name, Old_Cost_Centre_Name,
                     Cost_Centre_Type_Id, Rig_Id, Location_Id,
                     Cost_Centre_Active, Cr_User_Id, Cr_Dt)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, [new_id, name, old_name, type_id, rig_id, loc_id, "Y", cr_user_id, now])
            _audit.record_save(request, cursor, "masters.cost_centres", new_id, _before)
            return JsonResponse({"success": True, "Cost_Centre_Id": new_id, "action": "inserted"})

@csrf_exempt
def cost_centre_deactivate_api(request, cc_id):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    _a = _get_access(request)
    if not _a["is_admin"] and not _a["perms"].get("masters.cost_centres", {}).get("delete"):
        return JsonResponse({"error": "Permission denied"}, status=403)
    from django.db import connections
    with connections["default"].cursor() as cursor:
        _before = _audit.snap(cursor, "masters.cost_centres", cc_id)
        dbq(cursor, """
            UPDATE eos_Mst_Cost_Centre
            SET Cost_Centre_Active='N', Mod_User_Id=%s, Mod_Dt=%s
            WHERE Cost_Centre_Id=%s
        """, [_audit.ops_user_id(request), datetime.now(), cc_id])
    _audit.record_deactivate(request, "masters.cost_centres", cc_id, _before)
    return JsonResponse({"success": True})

# ── Operator Master Form ──────────────────────────────────────────────────────

@require_permission("masters.operators", "view")
def operator_master_page(request):
    return render(request, "chatbot/masters/operator.html")

@require_GET
def operator_list_api(request):
    from django.db import connections
    with connections["default"].cursor() as cursor:
        dbq(cursor, """
            SELECT o.Operator_Id, o.Operator_Name, o.Operator_Short_Name,
                   o.Operator_SAP_Code, o.WBS_Client_Code,
                   o.Country_Id, c.country_name,
                   o.Location_Id, l.Location_Name,
                   o.Contact_Person, o.Tel_No, o.Email_Id,
                   o.Operator_Active
            FROM eos_Mst_Operator o
            LEFT JOIN Mst_Country c ON o.Country_Id = c.country_id
            LEFT JOIN Mst_Location l ON o.Location_Id = l.Location_Id
            ORDER BY o.Operator_Name
        """)
        cols = [c[0] for c in cursor.description]
        rows = [dict(zip(cols, row)) for row in cursor.fetchall()]
    return JsonResponse({"results": rows})

@require_GET
def operator_get_api(request, op_id):
    from django.db import connections
    with connections["default"].cursor() as cursor:
        dbq(cursor, """
            SELECT o.Operator_Id, o.Operator_Name, o.Operator_Short_Name,
                   o.Operator_SAP_Code, o.WBS_Client_Code,
                   o.Country_Id, c.country_name,
                   o.Location_Id, l.Location_Name,
                   o.Contact_Person, o.Tel_No, o.Email_Id,
                   o.Operator_Active
            FROM eos_Mst_Operator o
            LEFT JOIN Mst_Country c ON o.Country_Id = c.country_id
            LEFT JOIN Mst_Location l ON o.Location_Id = l.Location_Id
            WHERE o.Operator_Id = %s
        """, [op_id])
        cols = [c[0] for c in cursor.description]
        row = cursor.fetchone()
    if not row:
        return JsonResponse({"error": "Not found"}, status=404)
    return JsonResponse(dict(zip(cols, row)))

@csrf_exempt
def operator_save_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    _a = _get_access(request)
    if not _a["is_admin"]:
        try:
            _bpk = json.loads(request.body)
            _has_id = bool(_bpk.get("Operator_Id"))
        except Exception:
            _has_id = False
        _pact = "edit" if _has_id else "add"
        if not _a["perms"].get("masters.operators", {}).get(_pact):
            return JsonResponse({"error": "Permission denied"}, status=403)
    from django.db import connections
    body       = json.loads(request.body)
    op_id      = body.get("Operator_Id") or None
    name       = (body.get("Operator_Name") or "").strip()
    short_name = (body.get("Operator_Short_Name") or "").strip()
    sap_code   = (body.get("Operator_SAP_Code") or "").strip() or None
    wbs_code   = (body.get("WBS_Client_Code") or "").strip() or None
    country_id = body.get("Country_Id") or None
    loc_id     = body.get("Location_Id") or None
    contact    = (body.get("Contact_Person") or "").strip() or None
    tel        = (body.get("Tel_No") or "").strip() or None
    email      = (body.get("Email_Id") or "").strip() or None
    active     = body.get("Operator_Active", "Y")
    if not name or not short_name:
        return JsonResponse({"error": "Operator name and short name are required"}, status=400)
    now = datetime.now()
    cr_user_id = _audit.ops_user_id(request)
    with connections["default"].cursor() as cursor:
        _before = _audit.snap(cursor, "masters.operators", op_id)
        if op_id:
            dbq(cursor, """
                UPDATE eos_Mst_Operator
                SET Operator_Name=%s, Operator_Short_Name=%s, Operator_SAP_Code=%s,
                    WBS_Client_Code=%s, Country_Id=%s, Location_Id=%s,
                    Contact_Person=%s, Tel_No=%s, Email_Id=%s,
                    Operator_Active=%s, Mod_User_Id=%s, Mod_Dt=%s
                WHERE Operator_Id=%s
            """, [name, short_name, sap_code, wbs_code, country_id, loc_id,
                  contact, tel, email, active, cr_user_id, now, op_id])
            _audit.record_save(request, cursor, "masters.operators", op_id, _before)
            return JsonResponse({"success": True, "Operator_Id": op_id, "action": "updated"})
        else:
            dbq(cursor, "SELECT COALESCE(MAX(Operator_Id), 0) + 1 FROM eos_Mst_Operator")
            new_id = cursor.fetchone()[0]
            dbq(cursor, """
                INSERT INTO eos_Mst_Operator
                    (Operator_Id, Operator_Name, Operator_Short_Name, Operator_SAP_Code,
                     WBS_Client_Code, Country_Id, Location_Id, Contact_Person,
                     Tel_No, Email_Id, Operator_Active, Cr_User_Id, Cr_Dt)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, [new_id, name, short_name, sap_code, wbs_code, country_id, loc_id,
                  contact, tel, email, "Y", cr_user_id, now])
            _audit.record_save(request, cursor, "masters.operators", new_id, _before)
            return JsonResponse({"success": True, "Operator_Id": new_id, "action": "inserted"})

@csrf_exempt
def operator_deactivate_api(request, op_id):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    _a = _get_access(request)
    if not _a["is_admin"] and not _a["perms"].get("masters.operators", {}).get("delete"):
        return JsonResponse({"error": "Permission denied"}, status=403)
    from django.db import connections
    with connections["default"].cursor() as cursor:
        _before = _audit.snap(cursor, "masters.operators", op_id)
        dbq(cursor, """
            UPDATE eos_Mst_Operator
            SET Operator_Active='N', Mod_User_Id=%s, Mod_Dt=%s
            WHERE Operator_Id=%s
        """, [_audit.ops_user_id(request), datetime.now(), op_id])
    _audit.record_deactivate(request, "masters.operators", op_id, _before)
    return JsonResponse({"success": True})

@require_GET
def operator_countries_search_api(request):
    from django.db import connections
    q      = request.GET.get("q", "").strip()
    offset = max(0, int(request.GET.get("offset", 0)))
    limit  = min(50, max(1, int(request.GET.get("limit", 20))))
    with connections["default"].cursor() as cursor:
        dbq(cursor, """
            SELECT country_id, country_name FROM Mst_Country
            WHERE country_active = 'Y' AND country_name LIKE %s
            ORDER BY country_name LIMIT %s OFFSET %s
        """, [f"%{q}%", limit, offset])
        cols = [c[0] for c in cursor.description]
        rows = [dict(zip(cols, row)) for row in cursor.fetchall()]
    return JsonResponse({"results": rows})

# ── Cost Centre Type — check/delete ──────────────────────────────────────────

@require_GET
def cost_centre_type_check_delete_api(request, type_id):
    from django.db import connections
    with connections["default"].cursor() as cursor:
        refs = []
        for table, col, label in [
            ("eos_Mst_Cost_Centre", "Cost_Centre_Type_Id", "Cost Centres"),
            ("eos_Mst_HSE_Manhours_Party", "Cost_Centre_Type_Id", "HSE Manhours Parties"),
        ]:
            dbq(cursor, f"SELECT COUNT(*) FROM {table} WHERE {col}=%s", [type_id])
            count = cursor.fetchone()[0]
            if count > 0:
                refs.append({"label": label, "count": count})
    return JsonResponse({"can_delete": len(refs) == 0, "references": refs})


@csrf_exempt
def cost_centre_type_delete_api(request, type_id):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    _a = _get_access(request)
    if not _a["is_admin"] and not _a["perms"].get("masters.cost_centre_types", {}).get("delete"):
        return JsonResponse({"error": "Permission denied"}, status=403)
    from django.db import connections
    with connections["default"].cursor() as cursor:
        _before = _audit.snap(cursor, "masters.cost_centre_types", type_id)
        for table, col in [
            ("eos_Mst_Cost_Centre", "Cost_Centre_Type_Id"),
            ("eos_Mst_HSE_Manhours_Party", "Cost_Centre_Type_Id"),
        ]:
            dbq(cursor, f"SELECT COUNT(*) FROM {table} WHERE {col}=%s", [type_id])
            if cursor.fetchone()[0] > 0:
                return JsonResponse({"error": "Record is still referenced and cannot be deleted."}, status=409)
        dbq(cursor, "DELETE FROM eos_Mst_Cost_Centre_Type WHERE Cost_Centre_Type_Id=%s", [type_id])
    _audit.record_delete(request, "masters.cost_centre_types", type_id, _before)
    return JsonResponse({"success": True})


# ── Cost Centre — check/delete ────────────────────────────────────────────────

@require_GET
def cost_centre_check_delete_api(request, cc_id):
    from django.db import connections
    with connections["default"].cursor() as cursor:
        refs = []
        for table, col, label in [
            ("eos_Invoice_Hdr", "Cost_Centre_Id", "Invoices"),
            ("eos_Actual_Crew_Expense", "Cost_Centre_Id", "Crew Expenses"),
            ("eos_Budgeted_Crew_Expense", "Cost_Centre_Id", "Budgeted Crew Expenses"),
            ("eos_Cost_Centre_To_Company_Mapping", "Cost_Centre_Id", "Company Mappings"),
            ("eos_Fs_Emp_To_CC_Mapping", "Cost_Centre_Id", "Employee Mappings"),
            ("eos_Proj_To_Cost_Centre_Mapping", "Cost_Centre_Id", "Project Mappings"),
        ]:
            dbq(cursor, f"SELECT COUNT(*) FROM {table} WHERE {col}=%s", [cc_id])
            count = cursor.fetchone()[0]
            if count > 0:
                refs.append({"label": label, "count": count})
    return JsonResponse({"can_delete": len(refs) == 0, "references": refs})


@csrf_exempt
def cost_centre_delete_api(request, cc_id):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    _a = _get_access(request)
    if not _a["is_admin"] and not _a["perms"].get("masters.cost_centres", {}).get("delete"):
        return JsonResponse({"error": "Permission denied"}, status=403)
    from django.db import connections
    with connections["default"].cursor() as cursor:
        _before = _audit.snap(cursor, "masters.cost_centres", cc_id)
        for table, col in [
            ("eos_Invoice_Hdr", "Cost_Centre_Id"),
            ("eos_Actual_Crew_Expense", "Cost_Centre_Id"),
            ("eos_Budgeted_Crew_Expense", "Cost_Centre_Id"),
            ("eos_Cost_Centre_To_Company_Mapping", "Cost_Centre_Id"),
            ("eos_Fs_Emp_To_CC_Mapping", "Cost_Centre_Id"),
            ("eos_Proj_To_Cost_Centre_Mapping", "Cost_Centre_Id"),
        ]:
            dbq(cursor, f"SELECT COUNT(*) FROM {table} WHERE {col}=%s", [cc_id])
            if cursor.fetchone()[0] > 0:
                return JsonResponse({"error": "Record is still referenced and cannot be deleted."}, status=409)
        dbq(cursor, "DELETE FROM eos_Mst_Cost_Centre WHERE Cost_Centre_Id=%s", [cc_id])
    _audit.record_delete(request, "masters.cost_centres", cc_id, _before)
    return JsonResponse({"success": True})


# ── Operator — check/delete ───────────────────────────────────────────────────

@require_GET
def operator_check_delete_api(request, op_id):
    from django.db import connections
    with connections["default"].cursor() as cursor:
        refs = []
        for table, col, label in [
            ("eos_Mst_Project", "Operator_Id", "Projects"),
            ("eos_Mst_Project_Contract", "Operator_Id", "Project Contracts"),
            ("eos_Tender_Dtl", "Operator_Id", "Tenders"),
            ("eos_Competitor_Contract_Dtl", "Operator_Id", "Competitor Contracts"),
        ]:
            dbq(cursor, f"SELECT COUNT(*) FROM {table} WHERE {col}=%s", [op_id])
            count = cursor.fetchone()[0]
            if count > 0:
                refs.append({"label": label, "count": count})
    return JsonResponse({"can_delete": len(refs) == 0, "references": refs})


@csrf_exempt
def operator_delete_api(request, op_id):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    _a = _get_access(request)
    if not _a["is_admin"] and not _a["perms"].get("masters.operators", {}).get("delete"):
        return JsonResponse({"error": "Permission denied"}, status=403)
    from django.db import connections
    with connections["default"].cursor() as cursor:
        _before = _audit.snap(cursor, "masters.operators", op_id)
        for table, col in [
            ("eos_Mst_Project", "Operator_Id"),
            ("eos_Mst_Project_Contract", "Operator_Id"),
            ("eos_Tender_Dtl", "Operator_Id"),
            ("eos_Competitor_Contract_Dtl", "Operator_Id"),
        ]:
            dbq(cursor, f"SELECT COUNT(*) FROM {table} WHERE {col}=%s", [op_id])
            if cursor.fetchone()[0] > 0:
                return JsonResponse({"error": "Record is still referenced and cannot be deleted."}, status=409)
        dbq(cursor, "DELETE FROM eos_Mst_Operator WHERE Operator_Id=%s", [op_id])
    _audit.record_delete(request, "masters.operators", op_id, _before)
    return JsonResponse({"success": True})


# ── Rig Master — check/delete ─────────────────────────────────────────────────

@require_GET
def rig_master_check_delete_api(request, rig_id):
    from django.db import connections
    with connections["default"].cursor() as cursor:
        refs = []
        for table, col, label in [
            ("eos_Mst_Cost_Centre", "Rig_Id", "Cost Centres"),
            ("eos_Incident_Details", "Rig_Id", "Incidents"),
            ("eos_Hazard_ID_Card", "Rig_Id", "Hazard Cards"),
            ("eos_Drilling_Hdr", "Rig_Id", "Drilling Records"),
            ("eos_Crew_Grp_Dtl", "Rig_Id", "Crew Group Records"),
            ("eos_Mst_Crew_Grp", "Rig_Id", "Crew Groups"),
        ]:
            dbq(cursor, f"SELECT COUNT(*) FROM {table} WHERE {col}=%s", [rig_id])
            count = cursor.fetchone()[0]
            if count > 0:
                refs.append({"label": label, "count": count})
    return JsonResponse({"can_delete": len(refs) == 0, "references": refs})


@csrf_exempt
def rig_master_delete_api(request, rig_id):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    _a = _get_access(request)
    if not _a["is_admin"] and not _a["perms"].get("masters.rigs", {}).get("delete"):
        return JsonResponse({"error": "Permission denied"}, status=403)
    from django.db import connections
    with connections["default"].cursor() as cursor:
        _before = _audit.snap(cursor, "masters.rigs", rig_id)
        for table, col in [
            ("eos_Mst_Cost_Centre", "Rig_Id"),
            ("eos_Incident_Details", "Rig_Id"),
            ("eos_Hazard_ID_Card", "Rig_Id"),
            ("eos_Drilling_Hdr", "Rig_Id"),
            ("eos_Crew_Grp_Dtl", "Rig_Id"),
            ("eos_Mst_Crew_Grp", "Rig_Id"),
        ]:
            dbq(cursor, f"SELECT COUNT(*) FROM {table} WHERE {col}=%s", [rig_id])
            if cursor.fetchone()[0] > 0:
                return JsonResponse({"error": "Record is still referenced and cannot be deleted."}, status=409)
        dbq(cursor, "DELETE FROM eos_Mst_Rig WHERE Rig_Id=%s", [rig_id])
    _audit.record_delete(request, "masters.rigs", rig_id, _before)
    return JsonResponse({"success": True})


# ── Rig Master Form ───────────────────────────────────────────────────────────

@require_permission("masters.rigs", "view")
def rig_master_page(request):
    return render(request, "chatbot/rigs/master.html")


@require_GET
def rig_master_meta_api(request):
    from django.db import connections
    with connections["default"].cursor() as cursor:
        dbq(cursor, """
            SELECT rs.Rig_Subtype_Id, rs.Rig_Subtype_Name, rs.Rig_Type_Id, rt.Rig_Type_Name
            FROM Mst_Rig_Subtype rs
            JOIN Mst_Rig_Type rt ON rs.Rig_Type_Id = rt.Rig_Type_Id
            ORDER BY rs.Rig_Subtype_Name
        """)
        cols = [c[0] for c in cursor.description]
        subtypes = [dict(zip(cols, row)) for row in cursor.fetchall()]

        dbq(cursor, "SELECT Rig_Type_Id, Rig_Type_Name FROM Mst_Rig_Type ORDER BY Rig_Type_Name")
        cols = [c[0] for c in cursor.description]
        types = [dict(zip(cols, row)) for row in cursor.fetchall()]

    return JsonResponse({"subtypes": subtypes, "types": types})


@require_GET
def rig_master_search_api(request):
    from django.db import connections
    q = request.GET.get("q", "").strip()
    with connections["default"].cursor() as cursor:
        if q:
            dbq(cursor, """
                SELECT r.Rig_Id, r.Rig_Name, r.Rig_Short_Name,
                       rs.Rig_Subtype_Name, rt.Rig_Type_Name, r.Rig_Active
                FROM eos_Mst_Rig r
                JOIN Mst_Rig_Subtype rs ON r.Rig_Subtype_Id = rs.Rig_Subtype_Id
                JOIN Mst_Rig_Type rt ON r.Rig_Type_Id = rt.Rig_Type_Id
                WHERE r.Rig_Name LIKE %s OR r.Rig_Short_Name LIKE %s
                ORDER BY r.Rig_Name
                LIMIT 20
            """, [f"%{q}%", f"%{q}%"])
        else:
            dbq(cursor, """
                SELECT r.Rig_Id, r.Rig_Name, r.Rig_Short_Name,
                       rs.Rig_Subtype_Name, rt.Rig_Type_Name, r.Rig_Active
                FROM eos_Mst_Rig r
                JOIN Mst_Rig_Subtype rs ON r.Rig_Subtype_Id = rs.Rig_Subtype_Id
                JOIN Mst_Rig_Type rt ON r.Rig_Type_Id = rt.Rig_Type_Id
                ORDER BY r.Rig_Name
            """)
        cols = [c[0] for c in cursor.description]
        rows = [dict(zip(cols, row)) for row in cursor.fetchall()]
    return JsonResponse({"results": rows})


@require_GET
def rig_master_get_api(request, rig_id):
    from django.db import connections
    with connections["default"].cursor() as cursor:
        dbq(cursor, """
            SELECT Rig_Id, Rig_Name, Rig_Short_Name, Old_Rig_Name,
                   Rig_Subtype_Id, Rig_Type_Id, Rig_Built_Dt,
                   Rig_Tel_No, Rig_Fax_No, Rig_Email_Id,
                   Personnel_Area, Org_Unit_Code, Rig_From, Rig_Active
            FROM eos_Mst_Rig WHERE Rig_Id = %s
        """, [rig_id])
        cols = [c[0] for c in cursor.description]
        row = cursor.fetchone()
    if not row:
        return JsonResponse({"error": "Not found"}, status=404)
    data = dict(zip(cols, row))
    for k in ["Rig_Built_Dt", "Rig_From"]:
        if data[k]:
            data[k] = data[k].isoformat()
    return JsonResponse(data)


@csrf_exempt
def rig_master_save_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    _a = _get_access(request)
    if not _a["is_admin"]:
        try:
            _bpk = json.loads(request.body)
            _has_id = bool(_bpk.get("Rig_Id"))
        except Exception:
            _has_id = False
        _pact = "edit" if _has_id else "add"
        if not _a["perms"].get("masters.rigs", {}).get(_pact):
            return JsonResponse({"error": "Permission denied"}, status=403)

    from django.db import connections
    body = json.loads(request.body)
    rig_id = body.get("Rig_Id") or None

    required = ["Rig_Name", "Rig_Short_Name", "Rig_Subtype_Id", "Rig_Type_Id", "Rig_Built_Dt", "Rig_From"]
    for field in required:
        if not body.get(field):
            return JsonResponse({"error": f"{field} is required"}, status=400)

    now = datetime.now()
    cr_user_id = _audit.ops_user_id(request)  # placeholder until auth

    with connections["default"].cursor() as cursor:
        _before = _audit.snap(cursor, "masters.rigs", rig_id)
        if rig_id:
            rig_active = body.get("Rig_Active", "Y")
            if rig_active not in ("Y", "N"):
                rig_active = "Y"
            dbq(cursor, """
                UPDATE eos_Mst_Rig SET
                    Rig_Name=%s, Rig_Short_Name=%s, Old_Rig_Name=%s,
                    Rig_Subtype_Id=%s, Rig_Type_Id=%s, Rig_Built_Dt=%s,
                    Rig_Tel_No=%s, Rig_Fax_No=%s, Rig_Email_Id=%s,
                    Personnel_Area=%s, Org_Unit_Code=%s, Rig_From=%s,
                    Rig_Active=%s, Mod_User_Id=%s, Mod_Dt=%s
                WHERE Rig_Id=%s
            """, [
                body["Rig_Name"], body["Rig_Short_Name"], body.get("Old_Rig_Name") or None,
                body["Rig_Subtype_Id"], body["Rig_Type_Id"], body["Rig_Built_Dt"],
                body.get("Rig_Tel_No") or None, body.get("Rig_Fax_No") or None,
                body.get("Rig_Email_Id") or None, body.get("Personnel_Area") or None,
                body.get("Org_Unit_Code") or None, body["Rig_From"],
                rig_active, cr_user_id, now, rig_id,
            ])
            _audit.record_save(request, cursor, "masters.rigs", rig_id, _before)
            return JsonResponse({"success": True, "Rig_Id": rig_id, "action": "updated"})
        else:
            dbq(cursor, "SELECT COALESCE(MAX(Rig_Id), 0) + 1 FROM eos_Mst_Rig")
            new_id = cursor.fetchone()[0]
            dbq(cursor, """
                INSERT INTO eos_Mst_Rig (
                    Rig_Id, Rig_Name, Rig_Short_Name, Old_Rig_Name,
                    Rig_Subtype_Id, Rig_Type_Id, Rig_Built_Dt,
                    Rig_Tel_No, Rig_Fax_No, Rig_Email_Id,
                    Personnel_Area, Org_Unit_Code, Rig_From, Rig_Active,
                    Cr_User_Id, Cr_Dt
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'Y',%s,%s)
            """, [
                new_id, body["Rig_Name"], body["Rig_Short_Name"], body.get("Old_Rig_Name") or None,
                body["Rig_Subtype_Id"], body["Rig_Type_Id"], body["Rig_Built_Dt"],
                body.get("Rig_Tel_No") or None, body.get("Rig_Fax_No") or None,
                body.get("Rig_Email_Id") or None, body.get("Personnel_Area") or None,
                body.get("Org_Unit_Code") or None, body["Rig_From"],
                cr_user_id, now,
            ])
            _audit.record_save(request, cursor, "masters.rigs", new_id, _before)
            return JsonResponse({"success": True, "Rig_Id": new_id, "action": "inserted"})


@require_GET
def rigs_list_api(request):
    from .analytics.rigs import get_rigs_list
    rigs = get_rigs_list()
    return JsonResponse({"rigs": rigs})


@require_GET
def rig_overview_api(request, rig_id):
    from .analytics.rigs import get_rig_overview
    data = get_rig_overview(rig_id)
    return JsonResponse(data)


@require_GET
def rig_snapshot_api(request, rig_id):
    from .analytics.rigs import get_rig_snapshot
    year = request.GET.get("year")
    year = int(year) if year and year.isdigit() else datetime.now().year
    return JsonResponse(get_rig_snapshot(rig_id, year))


@require_GET
def rig_crew_groups_api(request, rig_id):
    from .analytics.rigs import get_rig_crew_groups
    return JsonResponse(get_rig_crew_groups(rig_id))


@require_GET
def rig_people_api(request, rig_id):
    from .analytics.rigs import get_rig_people
    year = request.GET.get("year")
    year = int(year) if year and year.isdigit() else datetime.now().year
    data = get_rig_people(rig_id, year)
    return JsonResponse(data)


@require_GET
def rig_safety_api(request, rig_id):
    from .analytics.rigs import get_rig_safety
    year = request.GET.get("year")
    year = int(year) if year and year.isdigit() else datetime.now().year
    data = get_rig_safety(rig_id, year)
    return JsonResponse(data)


@require_GET
def rig_finance_api(request, rig_id):
    from .analytics.rigs import get_rig_finance
    year = request.GET.get("year")
    year = int(year) if year and year.isdigit() else datetime.now().year
    data = get_rig_finance(rig_id, year)
    return JsonResponse(data)


@require_GET
def rig_operations_api(request, rig_id):
    from .analytics.rigs import get_rig_operations
    year = request.GET.get("year")
    year = int(year) if year and year.isdigit() else datetime.now().year
    data = get_rig_operations(rig_id, year)
    return JsonResponse(data)


# ── Listings ─────────────────────────────────────────────────────────────────

def listings_page(request):
    from .permissions import get_user_access, can_view as _can
    access = get_user_access(request)
    listing_perms = {
        "incidents":      _can(access, "listings.incidents"),
        "hazard_cards":   _can(access, "listings.hazard_cards"),
        "employees":      _can(access, "listings.employees"),
        "staff":          _can(access, "listings.staff"),
        "crew_rotations": _can(access, "listings.crew_rotations"),
        "invoices":       _can(access, "listings.invoices"),
        "certificates":   _can(access, "listings.certificates"),
        "users":          _can(access, "listings.users"),
    }
    return render(request, "chatbot/listings/index.html", {"listing_perms": listing_perms})


def _listing_context(request, menu_key):
    """Return template context with can_export flag for a listing page."""
    from .permissions import get_user_access
    access = get_user_access(request)
    can_export = access["is_admin"] or access["perms"].get(menu_key, {}).get("export", False)
    return {"can_export": can_export}


def _csv_response(rows: list, filename: str):
    """Return an HttpResponse with CSV content from a list of dicts."""
    import csv as _csv
    from django.http import HttpResponse
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    if not rows:
        return response
    writer = _csv.DictWriter(response, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)
    return response


@require_permission("listings.incidents", "view")
def listings_incidents_page(request):
    return render(request, "chatbot/listings/incidents.html",
                  _listing_context(request, "listings.incidents"))


@require_permission("listings.hazard_cards", "view")
def listings_hazard_cards_page(request):
    return render(request, "chatbot/listings/hazard_cards.html",
                  _listing_context(request, "listings.hazard_cards"))


@require_GET
def listings_meta_api(request):
    """Filter dropdown options shared by the Listings pages."""
    from .analytics.tools import _query
    years = _query("""
        SELECT DISTINCT YEAR(Incident_Date) AS yr FROM eos_Incident_Details
        WHERE Incident_Date IS NOT NULL
        UNION
        SELECT DISTINCT YEAR(Event_Dt) AS yr FROM eos_Hazard_ID_Card
        WHERE Event_Dt IS NOT NULL
        ORDER BY yr DESC
    """)
    rigs = _query("""
        SELECT Rig_Id, Rig_Name, Rig_Short_Name FROM eos_Mst_Rig
        WHERE Rig_Type_Id IN (1,2) ORDER BY Rig_Name
    """)
    incident_types = _query("SELECT Incident_Type_Id AS id, Incident_Type AS name FROM Mstx_Incident_Type ORDER BY Incident_Type")
    hazard_types = _query("SELECT Haz_Type_Id AS id, Haz_Type_Name AS name FROM eos_Mst_Hazard_Type ORDER BY Haz_Type_Name")
    work_locations = _query("SELECT Work_Location_Id AS id, Work_Location AS name FROM Mstx_Work_Location ORDER BY Work_Location")
    return JsonResponse({
        "years": [r["yr"] for r in years if r["yr"]],
        "rigs": rigs,
        "incident_types": incident_types,
        "hazard_types": hazard_types,
        "work_locations": work_locations,
    })


@require_GET
def listings_incidents_api(request):
    from .analytics.listings import get_incident_listing
    g = request.GET
    page      = g.get("page")
    page_size = g.get("page_size")
    year      = g.get("year")
    data = get_incident_listing(
        page=int(page) if page and page.isdigit() else None,
        page_size=int(page_size) if page_size and page_size.isdigit() else None,
        rig=g.get("rig") or None,
        year=int(year) if year and year.isdigit() else None,
        severity=g.get("severity") or None,
        person_injured=g.get("person_injured") or None,
        incident_type=g.get("incident_type") or None,
        search=g.get("search") or None,
        sort=g.get("sort") or None,
        sort_dir=g.get("sort_dir") or None,
    )
    return JsonResponse(data)


@require_GET
def listings_hazard_cards_api(request):
    from .analytics.listings import get_hazard_card_listing
    g = request.GET
    page      = g.get("page")
    page_size = g.get("page_size")
    year      = g.get("year")
    data = get_hazard_card_listing(
        page=int(page) if page and page.isdigit() else None,
        page_size=int(page_size) if page_size and page_size.isdigit() else None,
        rig=g.get("rig") or None,
        year=int(year) if year and year.isdigit() else None,
        hazard_type=g.get("hazard_type") or None,
        status=g.get("status") or None,
        tfs=g.get("tfs") or None,
        work_location=g.get("work_location") or None,
        search=g.get("search") or None,
        sort=g.get("sort") or None,
        sort_dir=g.get("sort_dir") or None,
    )
    return JsonResponse(data)


@require_GET
def listings_hazard_cards_pdf(request):
    from .analytics.listings import get_hazard_card_listing, EXPORT_PAGE_SIZE
    from .pdf_reports import generate_hazard_cards_pdf
    g = request.GET
    year = g.get("year")
    rig  = g.get("rig") or None
    result = get_hazard_card_listing(
        page=1, page_size=EXPORT_PAGE_SIZE,
        rig=rig,
        year=int(year) if year and year.isdigit() else None,
        hazard_type=g.get("hazard_type") or None,
        status=g.get("status") or None,
        tfs=g.get("tfs") or None,
        work_location=g.get("work_location") or None,
        search=g.get("search") or None,
    )
    if "error" in result:
        return JsonResponse(result, status=400)
    rows = result.get("rows", [])
    rig_label    = rig or "All Rigs"
    period_label = year or "All Time"
    pdf_bytes = generate_hazard_cards_pdf(rows, rig_label=rig_label, period_label=str(period_label))
    response = HttpResponse(bytes(pdf_bytes), content_type="application/pdf")
    response["Content-Disposition"] = 'inline; filename="hazard_cards.pdf"'
    return response


@require_permission("listings.employees", "view")
def listings_employees_page(request):
    return render(request, "chatbot/listings/employees.html",
                  _listing_context(request, "listings.employees"))


@require_GET
def listings_employees_meta_api(request):
    """Filter dropdown options for the Employee listing."""
    from .analytics.tools import _query
    rigs = _query("""
        SELECT Rig_Id, Rig_Name FROM eos_Mst_Rig
        WHERE Rig_Type_Id IN (1,2) ORDER BY Rig_Name
    """)
    ranks = _query("SELECT rank_id AS id, rank_name AS name FROM Mst_Rank ORDER BY rank_name")
    categories = _query("SELECT fs_category_id AS id, fs_category_name AS name FROM Mst_Fs_Category ORDER BY fs_category_name")
    emp_types = _query("SELECT emp_type_id AS id, emp_type_name AS name FROM Mst_Emp_Type ORDER BY emp_type_name")
    return JsonResponse({
        "rigs": rigs,
        "ranks": ranks,
        "categories": categories,
        "emp_types": emp_types,
    })


@require_GET
def listings_employees_api(request):
    from .analytics.listings import get_employee_listing
    g = request.GET
    page      = g.get("page")
    page_size = g.get("page_size")
    data = get_employee_listing(
        page=int(page) if page and page.isdigit() else None,
        page_size=int(page_size) if page_size and page_size.isdigit() else None,
        rig=g.get("rig") or None,
        rank=g.get("rank") or None,
        category=g.get("category") or None,
        emp_type=g.get("emp_type") or None,
        status=g.get("status") or None,
        gender=g.get("gender") or None,
        search=g.get("search") or None,
        sort=g.get("sort") or None,
        sort_dir=g.get("sort_dir") or None,
    )
    return JsonResponse(data)


@require_permission("listings.crew_rotations", "view")
def listings_crew_rotations_page(request):
    return render(request, "chatbot/listings/crew_rotations.html",
                  _listing_context(request, "listings.crew_rotations"))


@require_GET
def listings_crew_rotations_meta_api(request):
    """Filter dropdown options for the Crew Rotations listing."""
    from .analytics.tools import _query
    rigs = _query("""
        SELECT Rig_Id, Rig_Name FROM eos_Mst_Rig
        WHERE Rig_Type_Id IN (1,2) ORDER BY Rig_Name
    """)
    ranks = _query("""
        SELECT DISTINCT mr.rank_id AS id, mr.rank_name AS name
        FROM eos_Service_Details sd
        JOIN Mst_Rank mr ON sd.Rank_Id = mr.rank_id
        WHERE sd.Serv_Subtype_Id = 7 AND sd.Serv_Subtype_To IS NULL
        ORDER BY mr.rank_name
    """)
    return JsonResponse({
        "rigs": rigs,
        "ranks": ranks,
    })


@require_GET
def listings_crew_rotations_api(request):
    from .analytics.listings import get_crew_rotation_listing
    g = request.GET
    page      = g.get("page")
    page_size = g.get("page_size")
    data = get_crew_rotation_listing(
        page=int(page) if page and page.isdigit() else None,
        page_size=int(page_size) if page_size and page_size.isdigit() else None,
        rig=g.get("rig") or None,
        rank=g.get("rank") or None,
        status=g.get("status") or None,
        search=g.get("search") or None,
        sort=g.get("sort") or None,
        sort_dir=g.get("sort_dir") or None,
    )
    return JsonResponse(data)


@require_permission("listings.staff", "view")
def listings_staff_page(request):
    return render(request, "chatbot/listings/staff.html",
                  _listing_context(request, "listings.staff"))


@require_GET
def listings_staff_meta_api(request):
    """Filter dropdown options for the Company Staff listing."""
    from .analytics.tools import _query
    companies = _query("SELECT COMPANY_ID AS id, Company_Name AS name FROM Mst_Company ORDER BY Company_Name")
    depts = _query("SELECT Dept_Id AS id, Dept_Name AS name FROM Mst_Department ORDER BY Dept_Name")
    return JsonResponse({
        "companies": companies,
        "depts": depts,
    })


@require_GET
def listings_staff_api(request):
    from .analytics.listings import get_staff_listing
    g = request.GET
    page      = g.get("page")
    page_size = g.get("page_size")
    data = get_staff_listing(
        page=int(page) if page and page.isdigit() else None,
        page_size=int(page_size) if page_size and page_size.isdigit() else None,
        company=g.get("company") or None,
        dept=g.get("dept") or None,
        status=g.get("status") or None,
        gender=g.get("gender") or None,
        search=g.get("search") or None,
        sort=g.get("sort") or None,
        sort_dir=g.get("sort_dir") or None,
    )
    return JsonResponse(data)


@require_permission("listings.invoices", "view")
def listings_invoices_page(request):
    return render(request, "chatbot/listings/invoices.html",
                  _listing_context(request, "listings.invoices"))


@require_GET
def listings_invoices_meta_api(request):
    from .analytics.tools import _query
    years   = _query("""
        SELECT DISTINCT YEAR(Invoice_Dt) AS yr
        FROM eos_Invoice_Hdr
        WHERE COALESCE(Marked_As_Deleted, '') != 'Y' AND Invoice_Amt IS NOT NULL
        ORDER BY yr DESC
    """)
    vendors = _query("""
        SELECT DISTINCT v.Vendor_Name AS name
        FROM eos_Invoice_Hdr i
        JOIN Mstx_Vendor v ON i.Vendor_Id = v.Vendor_Id
        WHERE COALESCE(i.Marked_As_Deleted, '') != 'Y' AND i.Invoice_Amt IS NOT NULL
        ORDER BY v.Vendor_Name
    """)
    return JsonResponse({
        "years":   [r["yr"] for r in years],
        "vendors": [r["name"] for r in vendors],
    })


@require_GET
def listings_invoices_api(request):
    from .analytics.listings import get_invoice_listing
    g = request.GET
    page      = g.get("page")
    page_size = g.get("page_size")
    year      = g.get("year")
    data = get_invoice_listing(
        page=int(page) if page and page.isdigit() else None,
        page_size=int(page_size) if page_size and page_size.isdigit() else None,
        year=int(year) if year and year.isdigit() else None,
        vendor=g.get("vendor") or None,
        search=g.get("search") or None,
        sort=g.get("sort") or None,
        sort_dir=g.get("sort_dir") or None,
    )
    return JsonResponse(data)


_preview_cache: dict = {}  # key -> pdf bytes, ephemeral in-memory store


@require_GET
def pdf_template_get(request, report_name):
    """Return a template JSON so the designer can load it."""
    from .pdf_reports import load_template
    rig = request.GET.get("rig") or None
    try:
        template = load_template(report_name, rig=rig)
        return JsonResponse(template)
    except FileNotFoundError as e:
        return JsonResponse({"error": str(e)}, status=404)


@csrf_exempt
def pdf_template_save(request, report_name):
    """Save a designer-exported template JSON to disk."""
    if request.method not in ("POST", "PUT"):
        return JsonResponse({"error": "use POST or PUT"}, status=405)
    from .pdf_reports import save_template
    import json as _json
    rig = request.GET.get("rig") or None
    try:
        template = _json.loads(request.body)
        path = save_template(report_name, template, rig=rig)
        return JsonResponse({"saved": str(path)})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)

@csrf_exempt
def reportbro_preview(request):
    """
    ReportBro designer preview protocol:
      PUT  → generate PDF, store with a key, return plain text "key:XXXX"
      GET  → ?key=XXXX&outputFormat=pdf → return stored PDF bytes
    """
    cors_headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, PUT, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    }

    def _cors(response):
        for k, v in cors_headers.items():
            response[k] = v
        return response

    if request.method == "OPTIONS":
        return _cors(HttpResponse(status=200))

    if request.method == "GET":
        key = request.GET.get("key", "")
        pdf = _preview_cache.pop(key, None)
        if pdf is None:
            return _cors(HttpResponse("not found", status=404))
        return _cors(HttpResponse(bytes(pdf), content_type="application/pdf"))

    if request.method == "PUT":
        import json as _json
        from reportbro import Report, ReportBroError
        try:
            body = _json.loads(request.body)
        except Exception:
            return _cors(HttpResponse("invalid JSON", status=400))

        template = body.get("report")
        data     = body.get("data", {})
        try:
            report = Report(template, data, is_test_data=True)
            if report.errors:
                return _cors(JsonResponse({"errors": report.errors}, status=400))
            pdf = bytes(report.generate_pdf())
            import uuid
            key = str(uuid.uuid4())
            _preview_cache[key] = pdf
            return _cors(HttpResponse(f"key:{key}", content_type="text/plain"))
        except ReportBroError as e:
            return _cors(JsonResponse({"error": str(e)}, status=400))

    return _cors(HttpResponse("method not allowed", status=405))


@require_permission("listings.certificates", "view")
def listings_certificates_page(request):
    return render(request, "chatbot/listings/certificates.html",
                  _listing_context(request, "listings.certificates"))


@require_permission("listings.users", "view")
def listings_users_page(request):
    return render(request, "chatbot/listings/users.html",
                  _listing_context(request, "listings.users"))


@require_GET
def listings_users_api(request):
    g           = request.GET
    q           = g.get("q", "").strip()
    active_fil  = g.get("active", "")
    type_fil    = g.get("type", "")
    page        = max(1, int(g.get("page", 1) or 1))
    per_page    = min(max(1, int(g.get("page_size", 50) or 50)), 200)
    offset      = (page - 1) * per_page

    # Whitelist of sortable columns
    SORT_COLS = {
        "user_id":   "u.USER_ID",
        "name":      "u.USER_NAME",
        "login_id":  "u.USER_LOGIN_ID",
        "email":     "u.USER_EMAIL",
        "dept_name": "d.Dept_Dispname",
        "user_type": "u.USER_TYPE_ID",
        "active":    "u.USER_ACTIVE",
    }
    sort_key = g.get("sort", "name")
    sort_col = SORT_COLS.get(sort_key, "u.USER_NAME")
    sort_dir = "DESC" if g.get("sort_dir", "asc").lower() == "desc" else "ASC"

    where_parts = []
    params      = []

    if q:
        where_parts.append("(u.USER_NAME LIKE %s OR u.USER_LOGIN_ID LIKE %s)")
        like = f"%{q}%"
        params += [like, like]
    if active_fil == "Y":
        where_parts.append("u.USER_ACTIVE = 'Y'")
    elif active_fil == "N":
        where_parts.append("(u.USER_ACTIVE != 'Y' OR u.USER_ACTIVE IS NULL)")
    if type_fil:
        where_parts.append("u.USER_TYPE_ID = %s")
        params.append(type_fil)

    where = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""

    sql_count = f"SELECT COUNT(*) FROM Mst_user u {where}"
    sql_rows  = f"""
        SELECT u.USER_ID, u.USER_NAME, u.USER_LOGIN_ID, u.USER_EMAIL,
               u.USER_ACTIVE, u.USER_TYPE_ID, d.Dept_Dispname
        FROM Mst_user u
        LEFT JOIN Mst_Department d ON d.Dept_Id = u.DEPT_ID
        {where}
        ORDER BY {sort_col} {sort_dir}
        LIMIT %s OFFSET %s
    """

    from django.db import connections
    import math
    with connections["default"].cursor() as cursor:
        dbq(cursor, sql_count, params)
        total = cursor.fetchone()[0]
        dbq(cursor, sql_rows, params + [per_page, offset])
        rows = cursor.fetchall()

    return JsonResponse({
        "total":       total,
        "total_pages": max(1, math.ceil(total / per_page)),
        "page":        page,
        "page_size":   per_page,
        "rows": [
            {
                "user_id":   r[0],
                "name":      r[1] or "",
                "login_id":  r[2] or "",
                "email":     r[3] or "",
                "active":    r[4] or "",
                "user_type": r[5] or "",
                "dept_name": r[6] or "",
            }
            for r in rows
        ],
    })


@require_GET
@require_permission("listings.users", "export")
def listings_users_export(request):
    from django.db import connections
    g = request.GET
    q           = g.get("q", "").strip()
    active_fil  = g.get("active", "")
    type_fil    = g.get("type", "")
    sort_key    = g.get("sort", "name")
    sort_dir_raw = g.get("sort_dir", "asc")
    SORT_COLS = {
        "user_id":   "u.USER_ID",
        "name":      "u.USER_NAME",
        "login_id":  "u.USER_LOGIN_ID",
        "email":     "u.USER_EMAIL",
        "dept_name": "d.Dept_Dispname",
        "user_type": "u.USER_TYPE_ID",
        "active":    "u.USER_ACTIVE",
    }
    sort_col = SORT_COLS.get(sort_key, "u.USER_NAME")
    sort_dir = "DESC" if sort_dir_raw.lower() == "desc" else "ASC"
    where_parts, params = [], []
    if q:
        where_parts.append("(u.USER_NAME LIKE %s OR u.USER_LOGIN_ID LIKE %s)")
        like = f"%{q}%"
        params += [like, like]
    if active_fil == "Y":
        where_parts.append("u.USER_ACTIVE = 'Y'")
    elif active_fil == "N":
        where_parts.append("(u.USER_ACTIVE != 'Y' OR u.USER_ACTIVE IS NULL)")
    if type_fil:
        where_parts.append("u.USER_TYPE_ID = %s")
        params.append(type_fil)
    where = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""
    sql = f"""
        SELECT u.USER_ID, u.USER_NAME, u.USER_LOGIN_ID, u.USER_EMAIL,
               u.USER_ACTIVE, u.USER_TYPE_ID, d.Dept_Dispname
        FROM Mst_user u
        LEFT JOIN Mst_Department d ON d.Dept_Id = u.DEPT_ID
        {where}
        ORDER BY {sort_col} {sort_dir}
    """
    with connections["default"].cursor() as cursor:
        dbq(cursor, sql, params)
        rows = [
            {
                "user_id": r[0], "name": r[1] or "", "login_id": r[2] or "",
                "email": r[3] or "", "active": "Yes" if r[4] == "Y" else "No",
                "user_type": r[5] or "", "department": r[6] or "",
            }
            for r in cursor.fetchall()
        ]
    _audit.record_action(request, "export", "listings.users", None, "%d row(s)" % len(rows), None)
    return _csv_response(rows, "users.csv")


@require_GET
def listings_certificates_meta_api(request):
    from .analytics.tools import _query
    cert_types = _query("""
        SELECT DISTINCT mc.cert_name AS name
        FROM eos_Fs_Certificates fc
        JOIN Mst_Cert mc ON fc.Cert_Id = mc.cert_id
        WHERE fc.Fs_Cert_Active = 'Y' AND fc.Fs_Cert_Valid_Till IS NOT NULL
        ORDER BY mc.cert_name
    """)
    return JsonResponse({"cert_types": [r["name"] for r in cert_types]})


@require_GET
def listings_certificates_api(request):
    from .analytics.listings import get_certificate_listing
    g = request.GET
    page      = g.get("page")
    page_size = g.get("page_size")
    data = get_certificate_listing(
        page=int(page) if page and page.isdigit() else None,
        page_size=int(page_size) if page_size and page_size.isdigit() else None,
        status=g.get("status") or None,
        cert_type=g.get("cert_type") or None,
        search=g.get("search") or None,
        sort=g.get("sort") or None,
        sort_dir=g.get("sort_dir") or None,
    )
    return JsonResponse(data)


# ── Listing CSV Exports ───────────────────────────────────────────────────────

@require_GET
@require_permission("listings.incidents", "export")
def listings_incidents_export(request):
    from .analytics.listings import get_incident_listing, EXPORT_PAGE_SIZE
    g = request.GET
    data = get_incident_listing(
        page=1, page_size=EXPORT_PAGE_SIZE,
        rig=g.get("rig") or None,
        year=int(g["year"]) if g.get("year","").isdigit() else None,
        severity=g.get("severity") or None,
        person_injured=g.get("injured") or None,
        incident_type=g.get("incident_type") or None,
        search=g.get("search") or None,
    )
    rows = [{k: v for k, v in r.items() if k not in ("description","id")}
            for r in data.get("rows", [])]
    _audit.record_action(request, "export", "listings.incidents", None, "%d row(s)" % len(rows), None)
    return _csv_response(rows, "incidents.csv")


@require_GET
@require_permission("listings.hazard_cards", "export")
def listings_hazard_cards_export(request):
    from .analytics.listings import get_hazard_card_listing, EXPORT_PAGE_SIZE
    g = request.GET
    data = get_hazard_card_listing(
        page=1, page_size=EXPORT_PAGE_SIZE,
        rig=g.get("rig") or None,
        year=int(g["year"]) if g.get("year","").isdigit() else None,
        hazard_type=g.get("hazard_type") or None,
        status=g.get("status") or None,
        tfs=g.get("tfs") or None,
        search=g.get("search") or None,
    )
    rows = [{k: v for k, v in r.items() if k not in ("id",)}
            for r in data.get("rows", [])]
    _audit.record_action(request, "export", "listings.hazard_cards", None, "%d row(s)" % len(rows), None)
    return _csv_response(rows, "hazard_cards.csv")


@require_GET
@require_permission("listings.employees", "export")
def listings_employees_export(request):
    from .analytics.listings import get_employee_listing, EXPORT_PAGE_SIZE
    g = request.GET
    data = get_employee_listing(
        page=1, page_size=EXPORT_PAGE_SIZE,
        rig=g.get("rig") or None,
        rank=g.get("rank") or None,
        category=g.get("category") or None,
        emp_type=g.get("emp_type") or None,
        status=g.get("status") or None,
        gender=g.get("gender") or None,
        search=g.get("search") or None,
    )
    rows = [{k: v for k, v in r.items() if k not in ("id",)}
            for r in data.get("rows", [])]
    _audit.record_action(request, "export", "listings.employees", None, "%d row(s)" % len(rows), None)
    return _csv_response(rows, "employees.csv")


@require_GET
@require_permission("listings.staff", "export")
def listings_staff_export(request):
    from .analytics.listings import get_staff_listing, EXPORT_PAGE_SIZE
    g = request.GET
    data = get_staff_listing(
        page=1, page_size=EXPORT_PAGE_SIZE,
        company=g.get("company") or None,
        dept=g.get("dept") or None,
        status=g.get("status") or None,
        gender=g.get("gender") or None,
        search=g.get("search") or None,
    )
    rows = [{k: v for k, v in r.items() if k not in ("id",)}
            for r in data.get("rows", [])]
    _audit.record_action(request, "export", "listings.staff", None, "%d row(s)" % len(rows), None)
    return _csv_response(rows, "staff.csv")


@require_GET
@require_permission("listings.crew_rotations", "export")
def listings_crew_rotations_export(request):
    from .analytics.listings import get_crew_rotation_listing, EXPORT_PAGE_SIZE
    g = request.GET
    data = get_crew_rotation_listing(
        page=1, page_size=EXPORT_PAGE_SIZE,
        rig=g.get("rig") or None,
        rank=g.get("rank") or None,
        status=g.get("status") or None,
        search=g.get("search") or None,
    )
    rows = [{k: v for k, v in r.items() if k not in ("id",)}
            for r in data.get("rows", [])]
    _audit.record_action(request, "export", "listings.crew_rotations", None, "%d row(s)" % len(rows), None)
    return _csv_response(rows, "crew_rotations.csv")


@require_GET
@require_permission("listings.invoices", "export")
def listings_invoices_export(request):
    from .analytics.listings import get_invoice_listing, EXPORT_PAGE_SIZE
    g = request.GET
    data = get_invoice_listing(
        page=1, page_size=EXPORT_PAGE_SIZE,
        year=int(g["year"]) if g.get("year","").isdigit() else None,
        vendor=g.get("vendor") or None,
        search=g.get("search") or None,
    )
    rows = [{k: v for k, v in r.items() if k not in ("id",)}
            for r in data.get("rows", [])]
    _audit.record_action(request, "export", "listings.invoices", None, "%d row(s)" % len(rows), None)
    return _csv_response(rows, "invoices.csv")


@require_GET
@require_permission("listings.certificates", "export")
def listings_certificates_export(request):
    from .analytics.listings import get_certificate_listing, EXPORT_PAGE_SIZE
    g = request.GET
    data = get_certificate_listing(
        page=1, page_size=EXPORT_PAGE_SIZE,
        status=g.get("status") or None,
        cert_type=g.get("cert_type") or None,
        search=g.get("search") or None,
    )
    rows = [{k: v for k, v in r.items() if k not in ("id",)}
            for r in data.get("rows", [])]
    _audit.record_action(request, "export", "listings.certificates", None, "%d row(s)" % len(rows), None)
    return _csv_response(rows, "certificates.csv")


# ── Chat API ───────────────────────────────────────────────────────────────────

@csrf_exempt
@require_POST
def chat_api(request, conversation_id):
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    question = body.get("question", "").strip()
    if not question:
        return JsonResponse({"error": "Question cannot be empty"}, status=400)

    convo = get_object_or_404(Conversation.objects.using("chathistory"), id=conversation_id)

    # Load history from DB
    from chatbot.rag.config import CHAT_HISTORY_WINDOW
    prior_messages = list(convo.messages.using("chathistory").all())

    # Trim to the last N messages for the LLM — keeps context window manageable
    # for Ollama models while preserving full history in the DB.
    lc_window = prior_messages[-CHAT_HISTORY_WINDOW:] if CHAT_HISTORY_WINDOW and len(prior_messages) > CHAT_HISTORY_WINDOW else prior_messages
    chat_history = _build_lc_history(lc_window)

    # Auto-title the conversation on first message
    if not prior_messages:
        convo.title = _auto_title(question)
        convo.save(using="chathistory")

    # Save user message
    Message.objects.using("chathistory").create(
        conversation=convo,
        role=Message.ROLE_USER,
        content=question,
    )

    # ── Analytics path: deterministic tool routing ────────────────────────────
    analytics_context = _extract_analytics_context(prior_messages)
    analytics_result  = analytics_route(question, context=analytics_context)
    if analytics_result is not None:
        try:
            chain = _get_chain()
            narration_prompt = (
                f"The user asked: {question}\n\n"
                f"Here is the EXACT data retrieved from the operational database:\n"
                f"{json.dumps(analytics_result, default=str, indent=2)}\n\n"
                f"STRICT RULES — you MUST follow these:\n"
                f"1. Only use the numbers and facts in the data above. Do NOT invent, estimate, or infer any figures.\n"
                f"2. If a field is null or missing, say it is not available. Do NOT guess.\n"
                f"3. Do NOT mention SQL, databases, tools, or JSON.\n"
                f"4. Be concise. Answer the user's question directly using only the provided data."
            )
            result = chain.invoke({"input": narration_prompt, "chat_history": chat_history})
            answer = result["answer"]
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

        dashboard_data = None
        if analytics_result.get("display") == "dashboard":
            dashboard_data = analytics_result

        Message.objects.using("chathistory").create(
            conversation=convo,
            role=Message.ROLE_ASSISTANT,
            content=answer,
            sources=[],
        )
        convo.save(using="chathistory", update_fields=["updated_at"])
        return JsonResponse({
            "answer": answer,
            "sources": [],
            "title": convo.title,
            "dashboard_data": dashboard_data,
        }, encoder=_UUIDDateEncoder)

    # ── RAG path: retrieval-augmented generation ───────────────────────────────
    try:
        chain = _get_chain()
        result = chain.invoke({"input": question, "chat_history": chat_history})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    # Build deduplicated sources with page numbers
    file_pages: dict[str, set[int]] = {}
    for doc in result.get("context", []):
        raw_source = doc.metadata.get("source", "")
        page = doc.metadata.get("page")
        filename = Path(raw_source).name if raw_source else "Unknown"
        file_pages.setdefault(filename, set())
        if isinstance(page, int):
            file_pages[filename].add(page + 1)

    sources = [
        {"file": filename, "pages": sorted(pages)}
        for filename, pages in file_pages.items()
    ]

    # Save assistant message
    Message.objects.using("chathistory").create(
        conversation=convo,
        role=Message.ROLE_ASSISTANT,
        content=result["answer"],
        sources=sources,
    )

    # Touch updated_at so sidebar sorts correctly
    convo.save(using="chathistory", update_fields=["updated_at"])

    return JsonResponse({
        "answer": result["answer"],
        "sources": sources,
        "title": convo.title,
    })


# ── Contractor Master ─────────────────────────────────────────────────────────



@require_permission("masters.contractors", "view")
def contractor_master_page(request):
    return render(request, "chatbot/masters/contractor.html")


@require_GET
def contractor_list_api(request):
    from django.db import connections
    q      = request.GET.get("q", "").strip()
    offset = max(0, int(request.GET.get("offset", 0)))
    limit  = min(200, max(1, int(request.GET.get("limit", 200))))
    with connections["default"].cursor() as cursor:
        dbq(cursor, """
            SELECT Contractor_Id, Contractor_Name
            FROM eos_Mst_Contractor
            WHERE Contractor_Name LIKE %s
            ORDER BY Contractor_Name
            LIMIT %s OFFSET %s
        """, [f"%{q}%", limit, offset])
        cols = [c[0] for c in cursor.description]
        rows = [dict(zip(cols, row)) for row in cursor.fetchall()]
    return JsonResponse({"results": rows})


@require_GET
def contractor_get_api(request, contractor_id):
    from django.db import connections
    with connections["default"].cursor() as cursor:
        dbq(cursor, """
            SELECT Contractor_Id, Contractor_Name
            FROM eos_Mst_Contractor
            WHERE Contractor_Id=%s
        """, [contractor_id])
        cols = [c[0] for c in cursor.description]
        row  = cursor.fetchone()
    if not row:
        return JsonResponse({"error": "Not found"}, status=404)
    return JsonResponse(dict(zip(cols, row)))


@csrf_exempt
def contractor_save_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    _a = _get_access(request)
    if not _a["is_admin"]:
        try:
            _bpk = json.loads(request.body)
            _has_id = bool(_bpk.get("contractor_id"))
        except Exception:
            _has_id = False
        _pact = "edit" if _has_id else "add"
        if not _a["perms"].get("masters.contractors", {}).get(_pact):
            return JsonResponse({"error": "Permission denied"}, status=403)
    from django.db import connections
    import json
    body            = json.loads(request.body)
    contractor_id   = body.get("contractor_id")
    contractor_name = (body.get("contractor_name") or "").strip()
    if not contractor_name:
        return JsonResponse({"error": "Contractor name is required"}, status=400)
    now = datetime.now()
    _uid = _audit.ops_user_id(request)
    with connections["default"].cursor() as cursor:
        _before = _audit.snap(cursor, "masters.contractors", contractor_id)
        if contractor_id:
            dbq(cursor, """
                UPDATE eos_Mst_Contractor
                SET Contractor_Name=%s, Mod_User_Id=%s, Mod_Dt=%s
                WHERE Contractor_Id=%s
            """, [contractor_name, _uid, now, contractor_id])
        else:
            dbq(cursor, "SELECT COALESCE(MAX(Contractor_Id),0)+1 FROM eos_Mst_Contractor")
            new_id = cursor.fetchone()[0]
            dbq(cursor, """
                INSERT INTO eos_Mst_Contractor
                    (Contractor_Id, Contractor_Name, Cr_User_Id, Cr_Dt)
                VALUES (%s, %s, %s, %s)
            """, [new_id, contractor_name, _uid, now])
            contractor_id = new_id
        _audit.record_save(request, cursor, "masters.contractors", contractor_id, _before)
    return JsonResponse({"success": True, "contractor_id": contractor_id})


@require_GET
def contractor_check_delete_api(request, contractor_id):
    return JsonResponse({"can_delete": True, "references": []})


@csrf_exempt
def contractor_delete_api(request, contractor_id):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    _a = _get_access(request)
    if not _a["is_admin"] and not _a["perms"].get("masters.contractors", {}).get("delete"):
        return JsonResponse({"error": "Permission denied"}, status=403)
    from django.db import connections
    with connections["default"].cursor() as cursor:
        _before = _audit.snap(cursor, "masters.contractors", contractor_id)
        dbq(cursor, "DELETE FROM eos_Mst_Contractor WHERE Contractor_Id=%s", [contractor_id])
    _audit.record_delete(request, "masters.contractors", contractor_id, _before)
    return JsonResponse({"success": True})


# ── Rig Operation Master ──────────────────────────────────────────────────────

@require_permission("masters.rig_operations", "view")
def rig_operation_page(request):
    return render(request, "chatbot/masters/rig_operation.html")


@require_GET
def rig_operation_list_api(request):
    from django.db import connections
    q      = request.GET.get("q", "").strip()
    offset = max(0, int(request.GET.get("offset", 0)))
    limit  = min(200, max(1, int(request.GET.get("limit", 200))))
    with connections["default"].cursor() as cursor:
        dbq(cursor, """
            SELECT Rig_Operation_Id, Rig_Operation_Name
            FROM eos_Mst_Rig_Operation
            WHERE Rig_Operation_Name LIKE %s
            ORDER BY Rig_Operation_Name
            LIMIT %s OFFSET %s
        """, [f"%{q}%", limit, offset])
        cols = [c[0] for c in cursor.description]
        rows = [dict(zip(cols, row)) for row in cursor.fetchall()]
    return JsonResponse({"results": rows})


@require_GET
def rig_operation_get_api(request, op_id):
    from django.db import connections
    with connections["default"].cursor() as cursor:
        dbq(cursor, """
            SELECT Rig_Operation_Id, Rig_Operation_Name
            FROM eos_Mst_Rig_Operation
            WHERE Rig_Operation_Id=%s
        """, [op_id])
        cols = [c[0] for c in cursor.description]
        row  = cursor.fetchone()
    if not row:
        return JsonResponse({"error": "Not found"}, status=404)
    return JsonResponse(dict(zip(cols, row)))


@csrf_exempt
def rig_operation_save_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    _a = _get_access(request)
    if not _a["is_admin"]:
        try:
            _bpk = json.loads(request.body)
            _has_id = bool(_bpk.get("rig_operation_id"))
        except Exception:
            _has_id = False
        _pact = "edit" if _has_id else "add"
        if not _a["perms"].get("masters.rig_operations", {}).get(_pact):
            return JsonResponse({"error": "Permission denied"}, status=403)
    from django.db import connections
    import json
    body          = json.loads(request.body)
    op_id         = body.get("rig_operation_id")
    op_name       = (body.get("rig_operation_name") or "").strip()
    if not op_name:
        return JsonResponse({"error": "Operation name is required"}, status=400)
    now = datetime.now()
    _uid = _audit.ops_user_id(request)
    with connections["default"].cursor() as cursor:
        _before = _audit.snap(cursor, "masters.rig_operations", op_id)
        if op_id:
            dbq(cursor, """
                UPDATE eos_Mst_Rig_Operation
                SET Rig_Operation_Name=%s, Mod_User_Id=%s, Mod_Dt=%s
                WHERE Rig_Operation_Id=%s
            """, [op_name, _uid, now, op_id])
        else:
            dbq(cursor, "SELECT COALESCE(MAX(Rig_Operation_Id),0)+1 FROM eos_Mst_Rig_Operation")
            new_id = cursor.fetchone()[0]
            dbq(cursor, """
                INSERT INTO eos_Mst_Rig_Operation
                    (Rig_Operation_Id, Rig_Operation_Name, Cr_User_Id, Cr_Dt)
                VALUES (%s, %s, %s, %s)
            """, [new_id, op_name, _uid, now])
            op_id = new_id
        _audit.record_save(request, cursor, "masters.rig_operations", op_id, _before)
    return JsonResponse({"success": True, "rig_operation_id": op_id})


@require_GET
def rig_operation_check_delete_api(request, op_id):
    return JsonResponse({"can_delete": True, "references": []})


@csrf_exempt
def rig_operation_delete_api(request, op_id):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    _a = _get_access(request)
    if not _a["is_admin"] and not _a["perms"].get("masters.rig_operations", {}).get("delete"):
        return JsonResponse({"error": "Permission denied"}, status=403)
    from django.db import connections
    with connections["default"].cursor() as cursor:
        _before = _audit.snap(cursor, "masters.rig_operations", op_id)
        dbq(cursor, "DELETE FROM eos_Mst_Rig_Operation WHERE Rig_Operation_Id=%s", [op_id])
    _audit.record_delete(request, "masters.rig_operations", op_id, _before)
    return JsonResponse({"success": True})


# ── Contact Exposure Type Master ──────────────────────────────────────────────

@require_permission("masters.contact_exposure_types", "view")
def contact_exposure_type_page(request):
    return render(request, "chatbot/masters/contact_exposure_type.html")


@require_GET
def contact_exposure_type_list_api(request):
    from django.db import connections
    q      = request.GET.get("q", "").strip()
    offset = max(0, int(request.GET.get("offset", 0)))
    limit  = min(200, max(1, int(request.GET.get("limit", 200))))
    with connections["default"].cursor() as cursor:
        dbq(cursor, """
            SELECT Contact_Expo_Type_Id, Contact_Expo_Type_Name
            FROM eos_Mst_Contact_Exposure_Type
            WHERE Contact_Expo_Type_Name LIKE %s
            ORDER BY Contact_Expo_Type_Name
            LIMIT %s OFFSET %s
        """, [f"%{q}%", limit, offset])
        cols = [c[0] for c in cursor.description]
        rows = [dict(zip(cols, row)) for row in cursor.fetchall()]
    return JsonResponse({"results": rows})


@require_GET
def contact_exposure_type_get_api(request, type_id):
    from django.db import connections
    with connections["default"].cursor() as cursor:
        dbq(cursor, """
            SELECT Contact_Expo_Type_Id, Contact_Expo_Type_Name
            FROM eos_Mst_Contact_Exposure_Type
            WHERE Contact_Expo_Type_Id=%s
        """, [type_id])
        cols = [c[0] for c in cursor.description]
        row  = cursor.fetchone()
    if not row:
        return JsonResponse({"error": "Not found"}, status=404)
    return JsonResponse(dict(zip(cols, row)))


@csrf_exempt
def contact_exposure_type_save_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    _a = _get_access(request)
    if not _a["is_admin"]:
        try:
            _bpk = json.loads(request.body)
            _has_id = bool(_bpk.get("contact_expo_type_id"))
        except Exception:
            _has_id = False
        _pact = "edit" if _has_id else "add"
        if not _a["perms"].get("masters.contact_exposure_types", {}).get(_pact):
            return JsonResponse({"error": "Permission denied"}, status=403)
    from django.db import connections
    import json
    body      = json.loads(request.body)
    type_id   = body.get("contact_expo_type_id")
    type_name = (body.get("contact_expo_type_name") or "").strip()
    if not type_name:
        return JsonResponse({"error": "Type name is required"}, status=400)
    now = datetime.now()
    _uid = _audit.ops_user_id(request)
    with connections["default"].cursor() as cursor:
        _before = _audit.snap(cursor, "masters.contact_exposure_types", type_id)
        if type_id:
            dbq(cursor, """
                UPDATE eos_Mst_Contact_Exposure_Type
                SET Contact_Expo_Type_Name=%s, Mod_User_Id=%s, Mod_Dt=%s
                WHERE Contact_Expo_Type_Id=%s
            """, [type_name, _uid, now, type_id])
        else:
            dbq(cursor, "SELECT COALESCE(MAX(Contact_Expo_Type_Id),0)+1 FROM eos_Mst_Contact_Exposure_Type")
            new_id = cursor.fetchone()[0]
            dbq(cursor, """
                INSERT INTO eos_Mst_Contact_Exposure_Type
                    (Contact_Expo_Type_Id, Contact_Expo_Type_Name, Cr_User_Id, Cr_Dt)
                VALUES (%s, %s, %s, %s)
            """, [new_id, type_name, _uid, now])
            type_id = new_id
        _audit.record_save(request, cursor, "masters.contact_exposure_types", type_id, _before)
    return JsonResponse({"success": True, "contact_expo_type_id": type_id})


@require_GET
def contact_exposure_type_check_delete_api(request, type_id):
    return JsonResponse({"can_delete": True, "references": []})


@csrf_exempt
def contact_exposure_type_delete_api(request, type_id):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    _a = _get_access(request)
    if not _a["is_admin"] and not _a["perms"].get("masters.contact_exposure_types", {}).get("delete"):
        return JsonResponse({"error": "Permission denied"}, status=403)
    from django.db import connections
    with connections["default"].cursor() as cursor:
        _before = _audit.snap(cursor, "masters.contact_exposure_types", type_id)
        dbq(cursor, "DELETE FROM eos_Mst_Contact_Exposure_Type WHERE Contact_Expo_Type_Id=%s", [type_id])
    _audit.record_delete(request, "masters.contact_exposure_types", type_id, _before)
    return JsonResponse({"success": True})


# ── Indicator Type Master ─────────────────────────────────────────────────────

_INDICATOR_REPORT_TYPES = ("Leading", "Lagging")


@require_permission("masters.indicator_types", "view")
def indicator_type_page(request):
    return render(request, "chatbot/masters/indicator_type.html")


@require_GET
def indicator_type_list_api(request):
    from django.db import connections
    q      = request.GET.get("q", "").strip()
    offset = max(0, int(request.GET.get("offset", 0)))
    limit  = min(200, max(1, int(request.GET.get("limit", 200))))
    with connections["default"].cursor() as cursor:
        dbq(cursor, """
            SELECT Indicator_Type_Id, Indicator_Type_Name, Report_Type, Indicator_Type_Order
            FROM eos_Mst_Indicator_Type
            WHERE Indicator_Type_Name LIKE %s
            ORDER BY Report_Type, Indicator_Type_Order
            LIMIT %s OFFSET %s
        """, [f"%{q}%", limit, offset])
        cols = [c[0] for c in cursor.description]
        rows = [dict(zip(cols, row)) for row in cursor.fetchall()]
    return JsonResponse({"results": rows})


@require_GET
def indicator_type_get_api(request, type_id):
    from django.db import connections
    with connections["default"].cursor() as cursor:
        dbq(cursor, """
            SELECT Indicator_Type_Id, Indicator_Type_Name, Report_Type, Indicator_Type_Order
            FROM eos_Mst_Indicator_Type
            WHERE Indicator_Type_Id=%s
        """, [type_id])
        cols = [c[0] for c in cursor.description]
        row  = cursor.fetchone()
    if not row:
        return JsonResponse({"error": "Not found"}, status=404)
    return JsonResponse(dict(zip(cols, row)))


@csrf_exempt
def indicator_type_save_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    _a = _get_access(request)
    if not _a["is_admin"]:
        try:
            _bpk = json.loads(request.body)
            _has_id = bool(_bpk.get("indicator_type_id"))
        except Exception:
            _has_id = False
        _pact = "edit" if _has_id else "add"
        if not _a["perms"].get("masters.indicator_types", {}).get(_pact):
            return JsonResponse({"error": "Permission denied"}, status=403)
    from django.db import connections
    import json
    body        = json.loads(request.body)
    type_id     = body.get("indicator_type_id")
    type_name   = (body.get("indicator_type_name") or "").strip()
    report_type = (body.get("report_type") or "").strip()
    if not type_name:
        return JsonResponse({"error": "Indicator type name is required"}, status=400)
    if report_type not in _INDICATOR_REPORT_TYPES:
        return JsonResponse({"error": "Report type must be Leading or Lagging"}, status=400)
    now = datetime.now()
    _uid = _audit.ops_user_id(request)
    with connections["default"].cursor() as cursor:
        _before = _audit.snap(cursor, "masters.indicator_types", type_id)
        if type_id:
            dbq(cursor, """
                UPDATE eos_Mst_Indicator_Type
                SET Indicator_Type_Name=%s, Report_Type=%s, Mod_User_Id=%s, Mod_Dt=%s
                WHERE Indicator_Type_Id=%s
            """, [type_name, report_type, _uid, now, type_id])
        else:
            dbq(cursor, "SELECT COALESCE(MAX(Indicator_Type_Id),0)+1 FROM eos_Mst_Indicator_Type")
            new_id = cursor.fetchone()[0]
            # Order is a per-Report_Type sequence.
            dbq(cursor, "SELECT COALESCE(MAX(Indicator_Type_Order),0)+1 FROM eos_Mst_Indicator_Type WHERE Report_Type=%s", [report_type])
            new_order = cursor.fetchone()[0]
            dbq(cursor, """
                INSERT INTO eos_Mst_Indicator_Type
                    (Indicator_Type_Id, Indicator_Type_Name, Indicator_Type_Order, Report_Type, Cr_User_Id, Cr_Dt)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, [new_id, type_name, new_order, report_type, _uid, now])
            type_id = new_id
        _audit.record_save(request, cursor, "masters.indicator_types", type_id, _before)
    return JsonResponse({"success": True, "indicator_type_id": type_id})


@require_GET
def indicator_type_check_delete_api(request, type_id):
    from django.db import connections
    with connections["default"].cursor() as cursor:
        dbq(cursor, "SELECT COUNT(*) FROM eos_Mst_Indicator_Subtype WHERE Indicator_Type_Id=%s", [type_id])
        n = cursor.fetchone()[0]
    if n:
        return JsonResponse({"can_delete": False, "references": [{"count": n, "label": "Indicator Subtype(s)"}]})
    return JsonResponse({"can_delete": True, "references": []})


@csrf_exempt
def indicator_type_delete_api(request, type_id):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    _a = _get_access(request)
    if not _a["is_admin"] and not _a["perms"].get("masters.indicator_types", {}).get("delete"):
        return JsonResponse({"error": "Permission denied"}, status=403)
    from django.db import connections
    with connections["default"].cursor() as cursor:
        dbq(cursor, "SELECT COUNT(*) FROM eos_Mst_Indicator_Subtype WHERE Indicator_Type_Id=%s", [type_id])
        if cursor.fetchone()[0]:
            return JsonResponse({"error": "Cannot delete: referenced by Indicator Subtypes"}, status=409)
        _before = _audit.snap(cursor, "masters.indicator_types", type_id)
        dbq(cursor, "DELETE FROM eos_Mst_Indicator_Type WHERE Indicator_Type_Id=%s", [type_id])
    _audit.record_delete(request, "masters.indicator_types", type_id, _before)
    return JsonResponse({"success": True})


# ── Indicator Subtype Master ──────────────────────────────────────────────────

@require_permission("masters.indicator_subtypes", "view")
def indicator_subtype_page(request):
    return render(request, "chatbot/masters/indicator_subtype.html")


@require_GET
def indicator_subtype_meta_api(request):
    """Indicator Type options for the dropdown."""
    from django.db import connections
    with connections["default"].cursor() as cursor:
        dbq(cursor, """
            SELECT Indicator_Type_Id, Indicator_Type_Name, Report_Type
            FROM eos_Mst_Indicator_Type
            ORDER BY Report_Type, Indicator_Type_Order
        """)
        cols = [c[0] for c in cursor.description]
        types = [dict(zip(cols, row)) for row in cursor.fetchall()]
    return JsonResponse({"types": types})


@require_GET
def indicator_subtype_list_api(request):
    from django.db import connections
    q      = request.GET.get("q", "").strip()
    offset = max(0, int(request.GET.get("offset", 0)))
    limit  = min(200, max(1, int(request.GET.get("limit", 200))))
    with connections["default"].cursor() as cursor:
        dbq(cursor, """
            SELECT s.Indicator_Subtype_Id, s.Indicator_Type_Id, t.Indicator_Type_Name,
                   t.Report_Type, s.Indicator_Subtype_Name, s.Indicator_Subtype_Order
            FROM eos_Mst_Indicator_Subtype s
            LEFT JOIN eos_Mst_Indicator_Type t ON s.Indicator_Type_Id = t.Indicator_Type_Id
            WHERE s.Indicator_Subtype_Name LIKE %s
            ORDER BY t.Indicator_Type_Name, s.Indicator_Subtype_Order
            LIMIT %s OFFSET %s
        """, [f"%{q}%", limit, offset])
        cols = [c[0] for c in cursor.description]
        rows = [dict(zip(cols, row)) for row in cursor.fetchall()]
    return JsonResponse({"results": rows})


@require_GET
def indicator_subtype_get_api(request, subtype_id):
    from django.db import connections
    with connections["default"].cursor() as cursor:
        dbq(cursor, """
            SELECT Indicator_Subtype_Id, Indicator_Type_Id, Indicator_Subtype_Name, Indicator_Subtype_Order
            FROM eos_Mst_Indicator_Subtype
            WHERE Indicator_Subtype_Id=%s
        """, [subtype_id])
        cols = [c[0] for c in cursor.description]
        row  = cursor.fetchone()
    if not row:
        return JsonResponse({"error": "Not found"}, status=404)
    return JsonResponse(dict(zip(cols, row)))


@csrf_exempt
def indicator_subtype_save_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    _a = _get_access(request)
    if not _a["is_admin"]:
        try:
            _bpk = json.loads(request.body)
            _has_id = bool(_bpk.get("indicator_subtype_id"))
        except Exception:
            _has_id = False
        _pact = "edit" if _has_id else "add"
        if not _a["perms"].get("masters.indicator_subtypes", {}).get(_pact):
            return JsonResponse({"error": "Permission denied"}, status=403)
    from django.db import connections
    import json
    body         = json.loads(request.body)
    subtype_id   = body.get("indicator_subtype_id")
    subtype_name = (body.get("indicator_subtype_name") or "").strip()
    type_id      = body.get("indicator_type_id")
    if not subtype_name:
        return JsonResponse({"error": "Indicator subtype name is required"}, status=400)
    if not type_id:
        return JsonResponse({"error": "Indicator type is required"}, status=400)
    _uid = _audit.ops_user_id(request)
    with connections["default"].cursor() as cursor:
        _before = _audit.snap(cursor, "masters.indicator_subtypes", subtype_id)
        dbq(cursor, "SELECT COUNT(*) FROM eos_Mst_Indicator_Type WHERE Indicator_Type_Id=%s", [type_id])
        if not cursor.fetchone()[0]:
            return JsonResponse({"error": "Selected indicator type does not exist"}, status=400)
        now = datetime.now()
        if subtype_id:
            dbq(cursor, """
                UPDATE eos_Mst_Indicator_Subtype
                SET Indicator_Subtype_Name=%s, Indicator_Type_Id=%s, Mod_User_Id=%s, Mod_Dt=%s
                WHERE Indicator_Subtype_Id=%s
            """, [subtype_name, type_id, _uid, now, subtype_id])
        else:
            dbq(cursor, "SELECT COALESCE(MAX(Indicator_Subtype_Id),0)+1 FROM eos_Mst_Indicator_Subtype")
            new_id = cursor.fetchone()[0]
            # Order is a per-Indicator_Type sequence.
            dbq(cursor, "SELECT COALESCE(MAX(Indicator_Subtype_Order),0)+1 FROM eos_Mst_Indicator_Subtype WHERE Indicator_Type_Id=%s", [type_id])
            new_order = cursor.fetchone()[0]
            dbq(cursor, """
                INSERT INTO eos_Mst_Indicator_Subtype
                    (Indicator_Subtype_Id, Indicator_Type_Id, Indicator_Subtype_Name, Indicator_Subtype_Order, Cr_User_Id, Cr_Dt)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, [new_id, type_id, subtype_name, new_order, _uid, now])
            subtype_id = new_id
        _audit.record_save(request, cursor, "masters.indicator_subtypes", subtype_id, _before)
    return JsonResponse({"success": True, "indicator_subtype_id": subtype_id})


@require_GET
def indicator_subtype_check_delete_api(request, subtype_id):
    from django.db import connections
    refs = []
    with connections["default"].cursor() as cursor:
        dbq(cursor, "SELECT COUNT(*) FROM eos_Leading_Indicators_Dtl WHERE Indicator_Subtype_Id=%s", [subtype_id])
        n = cursor.fetchone()[0]
        if n:
            refs.append({"count": n, "label": "Leading Indicator record(s)"})
        dbq(cursor, "SELECT COUNT(*) FROM eos_Lagging_Indicators_Dtl WHERE Indicator_Subtype_Id=%s", [subtype_id])
        n = cursor.fetchone()[0]
        if n:
            refs.append({"count": n, "label": "Lagging Indicator record(s)"})
    return JsonResponse({"can_delete": not refs, "references": refs})


@csrf_exempt
def indicator_subtype_delete_api(request, subtype_id):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    _a = _get_access(request)
    if not _a["is_admin"] and not _a["perms"].get("masters.indicator_subtypes", {}).get("delete"):
        return JsonResponse({"error": "Permission denied"}, status=403)
    from django.db import connections
    with connections["default"].cursor() as cursor:
        dbq(cursor, "SELECT COUNT(*) FROM eos_Leading_Indicators_Dtl WHERE Indicator_Subtype_Id=%s", [subtype_id])
        leading = cursor.fetchone()[0]
        dbq(cursor, "SELECT COUNT(*) FROM eos_Lagging_Indicators_Dtl WHERE Indicator_Subtype_Id=%s", [subtype_id])
        lagging = cursor.fetchone()[0]
        if leading or lagging:
            return JsonResponse({"error": "Cannot delete: referenced by Indicator records"}, status=409)
        _before = _audit.snap(cursor, "masters.indicator_subtypes", subtype_id)
        dbq(cursor, "DELETE FROM eos_Mst_Indicator_Subtype WHERE Indicator_Subtype_Id=%s", [subtype_id])
    _audit.record_delete(request, "masters.indicator_subtypes", subtype_id, _before)
    return JsonResponse({"success": True})


# ── Parts Of Body Master (add / edit only — no delete, widely referenced) ──────

@require_permission("masters.parts_of_body", "view")
def parts_of_body_page(request):
    return render(request, "chatbot/masters/parts_of_body.html")


@require_GET
def parts_of_body_list_api(request):
    from django.db import connections
    q      = request.GET.get("q", "").strip()
    offset = max(0, int(request.GET.get("offset", 0)))
    limit  = min(200, max(1, int(request.GET.get("limit", 200))))
    with connections["default"].cursor() as cursor:
        dbq(cursor, """
            SELECT Part_Of_Body_Id, Part_Of_Body_Name
            FROM eos_Mst_Parts_Of_Body
            WHERE Part_Of_Body_Name LIKE %s
            ORDER BY Part_Of_Body_Name
            LIMIT %s OFFSET %s
        """, [f"%{q}%", limit, offset])
        cols = [c[0] for c in cursor.description]
        rows = [dict(zip(cols, row)) for row in cursor.fetchall()]
    return JsonResponse({"results": rows})


@require_GET
def parts_of_body_get_api(request, part_id):
    from django.db import connections
    with connections["default"].cursor() as cursor:
        dbq(cursor, """
            SELECT Part_Of_Body_Id, Part_Of_Body_Name
            FROM eos_Mst_Parts_Of_Body
            WHERE Part_Of_Body_Id=%s
        """, [part_id])
        cols = [c[0] for c in cursor.description]
        row  = cursor.fetchone()
    if not row:
        return JsonResponse({"error": "Not found"}, status=404)
    return JsonResponse(dict(zip(cols, row)))


@csrf_exempt
def parts_of_body_save_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    _a = _get_access(request)
    if not _a["is_admin"]:
        try:
            _bpk = json.loads(request.body)
            _has_id = bool(_bpk.get("part_of_body_id"))
        except Exception:
            _has_id = False
        _pact = "edit" if _has_id else "add"
        if not _a["perms"].get("masters.parts_of_body", {}).get(_pact):
            return JsonResponse({"error": "Permission denied"}, status=403)
    from django.db import connections
    import json
    body      = json.loads(request.body)
    part_id   = body.get("part_of_body_id")
    part_name = (body.get("part_of_body_name") or "").strip()
    if not part_name:
        return JsonResponse({"error": "Parts Of Body is required"}, status=400)
    now = datetime.now()
    _uid = _audit.ops_user_id(request)
    with connections["default"].cursor() as cursor:
        _before = _audit.snap(cursor, "masters.parts_of_body", part_id)
        if part_id:
            dbq(cursor, """
                UPDATE eos_Mst_Parts_Of_Body
                SET Part_Of_Body_Name=%s, Mod_User_Id=%s, Mod_Dt=%s
                WHERE Part_Of_Body_Id=%s
            """, [part_name, _uid, now, part_id])
        else:
            dbq(cursor, "SELECT COALESCE(MAX(Part_Of_Body_Id),0)+1 FROM eos_Mst_Parts_Of_Body")
            new_id = cursor.fetchone()[0]
            dbq(cursor, """
                INSERT INTO eos_Mst_Parts_Of_Body
                    (Part_Of_Body_Id, Part_Of_Body_Name, Cr_User_Id, Cr_Dt)
                VALUES (%s, %s, %s, %s)
            """, [new_id, part_name, _uid, now])
            part_id = new_id
        _audit.record_save(request, cursor, "masters.parts_of_body", part_id, _before)
    return JsonResponse({"success": True, "part_of_body_id": part_id})


# ── QHSE Category Master (add / edit only — referenced by QHSE actions) ─────────

@require_permission("masters.qhse_categories", "view")
def qhse_category_page(request):
    return render(request, "chatbot/masters/qhse_category.html")


@require_GET
def qhse_category_list_api(request):
    from django.db import connections
    q      = request.GET.get("q", "").strip()
    offset = max(0, int(request.GET.get("offset", 0)))
    limit  = min(200, max(1, int(request.GET.get("limit", 200))))
    with connections["default"].cursor() as cursor:
        dbq(cursor, """
            SELECT QHSE_Category_Id, QHSE_Category_Name
            FROM eos_Mst_QHSE_Category
            WHERE QHSE_Category_Name LIKE %s
            ORDER BY QHSE_Category_Name
            LIMIT %s OFFSET %s
        """, [f"%{q}%", limit, offset])
        cols = [c[0] for c in cursor.description]
        rows = [dict(zip(cols, row)) for row in cursor.fetchall()]
    return JsonResponse({"results": rows})


@require_GET
def qhse_category_get_api(request, cat_id):
    from django.db import connections
    with connections["default"].cursor() as cursor:
        dbq(cursor, """
            SELECT QHSE_Category_Id, QHSE_Category_Name
            FROM eos_Mst_QHSE_Category
            WHERE QHSE_Category_Id=%s
        """, [cat_id])
        cols = [c[0] for c in cursor.description]
        row  = cursor.fetchone()
    if not row:
        return JsonResponse({"error": "Not found"}, status=404)
    return JsonResponse(dict(zip(cols, row)))


@csrf_exempt
def qhse_category_save_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    _a = _get_access(request)
    if not _a["is_admin"]:
        try:
            _bpk = json.loads(request.body)
            _has_id = bool(_bpk.get("qhse_category_id"))
        except Exception:
            _has_id = False
        _pact = "edit" if _has_id else "add"
        if not _a["perms"].get("masters.qhse_categories", {}).get(_pact):
            return JsonResponse({"error": "Permission denied"}, status=403)
    from django.db import connections
    import json
    body     = json.loads(request.body)
    cat_id   = body.get("qhse_category_id")
    cat_name = (body.get("qhse_category_name") or "").strip()
    if not cat_name:
        return JsonResponse({"error": "Category is required"}, status=400)
    now = datetime.now()
    _uid = _audit.ops_user_id(request)
    with connections["default"].cursor() as cursor:
        _before = _audit.snap(cursor, "masters.qhse_categories", cat_id)
        if cat_id:
            dbq(cursor, """
                UPDATE eos_Mst_QHSE_Category
                SET QHSE_Category_Name=%s, Mod_User_Id=%s, Mod_Dt=%s
                WHERE QHSE_Category_Id=%s
            """, [cat_name, _uid, now, cat_id])
        else:
            dbq(cursor, "SELECT COALESCE(MAX(QHSE_Category_Id),0)+1 FROM eos_Mst_QHSE_Category")
            new_id = cursor.fetchone()[0]
            dbq(cursor, """
                INSERT INTO eos_Mst_QHSE_Category
                    (QHSE_Category_Id, QHSE_Category_Name, Cr_User_Id, Cr_Dt)
                VALUES (%s, %s, %s, %s)
            """, [new_id, cat_name, _uid, now])
            cat_id = new_id
        _audit.record_save(request, cursor, "masters.qhse_categories", cat_id, _before)
    return JsonResponse({"success": True, "qhse_category_id": cat_id})


# ── HSE Activity Master ───────────────────────────────────────────────────────

# Activity type is a fixed 2-char code → label map.
_HSE_ACTIVITY_TYPES = {"IN": "Inspection", "DR": "Drill", "AU": "Audit", "OT": "Other"}


@require_permission("masters.hse_activities", "view")
def hse_activity_page(request):
    return render(request, "chatbot/masters/hse_activity.html")


@require_GET
def hse_activity_list_api(request):
    from django.db import connections
    q      = request.GET.get("q", "").strip()
    offset = max(0, int(request.GET.get("offset", 0)))
    limit  = min(200, max(1, int(request.GET.get("limit", 200))))
    with connections["default"].cursor() as cursor:
        dbq(cursor, """
            SELECT HSE_Activity_Id, HSE_Activity_Name, HSE_Activity_Type
            FROM eos_Mst_HSE_Activity
            WHERE HSE_Activity_Name LIKE %s
            ORDER BY HSE_Activity_Name
            LIMIT %s OFFSET %s
        """, [f"%{q}%", limit, offset])
        cols = [c[0] for c in cursor.description]
        rows = [dict(zip(cols, row)) for row in cursor.fetchall()]
    return JsonResponse({"results": rows})


@require_GET
def hse_activity_get_api(request, act_id):
    from django.db import connections
    with connections["default"].cursor() as cursor:
        dbq(cursor, """
            SELECT HSE_Activity_Id, HSE_Activity_Name, HSE_Activity_Type
            FROM eos_Mst_HSE_Activity
            WHERE HSE_Activity_Id=%s
        """, [act_id])
        cols = [c[0] for c in cursor.description]
        row  = cursor.fetchone()
    if not row:
        return JsonResponse({"error": "Not found"}, status=404)
    return JsonResponse(dict(zip(cols, row)))


@csrf_exempt
def hse_activity_save_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    _a = _get_access(request)
    if not _a["is_admin"]:
        try:
            _bpk = json.loads(request.body)
            _has_id = bool(_bpk.get("hse_activity_id"))
        except Exception:
            _has_id = False
        _pact = "edit" if _has_id else "add"
        if not _a["perms"].get("masters.hse_activities", {}).get(_pact):
            return JsonResponse({"error": "Permission denied"}, status=403)
    from django.db import connections
    import json
    body      = json.loads(request.body)
    act_id    = body.get("hse_activity_id")
    act_name  = (body.get("hse_activity_name") or "").strip()
    act_type  = (body.get("hse_activity_type") or "").strip()
    if not act_name:
        return JsonResponse({"error": "Activity name is required"}, status=400)
    if act_type not in _HSE_ACTIVITY_TYPES:
        return JsonResponse({"error": "Activity type is required"}, status=400)
    now = datetime.now()
    _uid = _audit.ops_user_id(request)
    with connections["default"].cursor() as cursor:
        _before = _audit.snap(cursor, "masters.hse_activities", act_id)
        if act_id:
            dbq(cursor, """
                UPDATE eos_Mst_HSE_Activity
                SET HSE_Activity_Name=%s, HSE_Activity_Type=%s, Mod_User_Id=%s, Mod_Dt=%s
                WHERE HSE_Activity_Id=%s
            """, [act_name, act_type, _uid, now, act_id])
        else:
            dbq(cursor, "SELECT COALESCE(MAX(HSE_Activity_Id),0)+1 FROM eos_Mst_HSE_Activity")
            new_id = cursor.fetchone()[0]
            dbq(cursor, """
                INSERT INTO eos_Mst_HSE_Activity
                    (HSE_Activity_Id, HSE_Activity_Name, HSE_Activity_Type, Cr_User_Id, Cr_Dt)
                VALUES (%s, %s, %s, %s, %s)
            """, [new_id, act_name, act_type, _uid, now])
            act_id = new_id
        _audit.record_save(request, cursor, "masters.hse_activities", act_id, _before)
    return JsonResponse({"success": True, "hse_activity_id": act_id})


@require_GET
def hse_activity_check_delete_api(request, act_id):
    from django.db import connections
    with connections["default"].cursor() as cursor:
        dbq(cursor, "SELECT COUNT(*) FROM eos_MIS_Monthly_HSE_Activities WHERE HSE_Activity_Id=%s", [act_id])
        n = cursor.fetchone()[0]
    if n:
        return JsonResponse({"can_delete": False, "references": [{"count": n, "label": "Monthly HSE Activity record(s)"}]})
    return JsonResponse({"can_delete": True, "references": []})


@csrf_exempt
def hse_activity_delete_api(request, act_id):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    _a = _get_access(request)
    if not _a["is_admin"] and not _a["perms"].get("masters.hse_activities", {}).get("delete"):
        return JsonResponse({"error": "Permission denied"}, status=403)
    from django.db import connections
    with connections["default"].cursor() as cursor:
        dbq(cursor, "SELECT COUNT(*) FROM eos_MIS_Monthly_HSE_Activities WHERE HSE_Activity_Id=%s", [act_id])
        if cursor.fetchone()[0]:
            return JsonResponse({"error": "Cannot delete: referenced by Monthly HSE Activity records"}, status=409)
        _before = _audit.snap(cursor, "masters.hse_activities", act_id)
        dbq(cursor, "DELETE FROM eos_Mst_HSE_Activity WHERE HSE_Activity_Id=%s", [act_id])
    _audit.record_delete(request, "masters.hse_activities", act_id, _before)
    return JsonResponse({"success": True})


# ── HSE Consumable Master ─────────────────────────────────────────────────────

@require_permission("masters.hse_consumables", "view")
def hse_consumable_page(request):
    return render(request, "chatbot/masters/hse_consumable.html")


@require_GET
def hse_consumable_list_api(request):
    from django.db import connections
    q      = request.GET.get("q", "").strip()
    offset = max(0, int(request.GET.get("offset", 0)))
    limit  = min(200, max(1, int(request.GET.get("limit", 200))))
    with connections["default"].cursor() as cursor:
        dbq(cursor, """
            SELECT HSE_Consumable_Id, HSE_Consumable_Name, HSE_Consumption_Unit
            FROM eos_Mst_HSE_Consumable
            WHERE HSE_Consumable_Name LIKE %s
            ORDER BY HSE_Consumable_Name
            LIMIT %s OFFSET %s
        """, [f"%{q}%", limit, offset])
        cols = [c[0] for c in cursor.description]
        rows = [dict(zip(cols, row)) for row in cursor.fetchall()]
    return JsonResponse({"results": rows})


@require_GET
def hse_consumable_get_api(request, con_id):
    from django.db import connections
    with connections["default"].cursor() as cursor:
        dbq(cursor, """
            SELECT HSE_Consumable_Id, HSE_Consumable_Name, HSE_Consumption_Unit
            FROM eos_Mst_HSE_Consumable
            WHERE HSE_Consumable_Id=%s
        """, [con_id])
        cols = [c[0] for c in cursor.description]
        row  = cursor.fetchone()
    if not row:
        return JsonResponse({"error": "Not found"}, status=404)
    return JsonResponse(dict(zip(cols, row)))


@csrf_exempt
def hse_consumable_save_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    _a = _get_access(request)
    if not _a["is_admin"]:
        try:
            _bpk = json.loads(request.body)
            _has_id = bool(_bpk.get("hse_consumable_id"))
        except Exception:
            _has_id = False
        _pact = "edit" if _has_id else "add"
        if not _a["perms"].get("masters.hse_consumables", {}).get(_pact):
            return JsonResponse({"error": "Permission denied"}, status=403)
    from django.db import connections
    import json
    body      = json.loads(request.body)
    con_id    = body.get("hse_consumable_id")
    con_name  = (body.get("hse_consumable_name") or "").strip()
    con_unit  = (body.get("hse_consumption_unit") or "").strip()
    if not con_name:
        return JsonResponse({"error": "Consumable name is required"}, status=400)
    if not con_unit:
        return JsonResponse({"error": "Consumption unit is required"}, status=400)
    now = datetime.now()
    _uid = _audit.ops_user_id(request)
    with connections["default"].cursor() as cursor:
        _before = _audit.snap(cursor, "masters.hse_consumables", con_id)
        if con_id:
            dbq(cursor, """
                UPDATE eos_Mst_HSE_Consumable
                SET HSE_Consumable_Name=%s, HSE_Consumption_Unit=%s, Mod_User_Id=%s, Mod_Dt=%s
                WHERE HSE_Consumable_Id=%s
            """, [con_name, con_unit, _uid, now, con_id])
        else:
            dbq(cursor, "SELECT COALESCE(MAX(HSE_Consumable_Id),0)+1 FROM eos_Mst_HSE_Consumable")
            new_id = cursor.fetchone()[0]
            dbq(cursor, """
                INSERT INTO eos_Mst_HSE_Consumable
                    (HSE_Consumable_Id, HSE_Consumable_Name, HSE_Consumption_Unit, Cr_User_Id, Cr_Dt)
                VALUES (%s, %s, %s, %s, %s)
            """, [new_id, con_name, con_unit, _uid, now])
            con_id = new_id
        _audit.record_save(request, cursor, "masters.hse_consumables", con_id, _before)
    return JsonResponse({"success": True, "hse_consumable_id": con_id})


@require_GET
def hse_consumable_check_delete_api(request, con_id):
    from django.db import connections
    with connections["default"].cursor() as cursor:
        dbq(cursor, "SELECT COUNT(*) FROM eos_MIS_Monthly_HSE_Environment WHERE HSE_Consumable_Id=%s", [con_id])
        n = cursor.fetchone()[0]
    if n:
        return JsonResponse({"can_delete": False, "references": [{"count": n, "label": "Monthly HSE Environment record(s)"}]})
    return JsonResponse({"can_delete": True, "references": []})


@csrf_exempt
def hse_consumable_delete_api(request, con_id):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    _a = _get_access(request)
    if not _a["is_admin"] and not _a["perms"].get("masters.hse_consumables", {}).get("delete"):
        return JsonResponse({"error": "Permission denied"}, status=403)
    from django.db import connections
    with connections["default"].cursor() as cursor:
        dbq(cursor, "SELECT COUNT(*) FROM eos_MIS_Monthly_HSE_Environment WHERE HSE_Consumable_Id=%s", [con_id])
        if cursor.fetchone()[0]:
            return JsonResponse({"error": "Cannot delete: referenced by Monthly HSE Environment records"}, status=409)
        _before = _audit.snap(cursor, "masters.hse_consumables", con_id)
        dbq(cursor, "DELETE FROM eos_Mst_HSE_Consumable WHERE HSE_Consumable_Id=%s", [con_id])
    _audit.record_delete(request, "masters.hse_consumables", con_id, _before)
    return JsonResponse({"success": True})


# ── Hazard Type Master ────────────────────────────────────────────────────────

_HAZARD_CLASSES = ("Negative", "Positive")

# Tables that reference a hazard type — checked before delete.
_HAZARD_REF_TABLES = (
    ("eos_Hazard_ID_Card",            "Hazard ID Card record(s)"),
    ("eos_Hazard_ID_Card_Client",     "Client Hazard ID Card record(s)"),
    ("eos_Wkg_Hazard_ID_Card_Client", "Working Client Hazard ID Card record(s)"),
)


@require_permission("masters.hazard_types", "view")
def hazard_type_page(request):
    return render(request, "chatbot/masters/hazard_type.html")


@require_GET
def hazard_type_list_api(request):
    from django.db import connections
    q      = request.GET.get("q", "").strip()
    offset = max(0, int(request.GET.get("offset", 0)))
    limit  = min(200, max(1, int(request.GET.get("limit", 200))))
    with connections["default"].cursor() as cursor:
        dbq(cursor, """
            SELECT Haz_Type_Id, Haz_Type_Name, Haz_Type_Class
            FROM eos_Mst_Hazard_Type
            WHERE Haz_Type_Name LIKE %s
            ORDER BY Haz_Type_Name
            LIMIT %s OFFSET %s
        """, [f"%{q}%", limit, offset])
        cols = [c[0] for c in cursor.description]
        rows = [dict(zip(cols, row)) for row in cursor.fetchall()]
    return JsonResponse({"results": rows})


@require_GET
def hazard_type_get_api(request, haz_id):
    from django.db import connections
    with connections["default"].cursor() as cursor:
        dbq(cursor, """
            SELECT Haz_Type_Id, Haz_Type_Name, Haz_Type_Class
            FROM eos_Mst_Hazard_Type
            WHERE Haz_Type_Id=%s
        """, [haz_id])
        cols = [c[0] for c in cursor.description]
        row  = cursor.fetchone()
    if not row:
        return JsonResponse({"error": "Not found"}, status=404)
    return JsonResponse(dict(zip(cols, row)))


@csrf_exempt
def hazard_type_save_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    _a = _get_access(request)
    if not _a["is_admin"]:
        try:
            _bpk = json.loads(request.body)
            _has_id = bool(_bpk.get("haz_type_id"))
        except Exception:
            _has_id = False
        _pact = "edit" if _has_id else "add"
        if not _a["perms"].get("masters.hazard_types", {}).get(_pact):
            return JsonResponse({"error": "Permission denied"}, status=403)
    from django.db import connections
    import json
    body       = json.loads(request.body)
    haz_id     = body.get("haz_type_id")
    haz_name   = (body.get("haz_type_name") or "").strip()
    haz_class  = (body.get("haz_type_class") or "").strip()
    if not haz_name:
        return JsonResponse({"error": "Hazard type is required"}, status=400)
    if haz_class not in _HAZARD_CLASSES:
        return JsonResponse({"error": "Class must be Negative or Positive"}, status=400)
    now = datetime.now()
    _uid = _audit.ops_user_id(request)
    with connections["default"].cursor() as cursor:
        _before = _audit.snap(cursor, "masters.hazard_types", haz_id)
        if haz_id:
            dbq(cursor, """
                UPDATE eos_Mst_Hazard_Type
                SET Haz_Type_Name=%s, Haz_Type_Class=%s, Mod_User_Id=%s, Mod_Dt=%s
                WHERE Haz_Type_Id=%s
            """, [haz_name, haz_class, _uid, now, haz_id])
        else:
            dbq(cursor, "SELECT COALESCE(MAX(Haz_Type_Id),0)+1 FROM eos_Mst_Hazard_Type")
            new_id = cursor.fetchone()[0]
            dbq(cursor, """
                INSERT INTO eos_Mst_Hazard_Type
                    (Haz_Type_Id, Haz_Type_Name, Haz_Type_Class, Haz_Type_Active, Cr_User_Id, Cr_Dt)
                VALUES (%s, %s, %s, 'Y', %s, %s)
            """, [new_id, haz_name, haz_class, _uid, now])
            haz_id = new_id
        _audit.record_save(request, cursor, "masters.hazard_types", haz_id, _before)
    return JsonResponse({"success": True, "haz_type_id": haz_id})


@require_GET
def hazard_type_check_delete_api(request, haz_id):
    from django.db import connections
    refs = []
    with connections["default"].cursor() as cursor:
        for table, label in _HAZARD_REF_TABLES:
            dbq(cursor, f"SELECT COUNT(*) FROM {table} WHERE Haz_Type_Id=%s", [haz_id])
            n = cursor.fetchone()[0]
            if n:
                refs.append({"count": n, "label": label})
    return JsonResponse({"can_delete": not refs, "references": refs})


@csrf_exempt
def hazard_type_delete_api(request, haz_id):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    _a = _get_access(request)
    if not _a["is_admin"] and not _a["perms"].get("masters.hazard_types", {}).get("delete"):
        return JsonResponse({"error": "Permission denied"}, status=403)
    from django.db import connections
    with connections["default"].cursor() as cursor:
        for table, _label in _HAZARD_REF_TABLES:
            dbq(cursor, f"SELECT COUNT(*) FROM {table} WHERE Haz_Type_Id=%s", [haz_id])
            if cursor.fetchone()[0]:
                return JsonResponse({"error": "Cannot delete: referenced by Hazard ID Card records"}, status=409)
        _before = _audit.snap(cursor, "masters.hazard_types", haz_id)
        dbq(cursor, "DELETE FROM eos_Mst_Hazard_Type WHERE Haz_Type_Id=%s", [haz_id])
    _audit.record_delete(request, "masters.hazard_types", haz_id, _before)
    return JsonResponse({"success": True})


# ── Cert Institute Master ─────────────────────────────────────────────────────

@require_permission("masters.cert_institutes", "view")
def cert_institute_page(request):
    return render(request, "chatbot/masters/cert_institute.html")

@require_GET
def cert_institute_list_api(request):
    from django.db import connections
    with connections["default"].cursor() as cursor:
        dbq(cursor, """
            SELECT ci.Cert_Institute_Id, ci.Cert_Institute_Name, ci.Cert_Institute_Shortname,
                   ci.Cert_Institute_Address, ci.Location_Id, l.Location_Name, ci.Tel_No
            FROM eos_Mst_Cert_Institute ci
            LEFT JOIN Mst_Location l ON ci.Location_Id = l.Location_Id
            ORDER BY ci.Cert_Institute_Name
        """)
        cols = [c[0] for c in cursor.description]
        rows = [dict(zip(cols, row)) for row in cursor.fetchall()]
    return JsonResponse({"results": rows})

@require_GET
def cert_institute_get_api(request, inst_id):
    from django.db import connections
    with connections["default"].cursor() as cursor:
        dbq(cursor, """
            SELECT ci.Cert_Institute_Id, ci.Cert_Institute_Name, ci.Cert_Institute_Shortname,
                   ci.Cert_Institute_Address, ci.Location_Id, l.Location_Name, ci.Tel_No
            FROM eos_Mst_Cert_Institute ci
            LEFT JOIN Mst_Location l ON ci.Location_Id = l.Location_Id
            WHERE ci.Cert_Institute_Id = %s
        """, [inst_id])
        cols = [c[0] for c in cursor.description]
        row = cursor.fetchone()
    if not row:
        return JsonResponse({"error": "Not found"}, status=404)
    return JsonResponse(dict(zip(cols, row)))

@csrf_exempt
def cert_institute_save_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    _a = _get_access(request)
    if not _a["is_admin"]:
        try:
            _bpk = json.loads(request.body)
            _has_id = bool(_bpk.get("Cert_Institute_Id"))
        except Exception:
            _has_id = False
        _pact = "edit" if _has_id else "add"
        if not _a["perms"].get("masters.cert_institutes", {}).get(_pact):
            return JsonResponse({"error": "Permission denied"}, status=403)
    from django.db import connections
    body     = json.loads(request.body)
    inst_id  = body.get("Cert_Institute_Id") or None
    name     = (body.get("Cert_Institute_Name") or "").strip()
    short    = (body.get("Cert_Institute_Shortname") or "").strip()
    address  = (body.get("Cert_Institute_Address") or "").strip() or None
    loc_id   = body.get("Location_Id") or None
    tel      = (body.get("Tel_No") or "").strip() or None
    if not name or not short or not loc_id:
        return JsonResponse({"error": "Institute Name, Short Name and Location are required"}, status=400)
    now = datetime.now()
    cr_user_id = _audit.ops_user_id(request)
    with connections["default"].cursor() as cursor:
        _before = _audit.snap(cursor, "masters.cert_institutes", inst_id)
        if inst_id:
            dbq(cursor, """
                UPDATE eos_Mst_Cert_Institute
                SET Cert_Institute_Name=%s, Cert_Institute_Shortname=%s,
                    Cert_Institute_Address=%s, Location_Id=%s, Tel_No=%s,
                    Mod_User_Id=%s, Mod_Dt=%s
                WHERE Cert_Institute_Id=%s
            """, [name, short, address, loc_id, tel, cr_user_id, now, inst_id])
            _audit.record_save(request, cursor, "masters.cert_institutes", inst_id, _before)
            return JsonResponse({"success": True, "Cert_Institute_Id": inst_id, "action": "updated"})
        else:
            dbq(cursor, "SELECT COALESCE(MAX(Cert_Institute_Id), 0) + 1 FROM eos_Mst_Cert_Institute")
            new_id = cursor.fetchone()[0]
            dbq(cursor, """
                INSERT INTO eos_Mst_Cert_Institute
                    (Cert_Institute_Id, Cert_Institute_Name, Cert_Institute_Shortname,
                     Cert_Institute_Address, Location_Id, Tel_No, Cr_User_Id, Cr_Dt)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, [new_id, name, short, address, loc_id, tel, cr_user_id, now])
            _audit.record_save(request, cursor, "masters.cert_institutes", new_id, _before)
            return JsonResponse({"success": True, "Cert_Institute_Id": new_id, "action": "inserted"})

@require_GET
def cert_institute_check_delete_api(request, inst_id):
    from django.db import connections
    refs = []
    with connections["default"].cursor() as cursor:
        for table, col, label in [
            ("eos_Emp_Certificate", "Cert_Institute_Id", "Employee Certificates"),
        ]:
            try:
                dbq(cursor, f"SELECT COUNT(*) FROM {table} WHERE {col}=%s", [inst_id])
                count = cursor.fetchone()[0]
                if count > 0:
                    refs.append({"label": label, "count": count})
            except Exception:
                pass
    return JsonResponse({"can_delete": len(refs) == 0, "references": refs})

@csrf_exempt
def cert_institute_delete_api(request, inst_id):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    _a = _get_access(request)
    if not _a["is_admin"] and not _a["perms"].get("masters.cert_institutes", {}).get("delete"):
        return JsonResponse({"error": "Permission denied"}, status=403)
    from django.db import connections
    with connections["default"].cursor() as cursor:
        _before = _audit.snap(cursor, "masters.cert_institutes", inst_id)
        dbq(cursor, "DELETE FROM eos_Mst_Cert_Institute WHERE Cert_Institute_Id=%s", [inst_id])
    _audit.record_delete(request, "masters.cert_institutes", inst_id, _before)
    return JsonResponse({"success": True})


# ── Email Notification Type Master ───────────────────────────────────────────

@require_permission("masters.email_notification_types", "view")
def email_notification_type_page(request):
    return render(request, "chatbot/masters/email_notification_type.html")

@require_GET
def email_notification_type_list_api(request):
    from django.db import connections
    with connections["default"].cursor() as cursor:
        dbq(cursor, """
            SELECT EN_Type_Id, EN_Type_Name, EN_Type_Subject, EN_Type_Active
            FROM eos_Email_Notification_Type
            ORDER BY EN_Type_Name
        """)
        cols = [c[0] for c in cursor.description]
        rows = [dict(zip(cols, row)) for row in cursor.fetchall()]
    return JsonResponse({"results": rows})

@require_GET
def email_notification_type_get_api(request, type_id):
    from django.db import connections
    with connections["default"].cursor() as cursor:
        dbq(cursor, """
            SELECT EN_Type_Id, EN_Type_Name, EN_Type_Subject, EN_Description, EN_Type_Active
            FROM eos_Email_Notification_Type
            WHERE EN_Type_Id = %s
        """, [type_id])
        cols = [c[0] for c in cursor.description]
        row = cursor.fetchone()
    if not row:
        return JsonResponse({"error": "Not found"}, status=404)
    return JsonResponse(dict(zip(cols, row)))

@csrf_exempt
def email_notification_type_save_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    _a = _get_access(request)
    if not _a["is_admin"]:
        try:
            _bpk = json.loads(request.body)
            _has_id = bool(_bpk.get("EN_Type_Id"))
        except Exception:
            _has_id = False
        _pact = "edit" if _has_id else "add"
        if not _a["perms"].get("masters.email_notification_types", {}).get(_pact):
            return JsonResponse({"error": "Permission denied"}, status=403)
    from django.db import connections
    body    = json.loads(request.body)
    type_id = body.get("EN_Type_Id") or None
    name    = (body.get("EN_Type_Name") or "").strip()
    subject = (body.get("EN_Type_Subject") or "").strip()
    desc    = (body.get("EN_Description") or "").strip()
    active  = body.get("EN_Type_Active", "Y")
    if not name or not subject:
        return JsonResponse({"error": "Type Name and Subject are required"}, status=400)
    now = datetime.now()
    cr_user_id = _audit.ops_user_id(request)
    with connections["default"].cursor() as cursor:
        _before = _audit.snap(cursor, "masters.email_notification_types", type_id)
        if type_id:
            dbq(cursor, """
                UPDATE eos_Email_Notification_Type
                SET EN_Type_Name=%s, EN_Type_Subject=%s, EN_Description=%s,
                    EN_Type_Active=%s, Mod_User_Id=%s, Mod_Dt=%s
                WHERE EN_Type_Id=%s
            """, [name, subject, desc, active, cr_user_id, now, type_id])
            _audit.record_save(request, cursor, "masters.email_notification_types", type_id, _before)
            return JsonResponse({"success": True, "EN_Type_Id": type_id, "action": "updated"})
        else:
            dbq(cursor, "SELECT COALESCE(MAX(EN_Type_Id), 0) + 1 FROM eos_Email_Notification_Type")
            new_id = cursor.fetchone()[0]
            dbq(cursor, """
                INSERT INTO eos_Email_Notification_Type
                    (EN_Type_Id, EN_Type_Name, EN_Type_Subject, EN_Description,
                     EN_Type_Active, Cr_User_Id, Cr_Dt)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, [new_id, name, subject, desc, "Y", cr_user_id, now])
            _audit.record_save(request, cursor, "masters.email_notification_types", new_id, _before)
            return JsonResponse({"success": True, "EN_Type_Id": new_id, "action": "inserted"})

@csrf_exempt
def email_notification_type_deactivate_api(request, type_id):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    _a = _get_access(request)
    if not _a["is_admin"] and not _a["perms"].get("masters.email_notification_types", {}).get("delete"):
        return JsonResponse({"error": "Permission denied"}, status=403)
    from django.db import connections
    with connections["default"].cursor() as cursor:
        _before = _audit.snap(cursor, "masters.email_notification_types", type_id)
        dbq(cursor, """
            UPDATE eos_Email_Notification_Type
            SET EN_Type_Active='N', Mod_User_Id=%s, Mod_Dt=%s
            WHERE EN_Type_Id=%s
        """, [_audit.ops_user_id(request), datetime.now(), type_id])
    _audit.record_deactivate(request, "masters.email_notification_types", type_id, _before)
    return JsonResponse({"success": True})


# ── JSON encoder that handles UUID and datetime ────────────────────────────────

import uuid
from datetime import datetime
from django.core.serializers.json import DjangoJSONEncoder


class _UUIDDateEncoder(DjangoJSONEncoder):
    def default(self, obj):
        if isinstance(obj, uuid.UUID):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


# ── Admin: User Rights ─────────────────────────────────────────────────────────

def _require_app_admin(view_fn):
    """Decorator: only app admins (or Django superusers) may access this view."""
    from functools import wraps
    from .permissions import get_user_access

    @wraps(view_fn)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("/login/")
        access = get_user_access(request)
        if not access["is_admin"]:
            return HttpResponse("Forbidden", status=403)
        return view_fn(request, *args, **kwargs)

    return wrapper


@_require_app_admin
def admin_user_rights_page(request):
    return render(request, "chatbot/admin/user_rights.html")


@_require_app_admin
@require_GET
def admin_users_api(request):
    """Paginated, searchable list of Mst_user rows for the user picker."""
    from django.db import connections as _conn
    from .models import UserProfile

    q          = request.GET.get("q", "").strip()
    admin_only = request.GET.get("admin_only") == "1"
    page       = max(int(request.GET.get("page", 1)), 1)
    limit      = 50
    offset     = (page - 1) * limit

    admin_ids = set(
        UserProfile.objects.filter(is_app_admin=True).values_list("user_id", flat=True)
    )

    conditions, params_base = [], []
    if q:
        conditions.append("(USER_NAME LIKE %s OR USER_LOGIN_ID LIKE %s)")
        params_base += [f"%{q}%", f"%{q}%"]
    if admin_only:
        if admin_ids:
            placeholders = ",".join(["%s"] * len(admin_ids))
            conditions.append(f"USER_ID IN ({placeholders})")
            params_base += list(admin_ids)
        else:
            conditions.append("1=0")

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    sql_counts = (
        f"SELECT COUNT(*), "
        f"SUM(CASE WHEN USER_ACTIVE='Y' THEN 1 ELSE 0 END), "
        f"SUM(CASE WHEN USER_ACTIVE!='Y' OR USER_ACTIVE IS NULL THEN 1 ELSE 0 END) "
        f"FROM Mst_user {where}"
    )
    sql_rows = (
        f"SELECT USER_ID, USER_LOGIN_ID, USER_NAME, USER_EMAIL, USER_ACTIVE "
        f"FROM Mst_user {where} ORDER BY USER_NAME LIMIT %s OFFSET %s"
    )

    with _conn["default"].cursor() as cursor:
        dbq(cursor, sql_counts, params_base)
        counts_row     = cursor.fetchone()
        total          = counts_row[0]
        active_count   = int(counts_row[1] or 0)
        inactive_count = int(counts_row[2] or 0)
        dbq(cursor, sql_rows, params_base + [limit, offset])
        rows = cursor.fetchall()

    users = [
        {
            "user_id":      r[0],
            "login_id":     r[1],
            "name":         r[2] or r[1],
            "email":        r[3] or "",
            "active":       r[4] == "Y",
            "is_app_admin": r[0] in admin_ids,
        }
        for r in rows
    ]
    return JsonResponse({
        "users": users, "page": page, "total": total,
        "active_count": active_count, "inactive_count": inactive_count,
        "admin_count": len(admin_ids),
        "has_more": offset + limit < total,
    })


@_require_app_admin
@require_GET
def admin_user_perms_api(request, user_id):
    """Return current permissions for one user."""
    from .models import UserPermission, UserProfile
    from .permissions import get_menu_registry

    try:
        profile = UserProfile.objects.get(user_id=user_id)
        is_admin = profile.is_app_admin
    except UserProfile.DoesNotExist:
        is_admin = False

    perm_rows = {
        p.menu_key: p
        for p in UserPermission.objects.filter(user_id=user_id)
    }

    menus = []
    for key, meta in get_menu_registry().items():
        row = perm_rows.get(key)
        menus.append({
            "key":     key,
            "label":   meta["label"],
            "group":   meta["group"],
            "actions": meta["actions"],
            "perms": {
                "view":   row.can_view   if row else False,
                "add":    row.can_add    if row else False,
                "edit":   row.can_edit   if row else False,
                "delete": row.can_delete if row else False,
                "export": row.can_export if row else False,
            },
        })

    return JsonResponse({"is_app_admin": is_admin, "menus": menus})


@_require_app_admin
@csrf_exempt
def admin_user_perms_save_api(request, user_id):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    from .models import UserPermission, UserProfile
    from .permissions import get_menu_registry

    is_admin  = bool(data.get("is_app_admin", False))
    login_id  = data.get("login_id", "")
    profile, _ = UserProfile.objects.get_or_create(
        user_id=user_id,
        defaults={"user_login_id": login_id},
    )
    # Snapshot the user's current rights for the audit diff.
    def _acts(obj):
        get = (lambda a: obj.get(a)) if isinstance(obj, dict) else (lambda a: getattr(obj, "can_" + a))
        return ",".join(a for a in ("view", "add", "edit", "delete", "export") if get(a)) or "—"
    _old_admin = profile.is_app_admin
    _old_perms = {up.menu_key: _acts(up) for up in UserPermission.objects.filter(user_id=user_id)}

    if login_id and profile.user_login_id != login_id:
        profile.user_login_id = login_id
    profile.is_app_admin = is_admin
    profile.save()

    menus = data.get("menus", {})
    granted_by = request.user.username
    valid_keys = set(get_menu_registry().keys())

    for key in valid_keys:
        if key not in menus:
            continue
        p = menus[key]
        UserPermission.objects.update_or_create(
            user_id=user_id,
            menu_key=key,
            defaults={
                "can_view":   bool(p.get("view")),
                "can_add":    bool(p.get("add")),
                "can_edit":   bool(p.get("edit")),
                "can_delete": bool(p.get("delete")),
                "can_export": bool(p.get("export")),
                "granted_by": granted_by,
            },
        )

    # Invalidate this user's cached permissions in all live sessions
    _invalidate_user_perm_cache(user_id)

    # Audit the permission change (before → after diff).
    _new_perms = {up.menu_key: _acts(up) for up in UserPermission.objects.filter(user_id=user_id)}
    _changes = {}
    if _old_admin != is_admin:
        _changes["is_app_admin"] = {"old": _old_admin, "new": is_admin}
    for _k in sorted(set(_old_perms) | set(_new_perms)):
        _ov, _nv = _old_perms.get(_k, "—"), _new_perms.get(_k, "—")
        if _ov != _nv:
            _changes[_k] = {"old": _ov, "new": _nv}
    _audit.record_action(request, "permission_change", "admin.user_rights",
                         user_id, (login_id or profile.user_login_id), _changes or None)

    return JsonResponse({"success": True})


@_require_app_admin
@csrf_exempt
def admin_user_admin_toggle_api(request, user_id):
    """Toggle is_app_admin for a user."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    from .models import UserProfile
    try:
        data = json.loads(request.body or "{}")
        login_id = data.get("login_id", "")
    except json.JSONDecodeError:
        login_id = ""
    profile, _ = UserProfile.objects.get_or_create(
        user_id=user_id,
        defaults={"user_login_id": login_id},
    )
    _was_admin = profile.is_app_admin
    profile.is_app_admin = not profile.is_app_admin
    profile.save()
    _invalidate_user_perm_cache(user_id)
    _audit.record_action(request, "permission_change", "admin.user_rights",
                         user_id, profile.user_login_id,
                         {"is_app_admin": {"old": _was_admin, "new": profile.is_app_admin}})
    return JsonResponse({"is_app_admin": profile.is_app_admin})


# ── Audit Trail (admin only) ───────────────────────────────────────────────────

@_require_app_admin
def admin_audit_trail_page(request):
    return render(request, "chatbot/admin/audit_trail.html")


@_require_app_admin
@require_GET
def admin_audit_facets_api(request):
    """Distinct users / entities / actions for the filter dropdowns.
    NOTE: .order_by() clears the model's default ordering (-ts) — otherwise Django
    adds ts to the SELECT and .distinct() dedupes over (value, ts) pairs, producing
    duplicate dropdown options."""
    from .models import CbAuditLog
    base = CbAuditLog.objects.order_by()
    actions = sorted(set(base.values_list("action", flat=True)))
    users   = sorted({u for u in base.values_list("username", flat=True) if u})
    seen, entities = {}, []
    for e in base.values_list("entity", "entity_label"):
        key = e[0]
        if key not in seen:
            seen[key] = e[1] or key
    entities = sorted(({"key": k, "label": v} for k, v in seen.items()), key=lambda x: x["label"])
    return JsonResponse({"actions": actions, "users": users, "entities": entities})


@_require_app_admin
@require_GET
def admin_audit_list_api(request):
    from django.db.models import Q
    from .models import CbAuditLog
    qs = CbAuditLog.objects.all()
    action = request.GET.get("action", "").strip()
    entity = request.GET.get("entity", "").strip()
    user   = request.GET.get("user", "").strip()
    q      = request.GET.get("q", "").strip()
    dfrom  = request.GET.get("from", "").strip()
    dto    = request.GET.get("to", "").strip()
    if action: qs = qs.filter(action=action)
    if entity: qs = qs.filter(entity=entity)
    if user:   qs = qs.filter(username=user)
    if q:      qs = qs.filter(Q(record_label__icontains=q) | Q(username__icontains=q) | Q(entity_label__icontains=q))
    if dfrom:  qs = qs.filter(ts__date__gte=dfrom)
    if dto:    qs = qs.filter(ts__date__lte=dto)

    total = qs.count()
    try:
        page = max(1, int(request.GET.get("page", 1)))
    except (TypeError, ValueError):
        page = 1
    size = 30
    rows = list(qs.order_by("-ts")[(page - 1) * size: page * size].values(
        "id", "ts", "user_id", "username", "action", "entity", "entity_label",
        "record_id", "record_label", "changes", "ip"))
    for r in rows:
        r["ts"] = r["ts"].strftime("%Y-%m-%d %H:%M:%S") if r["ts"] else ""
    return JsonResponse({
        "results": rows, "total": total, "page": page,
        "page_size": size, "pages": (total + size - 1) // size,
    })


# ── User Management ────────────────────────────────────────────────────────────

@_require_app_admin
def admin_user_management_page(request):
    return render(request, "chatbot/admin/user_management.html")


@_require_app_admin
@require_GET
def admin_user_management_list_api(request):
    """Paginated user list with auth_type (local/ad) and active status."""
    from django.db import connections as _conn
    from .models import CbMstUserPassword

    q          = request.GET.get("q", "").strip()
    page       = max(int(request.GET.get("page", 1)), 1)
    local_only = request.GET.get("local_only") == "1"
    limit  = 50
    offset = (page - 1) * limit

    # Fetch all local-password user IDs once (cross-db lookup)
    all_local_ids = set(
        CbMstUserPassword.objects.using("chathistory").values_list("user_id", flat=True)
    )
    local_count = len(all_local_ids)

    conditions, params_base = [], []
    if q:
        conditions.append("(USER_NAME LIKE %s OR USER_LOGIN_ID LIKE %s)")
        params_base += [f"%{q}%", f"%{q}%"]
    if local_only:
        if all_local_ids:
            placeholders = ",".join(["%s"] * len(all_local_ids))
            conditions.append(f"USER_ID IN ({placeholders})")
            params_base += list(all_local_ids)
        else:
            conditions.append("1=0")

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    sql_counts = (
        f"SELECT COUNT(*), "
        f"SUM(CASE WHEN USER_ACTIVE='Y' THEN 1 ELSE 0 END), "
        f"SUM(CASE WHEN USER_ACTIVE!='Y' OR USER_ACTIVE IS NULL THEN 1 ELSE 0 END) "
        f"FROM Mst_user {where}"
    )
    sql_rows = (
        f"SELECT USER_ID, USER_LOGIN_ID, USER_NAME, USER_EMAIL, USER_ACTIVE "
        f"FROM Mst_user {where} ORDER BY USER_NAME LIMIT %s OFFSET %s"
    )

    with _conn["default"].cursor() as cursor:
        dbq(cursor, sql_counts, params_base)
        cr = cursor.fetchone()
        total          = int(cr[0] or 0)
        active_count   = int(cr[1] or 0)
        inactive_count = int(cr[2] or 0)
        dbq(cursor, sql_rows, params_base + [limit, offset])
        rows = cursor.fetchall()

    # Mark auth_type for the returned page
    page_ids = [r[0] for r in rows]
    local_ids = all_local_ids & set(page_ids)

    users = [
        {
            "user_id":   r[0],
            "login_id":  r[1],
            "name":      r[2] or r[1],
            "email":     r[3] or "",
            "active":    r[4] == "Y",
            "auth_type": "local" if r[0] in local_ids else "ad",
        }
        for r in rows
    ]
    return JsonResponse({
        "users": users, "page": page, "total": total,
        "active_count": active_count, "inactive_count": inactive_count,
        "local_count": local_count,
        "has_more": offset + limit < total,
    })


@_require_app_admin
@require_GET
def admin_user_management_get_api(request, user_id):
    from django.db import connections as _conn
    from .models import CbMstUserPassword

    with _conn["default"].cursor() as cursor:
        dbq(cursor, 
            "SELECT u.USER_ID, u.USER_LOGIN_ID, u.USER_NAME, u.USER_EMAIL, u.USER_ACTIVE, "
            "u.USER_TYPE_ID, u.DEPT_ID, u.USER_FROM, u.USER_TO, u.EMP_ID, u.NONEMP_ID, "
            "u.CR_DT, u.MOD_DT, d.Dept_Dispname "
            "FROM Mst_user u "
            "LEFT JOIN Mst_Department d ON d.Dept_Id = u.DEPT_ID "
            "WHERE u.USER_ID = %s",
            [user_id],
        )
        row = cursor.fetchone()

    if not row:
        return JsonResponse({"error": "User not found"}, status=404)

    has_local = CbMstUserPassword.objects.using("chathistory").filter(user_id=user_id).exists()

    def _dt(v):
        return v.strftime("%Y-%m-%d") if v else ""

    return JsonResponse({
        "user_id":    row[0],
        "login_id":   row[1] or "",
        "name":       row[2] or row[1] or "",
        "email":      row[3] or "",
        "active":     row[4] == "Y",
        "user_type":  row[5] or "",
        "dept_id":    row[6],
        "dept_name":  row[13] or "",
        "user_from":  _dt(row[7]),
        "user_to":    _dt(row[8]),
        "emp_id":     row[9],
        "nonemp_id":  row[10],
        "created_at": _dt(row[11]),
        "modified_at":_dt(row[12]),
        "auth_type":  "local" if has_local else "ad",
    })


@_require_app_admin
@require_GET
def admin_user_management_meta_api(request):
    from django.db import connections as _conn
    with _conn["default"].cursor() as cursor:
        dbq(cursor, "SELECT Dept_Id, Dept_Dispname FROM Mst_Department ORDER BY Dept_Dispname")
        depts = [{"id": r[0], "name": r[1]} for r in cursor.fetchall()]
    return JsonResponse({"departments": depts})


@_require_app_admin
@csrf_exempt
def admin_user_management_update_api(request, user_id):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    name      = data.get("name", "").strip()
    email     = data.get("email", "").strip()
    dept_id   = data.get("dept_id") or None
    user_type = data.get("user_type", "").strip().upper() or None
    user_from = data.get("user_from", "").strip() or None
    user_to   = data.get("user_to", "").strip() or None

    if not name:
        return JsonResponse({"error": "Name is required"}, status=400)
    if user_type and user_type not in ("E", "N"):
        return JsonResponse({"error": "User type must be E or N"}, status=400)

    from django.db import connections as _conn
    from .models import UserProfile

    try:
        admin_profile = UserProfile.objects.get(user_login_id=request.user.username)
        mod_user_id = admin_profile.user_id
    except Exception:
        mod_user_id = 1

    with _conn["default"].cursor() as cursor:
        dbq(cursor, "SELECT USER_ID FROM Mst_user WHERE USER_ID = %s", [user_id])
        if not cursor.fetchone():
            return JsonResponse({"error": "User not found"}, status=404)

        dbq(cursor, 
            "UPDATE Mst_user SET USER_NAME=%s, USER_EMAIL=%s, DEPT_ID=%s, "
            "USER_TYPE_ID=%s, USER_FROM=%s, USER_TO=%s, MOD_USER_ID=%s, MOD_DT=NOW() "
            "WHERE USER_ID=%s",
            [name, email or None, dept_id, user_type, user_from, user_to, mod_user_id, user_id],
        )

    return JsonResponse({"success": True})


@_require_app_admin
@csrf_exempt
def admin_user_management_create_api(request):
    """Create a new user in Mst_user + optionally set a local password."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    login_id  = data.get("login_id", "").strip()
    name      = data.get("name", "").strip()
    email     = data.get("email", "").strip()
    password  = data.get("password", "").strip()
    user_type = (data.get("user_type") or "E").strip().upper()
    dept_id   = data.get("dept_id") or None
    user_from = data.get("user_from") or None
    user_to   = data.get("user_to") or None

    if not login_id or not name:
        return JsonResponse({"error": "login_id and name are required"}, status=400)
    if user_type not in ("E", "N"):
        user_type = "E"

    from django.db import connections as _conn
    from .auth_backend import _sha256
    from .models import CbMstUserPassword

    with _conn["default"].cursor() as cursor:
        dbq(cursor, 
            "SELECT COUNT(*) FROM Mst_user WHERE UPPER(USER_LOGIN_ID) = UPPER(%s)",
            [login_id],
        )
        if cursor.fetchone()[0] > 0:
            return JsonResponse({"error": "Login ID already exists"}, status=400)

        dbq(cursor, "SELECT COALESCE(MAX(USER_ID), 0) + 1 FROM Mst_user")
        new_user_id = cursor.fetchone()[0]

        from .models import UserProfile
        try:
            admin_profile = UserProfile.objects.get(user_login_id=request.user.username)
            cr_user_id = admin_profile.user_id
        except Exception:
            cr_user_id = 1

        from_expr = "%s" if user_from else "CURDATE()"
        dbq(cursor, 
            "INSERT INTO Mst_user "
            "(USER_ID, USER_LOGIN_ID, USER_NAME, USER_EMAIL, USER_ACTIVE, "
            f" USER_TYPE_ID, DEPT_ID, USER_FROM, USER_TO, CR_USER_ID, CR_DT) "
            f"VALUES (%s, %s, %s, %s, 'Y', %s, %s, {from_expr}, %s, %s, NOW())",
            ([new_user_id, login_id, name, email or None, user_type, dept_id]
             + ([user_from] if user_from else [])
             + [user_to, cr_user_id]),
        )

    if password and new_user_id:
        CbMstUserPassword.objects.using("chathistory").create(
            user_id=new_user_id,
            password_hash=_sha256(password),
        )

    return JsonResponse({"success": True, "user_id": new_user_id})


@_require_app_admin
@csrf_exempt
def admin_user_management_set_password_api(request, user_id):
    """Set or reset a user's local password in cb_mst_user_password."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    password = data.get("password", "").strip()
    if not password:
        return JsonResponse({"error": "password is required"}, status=400)

    from .auth_backend import _sha256
    from .models import CbMstUserPassword

    CbMstUserPassword.objects.using("chathistory").update_or_create(
        user_id=user_id,
        defaults={"password_hash": _sha256(password)},
    )
    return JsonResponse({"success": True, "auth_type": "local"})


@_require_app_admin
@csrf_exempt
def admin_user_management_remove_password_api(request, user_id):
    """Remove local password — user falls back to AD authentication."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    from .models import CbMstUserPassword
    CbMstUserPassword.objects.using("chathistory").filter(user_id=user_id).delete()
    return JsonResponse({"success": True, "auth_type": "ad"})


@_require_app_admin
@csrf_exempt
def admin_user_management_toggle_active_api(request, user_id):
    """Toggle USER_ACTIVE in Mst_user (Y ↔ N)."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    from django.db import connections as _conn
    with _conn["default"].cursor() as cursor:
        dbq(cursor, 
            "SELECT USER_ACTIVE FROM Mst_user WHERE USER_ID = %s", [user_id]
        )
        row = cursor.fetchone()
        if not row:
            return JsonResponse({"error": "User not found"}, status=404)
        new_active = "N" if row[0] == "Y" else "Y"
        dbq(cursor, 
            "UPDATE Mst_user SET USER_ACTIVE = %s WHERE USER_ID = %s",
            [new_active, user_id],
        )
    return JsonResponse({"success": True, "active": new_active == "Y"})


# ── Travel Eligibility Master ─────────────────────────────────────────────────

_TRAVEL_MODE_LABELS = {"A": "Air", "R": "Rail", "C": "Coach"}

@require_permission("masters.travel_eligibility", "view")
def travel_eligibility_page(request):
    return render(request, "chatbot/masters/travel_eligibility.html")


@require_GET
def travel_eligibility_meta_api(request):
    from django.db import connections
    with connections["default"].cursor() as cursor:
        dbq(cursor, 
            "SELECT fs_category_id, fs_category_name FROM Mst_Fs_Category ORDER BY fs_category_name"
        )
        categories = [{"id": r[0], "name": r[1]} for r in cursor.fetchall()]
        dbq(cursor, 
            "SELECT rank_id, rank_name, rank_abrv, fs_category_id FROM Mst_Rank ORDER BY fs_category_id, rank_order, rank_name"
        )
        ranks = [{"id": r[0], "name": r[1], "abrv": r[2], "category_id": r[3]} for r in cursor.fetchall()]
    modes = [
        {"code": "A", "label": "Air"},
        {"code": "R", "label": "Rail"},
        {"code": "C", "label": "Coach"},
    ]
    return JsonResponse({"categories": categories, "ranks": ranks, "modes": modes})


@require_GET
def travel_eligibility_list_api(request):
    from django.db import connections
    category_id = request.GET.get("category_id")
    mode = request.GET.get("mode")
    q = request.GET.get("q", "").strip()
    page = max(1, int(request.GET.get("page", 1)))
    _ps = request.GET.get("page_size", "25")
    page_size = int(_ps) if _ps and _ps.isdigit() and int(_ps) in (25, 50, 75, 100) else 25

    conditions = []
    params = []
    if category_id:
        conditions.append("te.Fs_Category_Id = %s")
        params.append(category_id)
    if mode:
        conditions.append("te.Travel_Mode = %s")
        params.append(mode)
    if q:
        conditions.append("(r.rank_name LIKE %s OR r.rank_abrv LIKE %s OR te.Travel_Class LIKE %s OR c.fs_category_name LIKE %s)")
        like = f"%{q}%"
        params.extend([like, like, like, like])

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    offset = (page - 1) * page_size

    with connections["default"].cursor() as cursor:
        dbq(cursor, 
            f"""
            SELECT COUNT(*) FROM eos_Travel_Eligibility te {where}
            """,
            params,
        )
        total = cursor.fetchone()[0]

        dbq(cursor, 
            f"""
            SELECT te.Travel_Eligibility_Id, c.fs_category_name, r.rank_name, r.rank_abrv,
                   te.Travel_Mode, te.Travel_Class, te.Travel_Preference,
                   te.Eligible_From, te.Eligible_To
            FROM eos_Travel_Eligibility te
            LEFT JOIN Mst_Fs_Category c ON c.fs_category_id = te.Fs_Category_Id
            LEFT JOIN Mst_Rank r ON r.rank_id = te.Rank_Id
            {where}
            ORDER BY c.fs_category_name, r.rank_order, te.Travel_Mode, te.Travel_Preference
            LIMIT %s OFFSET %s
            """,
            params + [page_size, offset],
        )
        rows = cursor.fetchall()

    records = [
        {
            "id": r[0],
            "category": r[1] or "",
            "rank": r[2] or "",
            "rank_abrv": r[3] or "",
            "mode": _TRAVEL_MODE_LABELS.get(r[4], r[4]),
            "mode_code": r[4],
            "travel_class": r[5] or "",
            "preference": r[6],
            "eligible_from": str(r[7]) if r[7] else "",
            "eligible_to": str(r[8]) if r[8] else "",
        }
        for r in rows
    ]
    return JsonResponse({"records": records, "total": total, "page": page, "page_size": page_size})


@require_GET
def travel_eligibility_get_api(request, rec_id):
    from django.db import connections
    with connections["default"].cursor() as cursor:
        dbq(cursor, 
            """
            SELECT Travel_Eligibility_Id, Fs_Category_Id, Rank_Id,
                   Travel_Mode, Travel_Class, Travel_Preference,
                   Eligible_From, Eligible_To
            FROM eos_Travel_Eligibility WHERE Travel_Eligibility_Id = %s
            """,
            [rec_id],
        )
        row = cursor.fetchone()
    if not row:
        return JsonResponse({"error": "Not found"}, status=404)
    return JsonResponse({
        "id": row[0],
        "category_id": row[1],
        "rank_id": row[2],
        "mode": row[3],
        "travel_class": row[4] or "",
        "preference": row[5],
        "eligible_from": str(row[6]) if row[6] else "",
        "eligible_to": str(row[7]) if row[7] else "",
    })


@csrf_exempt
def travel_eligibility_save_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    _a = _get_access(request)
    if not _a["is_admin"]:
        try:
            _bpk = json.loads(request.body)
            _has_id = bool(_bpk.get("id"))
        except Exception:
            _has_id = False
        _pact = "edit" if _has_id else "add"
        if not _a["perms"].get("masters.travel_eligibility", {}).get(_pact):
            return JsonResponse({"error": "Permission denied"}, status=403)
    import json
    data = json.loads(request.body)
    rec_id = data.get("id")
    category_id = data.get("category_id")
    rank_id = data.get("rank_id")
    mode = data.get("mode", "").strip().upper()
    travel_class = data.get("travel_class", "").strip()
    preference = data.get("preference")
    eligible_from = data.get("eligible_from") or None
    eligible_to = data.get("eligible_to") or None

    if not all([category_id, rank_id, mode, travel_class, preference, eligible_from]):
        return JsonResponse({"error": "All required fields must be filled"}, status=400)
    if mode not in ("A", "R", "C"):
        return JsonResponse({"error": "Invalid travel mode"}, status=400)

    user_id = _audit.ops_user_id(request)
    from django.db import connections
    with connections["default"].cursor() as cursor:
        _before = _audit.snap(cursor, "masters.travel_eligibility", rec_id)
        if rec_id:
            dbq(cursor, 
                """UPDATE eos_Travel_Eligibility
                   SET Fs_Category_Id=%s, Rank_Id=%s, Travel_Mode=%s,
                       Travel_Class=%s, Travel_Preference=%s,
                       Eligible_From=%s, Eligible_To=%s,
                       Mod_User_Id=%s, Mod_Dt=NOW()
                   WHERE Travel_Eligibility_Id=%s""",
                [category_id, rank_id, mode, travel_class, preference,
                 eligible_from, eligible_to, user_id, rec_id],
            )
            new_id = rec_id
        else:
            dbq(cursor, 
                """INSERT INTO eos_Travel_Eligibility
                   (Fs_Category_Id, Rank_Id, Travel_Mode, Travel_Class,
                    Travel_Preference, Eligible_From, Eligible_To, Cr_User_Id, Cr_Dt)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())""",
                [category_id, rank_id, mode, travel_class, preference,
                 eligible_from, eligible_to, user_id],
            )
            new_id = cursor.lastrowid
        _audit.record_save(request, cursor, "masters.travel_eligibility", new_id, _before)
    return JsonResponse({"success": True, "id": new_id})


@csrf_exempt
def travel_eligibility_delete_api(request, rec_id):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    _a = _get_access(request)
    if not _a["is_admin"] and not _a["perms"].get("masters.travel_eligibility", {}).get("delete"):
        return JsonResponse({"error": "Permission denied"}, status=403)
    from django.db import connections
    with connections["default"].cursor() as cursor:
        _before = _audit.snap(cursor, "masters.travel_eligibility", rec_id)
        dbq(cursor, 
            "DELETE FROM eos_Travel_Eligibility WHERE Travel_Eligibility_Id=%s", [rec_id]
        )
    _audit.record_delete(request, "masters.travel_eligibility", rec_id, _before)
    return JsonResponse({"success": True})


# ─── Reporting Structure master ───────────────────────────────────────────────

@require_permission("masters.reporting_structure", "view")
def reporting_structure_page(request):
    return render(request, "chatbot/masters/reporting_structure.html")


@require_GET
def reporting_structure_meta_api(request):
    from django.db import connections
    with connections["default"].cursor() as cursor:
        dbq(cursor, "SELECT Fs_Category_Id, Fs_Category_Name FROM Mst_Fs_Category ORDER BY Fs_Category_Name")
        cats = [{"id": r[0], "name": r[1]} for r in cursor.fetchall()]
        dbq(cursor, "SELECT Rank_Id, Rank_Name, Rank_Abrv, Fs_Category_Id FROM Mst_Rank ORDER BY Rank_Name")
        ranks = [{"id": r[0], "name": r[1], "abrv": r[2], "category_id": r[3]} for r in cursor.fetchall()]
    return JsonResponse({"categories": cats, "ranks": ranks})


@require_GET
def reporting_structure_list_api(request):
    from django.db import connections
    _ps = request.GET.get("page_size", "25")
    page_size = int(_ps) if _ps and _ps.isdigit() and int(_ps) in (25, 50, 75, 100) else 25
    page = max(int(request.GET.get("page", 1)), 1)
    offset = (page - 1) * page_size
    cat_id  = request.GET.get("category_id", "")
    q       = request.GET.get("q", "").strip()

    where, params = ["1=1"], []
    if cat_id:
        where.append("rs.Fs_Category_Id = %s"); params.append(cat_id)
    if q:
        like = f"%{q}%"
        where.append("(r.Rank_Name LIKE %s OR r.Rank_Abrv LIKE %s OR rr.Rank_Name LIKE %s OR rr.Rank_Abrv LIKE %s OR c.Fs_Category_Name LIKE %s)")
        params += [like, like, like, like, like]

    sql_base = """
        FROM eos_Reporting_Structure rs
        JOIN Mst_Fs_Category c  ON c.Fs_Category_Id  = rs.Fs_Category_Id
        JOIN Mst_Rank r          ON r.Rank_Id          = rs.Rank_Id
        JOIN Mst_Rank rr         ON rr.Rank_Id         = rs.Reporting_Rank_Id
        WHERE """ + " AND ".join(where)

    with connections["default"].cursor() as cursor:
        dbq(cursor, "SELECT COUNT(*) " + sql_base, params)
        total = cursor.fetchone()[0]
        dbq(cursor, 
            "SELECT rs.Reporting_Structure_Id, c.Fs_Category_Name, r.Rank_Name, r.Rank_Abrv, rr.Rank_Name, rr.Rank_Abrv "
            + sql_base + " ORDER BY c.Fs_Category_Name, r.Rank_Name LIMIT %s OFFSET %s",
            params + [page_size, offset],
        )
        rows = [
            {"id": row[0], "category": row[1],
             "rank": row[2], "rank_abrv": row[3],
             "reporting_rank": row[4], "reporting_rank_abrv": row[5]}
            for row in cursor.fetchall()
        ]
    return JsonResponse({"records": rows, "total": total, "page": page, "page_size": page_size})


@require_GET
def reporting_structure_get_api(request, rec_id):
    from django.db import connections
    with connections["default"].cursor() as cursor:
        dbq(cursor, 
            "SELECT Reporting_Structure_Id, Fs_Category_Id, Rank_Id, Reporting_Rank_Id "
            "FROM eos_Reporting_Structure WHERE Reporting_Structure_Id=%s", [rec_id]
        )
        row = cursor.fetchone()
    if not row:
        return JsonResponse({"error": "Not found"}, status=404)
    return JsonResponse({"id": row[0], "category_id": row[1], "rank_id": row[2], "reporting_rank_id": row[3]})


@csrf_exempt
def reporting_structure_save_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    _a = _get_access(request)
    if not _a["is_admin"]:
        try:
            _bpk = json.loads(request.body)
            _has_id = bool(_bpk.get("id"))
        except Exception:
            _has_id = False
        _pact = "edit" if _has_id else "add"
        if not _a["perms"].get("masters.reporting_structure", {}).get(_pact):
            return JsonResponse({"error": "Permission denied"}, status=403)
    import json as _json
    from django.db import connections
    body = _json.loads(request.body)
    rec_id       = body.get("id")
    category_id  = body.get("category_id")
    rank_id      = body.get("rank_id")
    rep_rank_id  = body.get("reporting_rank_id")
    user_id      = _audit.ops_user_id(request)

    if not all([category_id, rank_id, rep_rank_id]):
        return JsonResponse({"error": "category_id, rank_id and reporting_rank_id are required"}, status=400)

    with connections["default"].cursor() as cursor:
        _before = _audit.snap(cursor, "masters.reporting_structure", rec_id)
        if rec_id:
            dbq(cursor, 
                "UPDATE eos_Reporting_Structure SET Fs_Category_Id=%s, Rank_Id=%s, Reporting_Rank_Id=%s, Mod_User_Id=%s, Mod_Dt=NOW() WHERE Reporting_Structure_Id=%s",
                [category_id, rank_id, rep_rank_id, user_id, rec_id],
            )
            new_id = rec_id
        else:
            dbq(cursor, 
                "INSERT INTO eos_Reporting_Structure (Fs_Category_Id, Rank_Id, Reporting_Rank_Id, Cr_User_Id, Cr_Dt) VALUES (%s, %s, %s, %s, NOW())",
                [category_id, rank_id, rep_rank_id, user_id],
            )
            new_id = cursor.lastrowid
        _audit.record_save(request, cursor, "masters.reporting_structure", new_id, _before)
    return JsonResponse({"success": True, "id": new_id})


@csrf_exempt
def reporting_structure_delete_api(request, rec_id):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    _a = _get_access(request)
    if not _a["is_admin"] and not _a["perms"].get("masters.reporting_structure", {}).get("delete"):
        return JsonResponse({"error": "Permission denied"}, status=403)
    from django.db import connections
    with connections["default"].cursor() as cursor:
        _before = _audit.snap(cursor, "masters.reporting_structure", rec_id)
        dbq(cursor, "DELETE FROM eos_Reporting_Structure WHERE Reporting_Structure_Id=%s", [rec_id])
    _audit.record_delete(request, "masters.reporting_structure", rec_id, _before)
    return JsonResponse({"success": True})


# ── Job Descriptions ─────────────────────────────────────────────────────────

@require_permission("masters.job_descriptions", "view")
def job_description_page(request):
    return render(request, "chatbot/masters/job_description.html")


@require_GET
def job_description_meta_api(request):
    from django.db import connections
    with connections["default"].cursor() as cur:
        dbq(cur, "SELECT Fs_Category_Id, Fs_Category_Name FROM Mst_Fs_Category ORDER BY Fs_Category_Name")
        cats = [{"id": r[0], "name": r[1]} for r in cur.fetchall()]
        dbq(cur, "SELECT Rank_Id, Rank_Name, Rank_Abrv, Fs_Category_Id FROM Mst_Rank ORDER BY Rank_Name")
        ranks = [{"id": r[0], "name": r[1], "abrv": r[2], "category_id": r[3]} for r in cur.fetchall()]
    return JsonResponse({"categories": cats, "ranks": ranks})


@require_GET
def job_description_list_api(request):
    from django.db import connections
    cat_id = request.GET.get("category_id", "")
    q      = request.GET.get("q", "").strip()
    active = request.GET.get("active", "")
    _ps    = request.GET.get("page_size", "25")
    page_size = int(_ps) if _ps and _ps.isdigit() and int(_ps) in (25, 50, 75, 100) else 25
    try:
        page = max(1, int(request.GET.get("page", 1)))
    except ValueError:
        page = 1

    where, params = [], []
    if cat_id:
        where.append("h.Fs_Category_Id = %s"); params.append(cat_id)
    if active in ("Y", "N"):
        where.append("h.JD_Hdr_Active = %s"); params.append(active)
    if q:
        where.append("(h.JD_Hdr_Description LIKE %s OR r.Rank_Name LIKE %s OR c.Fs_Category_Name LIKE %s)")
        params += [f"%{q}%", f"%{q}%", f"%{q}%"]

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    base = f"""
        FROM eos_Job_Description_Hdr h
        JOIN Mst_Fs_Category c ON c.Fs_Category_Id = h.Fs_Category_Id
        JOIN Mst_Rank r ON r.Rank_Id = h.Rank_Id
        {where_sql}
    """
    with connections["default"].cursor() as cur:
        dbq(cur, f"SELECT COUNT(*) {base}", params)
        total = cur.fetchone()[0]
        offset = (page - 1) * page_size
        dbq(cur, 
            f"SELECT h.JD_Hdr_Id, c.Fs_Category_Name, r.Rank_Name, r.Rank_Abrv, h.JD_Hdr_Description, h.JD_Hdr_Order, h.JD_Hdr_Active {base} ORDER BY h.Fs_Category_Id, h.Rank_Id, h.JD_Hdr_Order LIMIT %s OFFSET %s",
            params + [page_size, offset],
        )
        rows = cur.fetchall()
    records = [
        {"id": r[0], "category": r[1], "rank": r[2], "rank_abrv": r[3],
         "description": r[4], "display_order": r[5], "active": r[6]}
        for r in rows
    ]
    return JsonResponse({"records": records, "total": total})


@require_GET
def job_description_get_api(request, hdr_id):
    from django.db import connections
    with connections["default"].cursor() as cur:
        dbq(cur, 
            "SELECT h.JD_Hdr_Id, h.Fs_Category_Id, c.Fs_Category_Name, h.Rank_Id, r.Rank_Name, r.Rank_Abrv, h.JD_Hdr_Description, h.JD_Hdr_Order, h.JD_Hdr_Active "
            "FROM eos_Job_Description_Hdr h "
            "JOIN Mst_Fs_Category c ON c.Fs_Category_Id = h.Fs_Category_Id "
            "JOIN Mst_Rank r ON r.Rank_Id = h.Rank_Id "
            "WHERE h.JD_Hdr_Id = %s",
            [hdr_id],
        )
        h = cur.fetchone()
        if not h:
            return JsonResponse({"error": "Not found"}, status=404)
        dbq(cur, 
            "SELECT JD_Dtl_Id, JD_Dtl_Description, JD_Dtl_Order, JD_Dtl_Active FROM eos_Job_Description_Dtl WHERE JD_Hdr_Id = %s ORDER BY JD_Dtl_Order",
            [hdr_id],
        )
        dtls = [{"id": r[0], "description": r[1], "display_order": r[2], "active": r[3]} for r in cur.fetchall()]
    return JsonResponse({
        "id": h[0], "category_id": h[1], "category": h[2],
        "rank_id": h[3], "rank": h[4], "rank_abrv": h[5],
        "description": h[6], "display_order": h[7], "active": h[8],
        "lines": dtls,
    })


@csrf_exempt
def job_description_save_hdr_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    _a = _get_access(request)
    if not _a["is_admin"]:
        try:
            _bpk = json.loads(request.body)
            _has_id = bool(_bpk.get("id"))
        except Exception:
            _has_id = False
        _pact = "edit" if _has_id else "add"
        if not _a["perms"].get("masters.job_descriptions", {}).get(_pact):
            return JsonResponse({"error": "Permission denied"}, status=403)
    import json as _json
    body        = _json.loads(request.body)
    hdr_id      = body.get("id")
    category_id = body.get("category_id")
    rank_id     = body.get("rank_id")
    description = (body.get("description") or "").strip()
    order       = body.get("display_order", 1)
    active      = body.get("active", "Y")
    user_id     = _audit.ops_user_id(request)

    if not all([category_id, rank_id, description]):
        return JsonResponse({"error": "category_id, rank_id and description are required"}, status=400)

    from django.db import connections
    with connections["default"].cursor() as cur:
        _before = _audit.snap(cur, "masters.job_descriptions", hdr_id)
        if hdr_id:
            dbq(cur, 
                "UPDATE eos_Job_Description_Hdr SET Fs_Category_Id=%s, Rank_Id=%s, JD_Hdr_Description=%s, JD_Hdr_Order=%s, JD_Hdr_Active=%s, Mod_User_Id=%s, Mod_Dt=NOW() WHERE JD_Hdr_Id=%s",
                [category_id, rank_id, description, order, active, user_id, hdr_id],
            )
            new_id = hdr_id
        else:
            dbq(cur, "SELECT COALESCE(MAX(JD_Hdr_Id), 0) + 1 FROM eos_Job_Description_Hdr")
            new_id = cur.fetchone()[0]
            dbq(cur, 
                "INSERT INTO eos_Job_Description_Hdr (JD_Hdr_Id, Fs_Category_Id, Rank_Id, JD_Hdr_Description, JD_Hdr_Order, JD_Hdr_Active, Cr_User_Id, Cr_Dt) VALUES (%s,%s,%s,%s,%s,%s,%s,NOW())",
                [new_id, category_id, rank_id, description, order, active, user_id],
            )
        _audit.record_save(request, cur, "masters.job_descriptions", new_id, _before)
    return JsonResponse({"success": True, "id": new_id})


@csrf_exempt
def job_description_delete_hdr_api(request, hdr_id):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    _a = _get_access(request)
    if not _a["is_admin"] and not _a["perms"].get("masters.job_descriptions", {}).get("delete"):
        return JsonResponse({"error": "Permission denied"}, status=403)
    from django.db import connections
    with connections["default"].cursor() as cur:
        _before = _audit.snap(cur, "masters.job_descriptions", hdr_id)
        dbq(cur, "DELETE FROM eos_Job_Description_Dtl WHERE JD_Hdr_Id=%s", [hdr_id])
        dbq(cur, "DELETE FROM eos_Job_Description_Hdr WHERE JD_Hdr_Id=%s", [hdr_id])
    _audit.record_delete(request, "masters.job_descriptions", hdr_id, _before)
    return JsonResponse({"success": True})


@csrf_exempt
def job_description_save_dtl_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    _a = _get_access(request)
    if not _a["is_admin"]:
        try:
            _bpk = json.loads(request.body)
            _has_id = bool(_bpk.get("id"))
        except Exception:
            _has_id = False
        _pact = "edit" if _has_id else "add"
        if not _a["perms"].get("masters.job_descriptions", {}).get(_pact):
            return JsonResponse({"error": "Permission denied"}, status=403)
    import json as _json
    body        = _json.loads(request.body)
    dtl_id      = body.get("id")
    hdr_id      = body.get("hdr_id")
    description = (body.get("description") or "").strip()
    order       = body.get("display_order", 1)
    active      = body.get("active", "Y")
    user_id     = _audit.ops_user_id(request)

    if not description:
        return JsonResponse({"error": "description is required"}, status=400)

    from django.db import connections
    with connections["default"].cursor() as cur:
        if dtl_id:
            dbq(cur, 
                "UPDATE eos_Job_Description_Dtl SET JD_Dtl_Description=%s, JD_Dtl_Order=%s, JD_Dtl_Active=%s, Mod_User_Id=%s, Mod_Dt=NOW() WHERE JD_Dtl_Id=%s",
                [description, order, active, user_id, dtl_id],
            )
            new_id = dtl_id
        else:
            dbq(cur, "SELECT COALESCE(MAX(JD_Dtl_Id), 0) + 1 FROM eos_Job_Description_Dtl")
            new_id = cur.fetchone()[0]
            dbq(cur, 
                "INSERT INTO eos_Job_Description_Dtl (JD_Dtl_Id, JD_Hdr_Id, JD_Dtl_Description, JD_Dtl_Order, JD_Dtl_Active, Cr_User_Id, Cr_Dt) VALUES (%s,%s,%s,%s,%s,%s,NOW())",
                [new_id, hdr_id, description, order, active, user_id],
            )
    _audit.record_action(request, ("update" if dtl_id else "create"), "masters.job_descriptions",
                         new_id, ("Detail line: " + description)[:200],
                         {"JD_Dtl_Description": {"old": None, "new": description}})
    return JsonResponse({"success": True, "id": new_id})


@csrf_exempt
def job_description_delete_dtl_api(request, dtl_id):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    _a = _get_access(request)
    if not _a["is_admin"] and not _a["perms"].get("masters.job_descriptions", {}).get("delete"):
        return JsonResponse({"error": "Permission denied"}, status=403)
    from django.db import connections
    with connections["default"].cursor() as cur:
        dbq(cur, "DELETE FROM eos_Job_Description_Dtl WHERE JD_Dtl_Id=%s", [dtl_id])
    _audit.record_action(request, "delete", "masters.job_descriptions", dtl_id,
                         "Detail line #%s" % dtl_id, None)
    return JsonResponse({"success": True})


# ── Competency Master ────────────────────────────────────────────────────────

COMPETENCY_DEPT_IDS = (3, 14, 35)

def _get_competency_depts(cur):
    dbq(cur, 
        "SELECT Dept_Id, Dept_Name FROM Mst_Department WHERE Dept_Id IN %s ORDER BY Dept_Name",
        [COMPETENCY_DEPT_IDS],
    )
    return [{"id": r[0], "name": r[1]} for r in cur.fetchall()]


@require_permission("masters.competency", "view")
def competency_page(request):
    return render(request, "chatbot/masters/competency.html")


@require_GET
def competency_meta_api(request):
    from django.db import connections
    with connections["default"].cursor() as cur:
        depts = _get_competency_depts(cur)
    return JsonResponse({"depts": depts})


@require_GET
def competency_list_api(request):
    dept_id = request.GET.get("dept_id", "")
    q       = request.GET.get("q", "").strip()
    active  = request.GET.get("active", "")
    page    = max(1, int(request.GET.get("page", 1)))
    size    = 25

    where, params = ["1=1"], []
    if dept_id:
        where.append("Dept_Id = %s"); params.append(dept_id)
    if q:
        where.append("Competency_Name LIKE %s"); params.append(f"%{q}%")
    if active in ("Y", "N"):
        where.append("Active = %s"); params.append(active)

    clause = " AND ".join(where)
    from django.db import connections
    with connections["default"].cursor() as cur:
        dbq(cur, f"SELECT COUNT(*) FROM eos_Mst_Competency WHERE {clause}", params)
        total = cur.fetchone()[0]
        dbq(cur, 
            f"SELECT Competency_Id, Competency_Name, Dept_Id, Active FROM eos_Mst_Competency WHERE {clause} ORDER BY Dept_Id, Competency_Name LIMIT %s OFFSET %s",
            params + [size, (page - 1) * size],
        )
        rows = cur.fetchall()
        dept_map = {d["id"]: d["name"] for d in _get_competency_depts(cur)}
    records = [
        {"id": r[0], "name": r[1], "dept_id": r[2], "dept": dept_map.get(r[2], str(r[2])), "active": r[3]}
        for r in rows
    ]
    return JsonResponse({"records": records, "total": total, "page": page, "size": size})


@require_GET
def competency_get_api(request, rec_id):
    from django.db import connections
    with connections["default"].cursor() as cur:
        dbq(cur, 
            "SELECT Competency_Id, Competency_Name, Dept_Id, Active FROM eos_Mst_Competency WHERE Competency_Id=%s",
            [rec_id],
        )
        row = cur.fetchone()
    if not row:
        return JsonResponse({"error": "Not found"}, status=404)
    return JsonResponse({"id": row[0], "name": row[1], "dept_id": row[2], "active": row[3]})


@csrf_exempt
def competency_save_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    _a = _get_access(request)
    if not _a["is_admin"]:
        try:
            _bpk = json.loads(request.body)
            _has_id = bool(_bpk.get("id"))
        except Exception:
            _has_id = False
        _pact = "edit" if _has_id else "add"
        if not _a["perms"].get("masters.competency", {}).get(_pact):
            return JsonResponse({"error": "Permission denied"}, status=403)
    data      = json.loads(request.body)
    rec_id    = data.get("id")
    name      = data.get("name", "").strip()[:50]
    dept_id   = int(data.get("dept_id", 0))
    active    = "Y" if data.get("active") == "Y" else "N"
    user_id   = _audit.ops_user_id(request)

    if not name or not dept_id:
        return JsonResponse({"error": "Name and department are required"}, status=400)

    from django.db import connections
    with connections["default"].cursor() as cur:
        _before = _audit.snap(cur, "masters.competency", rec_id)
        if rec_id:
            dbq(cur, 
                "UPDATE eos_Mst_Competency SET Competency_Name=%s, Dept_Id=%s, Active=%s, Mod_User_Id=%s, Mod_Dt=NOW() WHERE Competency_Id=%s",
                [name, dept_id, active, user_id, rec_id],
            )
            new_id = rec_id
        else:
            dbq(cur, "SELECT COALESCE(MAX(Competency_Id), 0) + 1 FROM eos_Mst_Competency")
            new_id = cur.fetchone()[0]
            dbq(cur, 
                "INSERT INTO eos_Mst_Competency (Competency_Id, Competency_Name, Dept_Id, Active, Cr_User_Id, Cr_Dt) VALUES (%s,%s,%s,%s,%s,NOW())",
                [new_id, name, dept_id, active, user_id],
            )
        _audit.record_save(request, cur, "masters.competency", new_id, _before)
    return JsonResponse({"success": True, "id": new_id})


@csrf_exempt
def competency_delete_api(request, rec_id):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    _a = _get_access(request)
    if not _a["is_admin"] and not _a["perms"].get("masters.competency", {}).get("delete"):
        return JsonResponse({"error": "Permission denied"}, status=403)
    from django.db import connections
    with connections["default"].cursor() as cur:
        _before = _audit.snap(cur, "masters.competency", rec_id)
        dbq(cur, "DELETE FROM eos_Mst_Competency WHERE Competency_Id=%s", [rec_id])
    _audit.record_delete(request, "masters.competency", rec_id, _before)
    return JsonResponse({"success": True})


# ── User permission self-query ───────────────────────────────────────────────

@require_GET
def me_perms_api(request):
    """Return the current user's permissions for one or all menu keys.
    ?key=masters.rigs  → single key dict
    (no param)         → full perms dict
    """
    access = _get_access(request)
    if access["is_admin"]:
        # Admin sees everything as fully granted
        key = request.GET.get("key")
        full = {"view": True, "add": True, "edit": True, "delete": True, "export": True}
        if key:
            return JsonResponse({"is_admin": True, **full})
        return JsonResponse({"is_admin": True, "perms": {}})

    key = request.GET.get("key")
    if key:
        p = access["perms"].get(key, {})
        return JsonResponse({
            "is_admin": False,
            "can_view":   bool(p.get("view")),
            "can_add":    bool(p.get("add")),
            "can_edit":   bool(p.get("edit")),
            "can_delete": bool(p.get("delete")),
            "can_export": bool(p.get("export")),
        })
    return JsonResponse({"is_admin": False, "perms": access["perms"]})

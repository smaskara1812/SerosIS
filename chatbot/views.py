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
from .permissions import require_permission

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
    return render(request, "chatbot/masters/index.html")

# ── Cost Centre Type Master ───────────────────────────────────────────────────

@require_permission("masters.cost_centre_types", "view")
def cost_centre_type_page(request):
    return render(request, "chatbot/masters/cost_centre_type.html")

@require_GET
def cost_centre_type_list_api(request):
    from django.db import connections
    with connections["default"].cursor() as cursor:
        cursor.execute("""
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
        cursor.execute("""
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
    from django.db import connections
    body = json.loads(request.body)
    type_id  = body.get("Cost_Centre_Type_Id") or None
    name     = (body.get("Cost_Centre_Type_Name") or "").strip()
    short    = (body.get("Cost_Centre_Type_Shortname") or "").strip()
    active   = body.get("Cost_Centre_Type_Active", "Y")
    if not name or not short:
        return JsonResponse({"error": "Type Name and Short Name are required"}, status=400)
    now = datetime.now()
    cr_user_id = 1
    with connections["default"].cursor() as cursor:
        if type_id:
            cursor.execute("""
                UPDATE eos_Mst_Cost_Centre_Type
                SET Cost_Centre_Type_Name=%s, Cost_Centre_Type_Shortname=%s,
                    Cost_Centre_Type_Active=%s, Mod_User_Id=%s, Mod_Dt=%s
                WHERE Cost_Centre_Type_Id=%s
            """, [name, short, active, cr_user_id, now, type_id])
            return JsonResponse({"success": True, "Cost_Centre_Type_Id": type_id, "action": "updated"})
        else:
            cursor.execute("SELECT COALESCE(MAX(Cost_Centre_Type_Id), 0) + 1 FROM eos_Mst_Cost_Centre_Type")
            new_id = cursor.fetchone()[0]
            cursor.execute("""
                INSERT INTO eos_Mst_Cost_Centre_Type
                    (Cost_Centre_Type_Id, Cost_Centre_Type_Name, Cost_Centre_Type_Shortname,
                     Cost_Centre_Type_Active, Cr_User_Id, Cr_Dt)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, [new_id, name, short, "Y", cr_user_id, now])
            return JsonResponse({"success": True, "Cost_Centre_Type_Id": new_id, "action": "inserted"})

@csrf_exempt
def cost_centre_type_deactivate_api(request, type_id):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    from django.db import connections
    with connections["default"].cursor() as cursor:
        cursor.execute("""
            UPDATE eos_Mst_Cost_Centre_Type
            SET Cost_Centre_Type_Active='N', Mod_User_Id=%s, Mod_Dt=%s
            WHERE Cost_Centre_Type_Id=%s
        """, [1, datetime.now(), type_id])
    return JsonResponse({"success": True})

# ── Cost Centre Master ────────────────────────────────────────────────────────

@require_permission("masters.cost_centres", "view")
def cost_centre_page(request):
    return render(request, "chatbot/masters/cost_centre.html")

@require_GET
def cost_centre_meta_api(request):
    from django.db import connections
    with connections["default"].cursor() as cursor:
        cursor.execute("""
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
        cursor.execute(sql, params)
        cols = [c[0] for c in cursor.description]
        rows = [dict(zip(cols, row)) for row in cursor.fetchall()]
    return JsonResponse({"results": rows})

@require_GET
def cost_centre_list_api(request):
    from django.db import connections
    with connections["default"].cursor() as cursor:
        cursor.execute("""
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
        cursor.execute("""
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
    cr_user_id = 1
    with connections["default"].cursor() as cursor:
        if cc_id:
            cursor.execute("""
                UPDATE eos_Mst_Cost_Centre
                SET Cost_Centre_Name=%s, Old_Cost_Centre_Name=%s, Cost_Centre_Type_Id=%s,
                    Rig_Id=%s, Location_Id=%s, Cost_Centre_Active=%s,
                    Mod_User_Id=%s, Mod_Dt=%s
                WHERE Cost_Centre_Id=%s
            """, [name, old_name, type_id, rig_id, loc_id, active, cr_user_id, now, cc_id])
            return JsonResponse({"success": True, "Cost_Centre_Id": cc_id, "action": "updated"})
        else:
            cursor.execute("SELECT COALESCE(MAX(Cost_Centre_Id), 0) + 1 FROM eos_Mst_Cost_Centre")
            new_id = cursor.fetchone()[0]
            cursor.execute("""
                INSERT INTO eos_Mst_Cost_Centre
                    (Cost_Centre_Id, Cost_Centre_Name, Old_Cost_Centre_Name,
                     Cost_Centre_Type_Id, Rig_Id, Location_Id,
                     Cost_Centre_Active, Cr_User_Id, Cr_Dt)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, [new_id, name, old_name, type_id, rig_id, loc_id, "Y", cr_user_id, now])
            return JsonResponse({"success": True, "Cost_Centre_Id": new_id, "action": "inserted"})

@csrf_exempt
def cost_centre_deactivate_api(request, cc_id):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    from django.db import connections
    with connections["default"].cursor() as cursor:
        cursor.execute("""
            UPDATE eos_Mst_Cost_Centre
            SET Cost_Centre_Active='N', Mod_User_Id=%s, Mod_Dt=%s
            WHERE Cost_Centre_Id=%s
        """, [1, datetime.now(), cc_id])
    return JsonResponse({"success": True})

# ── Operator Master Form ──────────────────────────────────────────────────────

@require_permission("masters.operators", "view")
def operator_master_page(request):
    return render(request, "chatbot/masters/operator.html")

@require_GET
def operator_list_api(request):
    from django.db import connections
    with connections["default"].cursor() as cursor:
        cursor.execute("""
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
        cursor.execute("""
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
    cr_user_id = 1
    with connections["default"].cursor() as cursor:
        if op_id:
            cursor.execute("""
                UPDATE eos_Mst_Operator
                SET Operator_Name=%s, Operator_Short_Name=%s, Operator_SAP_Code=%s,
                    WBS_Client_Code=%s, Country_Id=%s, Location_Id=%s,
                    Contact_Person=%s, Tel_No=%s, Email_Id=%s,
                    Operator_Active=%s, Mod_User_Id=%s, Mod_Dt=%s
                WHERE Operator_Id=%s
            """, [name, short_name, sap_code, wbs_code, country_id, loc_id,
                  contact, tel, email, active, cr_user_id, now, op_id])
            return JsonResponse({"success": True, "Operator_Id": op_id, "action": "updated"})
        else:
            cursor.execute("SELECT COALESCE(MAX(Operator_Id), 0) + 1 FROM eos_Mst_Operator")
            new_id = cursor.fetchone()[0]
            cursor.execute("""
                INSERT INTO eos_Mst_Operator
                    (Operator_Id, Operator_Name, Operator_Short_Name, Operator_SAP_Code,
                     WBS_Client_Code, Country_Id, Location_Id, Contact_Person,
                     Tel_No, Email_Id, Operator_Active, Cr_User_Id, Cr_Dt)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, [new_id, name, short_name, sap_code, wbs_code, country_id, loc_id,
                  contact, tel, email, "Y", cr_user_id, now])
            return JsonResponse({"success": True, "Operator_Id": new_id, "action": "inserted"})

@csrf_exempt
def operator_deactivate_api(request, op_id):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    from django.db import connections
    with connections["default"].cursor() as cursor:
        cursor.execute("""
            UPDATE eos_Mst_Operator
            SET Operator_Active='N', Mod_User_Id=%s, Mod_Dt=%s
            WHERE Operator_Id=%s
        """, [1, datetime.now(), op_id])
    return JsonResponse({"success": True})

@require_GET
def operator_countries_search_api(request):
    from django.db import connections
    q      = request.GET.get("q", "").strip()
    offset = max(0, int(request.GET.get("offset", 0)))
    limit  = min(50, max(1, int(request.GET.get("limit", 20))))
    with connections["default"].cursor() as cursor:
        cursor.execute("""
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
            cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE {col}=%s", [type_id])
            count = cursor.fetchone()[0]
            if count > 0:
                refs.append({"label": label, "count": count})
    return JsonResponse({"can_delete": len(refs) == 0, "references": refs})


@csrf_exempt
def cost_centre_type_delete_api(request, type_id):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    from django.db import connections
    with connections["default"].cursor() as cursor:
        for table, col in [
            ("eos_Mst_Cost_Centre", "Cost_Centre_Type_Id"),
            ("eos_Mst_HSE_Manhours_Party", "Cost_Centre_Type_Id"),
        ]:
            cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE {col}=%s", [type_id])
            if cursor.fetchone()[0] > 0:
                return JsonResponse({"error": "Record is still referenced and cannot be deleted."}, status=409)
        cursor.execute("DELETE FROM eos_Mst_Cost_Centre_Type WHERE Cost_Centre_Type_Id=%s", [type_id])
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
            cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE {col}=%s", [cc_id])
            count = cursor.fetchone()[0]
            if count > 0:
                refs.append({"label": label, "count": count})
    return JsonResponse({"can_delete": len(refs) == 0, "references": refs})


@csrf_exempt
def cost_centre_delete_api(request, cc_id):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    from django.db import connections
    with connections["default"].cursor() as cursor:
        for table, col in [
            ("eos_Invoice_Hdr", "Cost_Centre_Id"),
            ("eos_Actual_Crew_Expense", "Cost_Centre_Id"),
            ("eos_Budgeted_Crew_Expense", "Cost_Centre_Id"),
            ("eos_Cost_Centre_To_Company_Mapping", "Cost_Centre_Id"),
            ("eos_Fs_Emp_To_CC_Mapping", "Cost_Centre_Id"),
            ("eos_Proj_To_Cost_Centre_Mapping", "Cost_Centre_Id"),
        ]:
            cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE {col}=%s", [cc_id])
            if cursor.fetchone()[0] > 0:
                return JsonResponse({"error": "Record is still referenced and cannot be deleted."}, status=409)
        cursor.execute("DELETE FROM eos_Mst_Cost_Centre WHERE Cost_Centre_Id=%s", [cc_id])
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
            cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE {col}=%s", [op_id])
            count = cursor.fetchone()[0]
            if count > 0:
                refs.append({"label": label, "count": count})
    return JsonResponse({"can_delete": len(refs) == 0, "references": refs})


@csrf_exempt
def operator_delete_api(request, op_id):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    from django.db import connections
    with connections["default"].cursor() as cursor:
        for table, col in [
            ("eos_Mst_Project", "Operator_Id"),
            ("eos_Mst_Project_Contract", "Operator_Id"),
            ("eos_Tender_Dtl", "Operator_Id"),
            ("eos_Competitor_Contract_Dtl", "Operator_Id"),
        ]:
            cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE {col}=%s", [op_id])
            if cursor.fetchone()[0] > 0:
                return JsonResponse({"error": "Record is still referenced and cannot be deleted."}, status=409)
        cursor.execute("DELETE FROM eos_Mst_Operator WHERE Operator_Id=%s", [op_id])
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
            cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE {col}=%s", [rig_id])
            count = cursor.fetchone()[0]
            if count > 0:
                refs.append({"label": label, "count": count})
    return JsonResponse({"can_delete": len(refs) == 0, "references": refs})


@csrf_exempt
def rig_master_delete_api(request, rig_id):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    from django.db import connections
    with connections["default"].cursor() as cursor:
        for table, col in [
            ("eos_Mst_Cost_Centre", "Rig_Id"),
            ("eos_Incident_Details", "Rig_Id"),
            ("eos_Hazard_ID_Card", "Rig_Id"),
            ("eos_Drilling_Hdr", "Rig_Id"),
            ("eos_Crew_Grp_Dtl", "Rig_Id"),
            ("eos_Mst_Crew_Grp", "Rig_Id"),
        ]:
            cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE {col}=%s", [rig_id])
            if cursor.fetchone()[0] > 0:
                return JsonResponse({"error": "Record is still referenced and cannot be deleted."}, status=409)
        cursor.execute("DELETE FROM eos_Mst_Rig WHERE Rig_Id=%s", [rig_id])
    return JsonResponse({"success": True})


# ── Rig Master Form ───────────────────────────────────────────────────────────

@require_permission("masters.rigs", "view")
def rig_master_page(request):
    return render(request, "chatbot/rigs/master.html")


@require_GET
def rig_master_meta_api(request):
    from django.db import connections
    with connections["default"].cursor() as cursor:
        cursor.execute("""
            SELECT rs.Rig_Subtype_Id, rs.Rig_Subtype_Name, rs.Rig_Type_Id, rt.Rig_Type_Name
            FROM Mst_Rig_Subtype rs
            JOIN Mst_Rig_Type rt ON rs.Rig_Type_Id = rt.Rig_Type_Id
            ORDER BY rs.Rig_Subtype_Name
        """)
        cols = [c[0] for c in cursor.description]
        subtypes = [dict(zip(cols, row)) for row in cursor.fetchall()]

        cursor.execute("SELECT Rig_Type_Id, Rig_Type_Name FROM Mst_Rig_Type ORDER BY Rig_Type_Name")
        cols = [c[0] for c in cursor.description]
        types = [dict(zip(cols, row)) for row in cursor.fetchall()]

    return JsonResponse({"subtypes": subtypes, "types": types})


@require_GET
def rig_master_search_api(request):
    from django.db import connections
    q = request.GET.get("q", "").strip()
    with connections["default"].cursor() as cursor:
        if q:
            cursor.execute("""
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
            cursor.execute("""
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
        cursor.execute("""
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

    from django.db import connections
    body = json.loads(request.body)
    rig_id = body.get("Rig_Id") or None

    required = ["Rig_Name", "Rig_Short_Name", "Rig_Subtype_Id", "Rig_Type_Id", "Rig_Built_Dt", "Rig_From"]
    for field in required:
        if not body.get(field):
            return JsonResponse({"error": f"{field} is required"}, status=400)

    now = datetime.now()
    cr_user_id = 1  # placeholder until auth

    with connections["default"].cursor() as cursor:
        if rig_id:
            rig_active = body.get("Rig_Active", "Y")
            if rig_active not in ("Y", "N"):
                rig_active = "Y"
            cursor.execute("""
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
            return JsonResponse({"success": True, "Rig_Id": rig_id, "action": "updated"})
        else:
            cursor.execute("SELECT COALESCE(MAX(Rig_Id), 0) + 1 FROM eos_Mst_Rig")
            new_id = cursor.fetchone()[0]
            cursor.execute("""
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


@require_permission("listings.incidents", "view")
def listings_incidents_page(request):
    return render(request, "chatbot/listings/incidents.html")


@require_permission("listings.hazard_cards", "view")
def listings_hazard_cards_page(request):
    return render(request, "chatbot/listings/hazard_cards.html")


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
    from .analytics.listings import get_hazard_card_listing
    from .pdf_reports import generate_hazard_cards_pdf
    g = request.GET
    year = g.get("year")
    rig  = g.get("rig") or None
    result = get_hazard_card_listing(
        page=1, page_size=2000,
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
    return render(request, "chatbot/listings/employees.html")


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
    return render(request, "chatbot/listings/crew_rotations.html")


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
    return render(request, "chatbot/listings/staff.html")


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
    return render(request, "chatbot/listings/invoices.html")


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
    return render(request, "chatbot/listings/certificates.html")


@require_permission("listings.users", "view")
def listings_users_page(request):
    return render(request, "chatbot/listings/users.html")


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
        cursor.execute(sql_count, params)
        total = cursor.fetchone()[0]
        cursor.execute(sql_rows, params + [per_page, offset])
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
        cursor.execute("""
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
        cursor.execute("""
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
    from django.db import connections
    import json
    body            = json.loads(request.body)
    contractor_id   = body.get("contractor_id")
    contractor_name = (body.get("contractor_name") or "").strip()
    if not contractor_name:
        return JsonResponse({"error": "Contractor name is required"}, status=400)
    now = datetime.now()
    with connections["default"].cursor() as cursor:
        if contractor_id:
            cursor.execute("""
                UPDATE eos_Mst_Contractor
                SET Contractor_Name=%s, Mod_User_Id=%s, Mod_Dt=%s
                WHERE Contractor_Id=%s
            """, [contractor_name, 1, now, contractor_id])
        else:
            cursor.execute("SELECT COALESCE(MAX(Contractor_Id),0)+1 FROM eos_Mst_Contractor")
            new_id = cursor.fetchone()[0]
            cursor.execute("""
                INSERT INTO eos_Mst_Contractor
                    (Contractor_Id, Contractor_Name, Cr_User_Id, Cr_Dt)
                VALUES (%s, %s, %s, %s)
            """, [new_id, contractor_name, 1, now])
            contractor_id = new_id
    return JsonResponse({"success": True, "contractor_id": contractor_id})


@require_GET
def contractor_check_delete_api(request, contractor_id):
    return JsonResponse({"can_delete": True, "references": []})


@csrf_exempt
def contractor_delete_api(request, contractor_id):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    from django.db import connections
    with connections["default"].cursor() as cursor:
        cursor.execute("DELETE FROM eos_Mst_Contractor WHERE Contractor_Id=%s", [contractor_id])
    return JsonResponse({"success": True})


# ── Cert Institute Master ─────────────────────────────────────────────────────

@require_permission("masters.cert_institutes", "view")
def cert_institute_page(request):
    return render(request, "chatbot/masters/cert_institute.html")

@require_GET
def cert_institute_list_api(request):
    from django.db import connections
    with connections["default"].cursor() as cursor:
        cursor.execute("""
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
        cursor.execute("""
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
    cr_user_id = 1
    with connections["default"].cursor() as cursor:
        if inst_id:
            cursor.execute("""
                UPDATE eos_Mst_Cert_Institute
                SET Cert_Institute_Name=%s, Cert_Institute_Shortname=%s,
                    Cert_Institute_Address=%s, Location_Id=%s, Tel_No=%s,
                    Mod_User_Id=%s, Mod_Dt=%s
                WHERE Cert_Institute_Id=%s
            """, [name, short, address, loc_id, tel, cr_user_id, now, inst_id])
            return JsonResponse({"success": True, "Cert_Institute_Id": inst_id, "action": "updated"})
        else:
            cursor.execute("SELECT COALESCE(MAX(Cert_Institute_Id), 0) + 1 FROM eos_Mst_Cert_Institute")
            new_id = cursor.fetchone()[0]
            cursor.execute("""
                INSERT INTO eos_Mst_Cert_Institute
                    (Cert_Institute_Id, Cert_Institute_Name, Cert_Institute_Shortname,
                     Cert_Institute_Address, Location_Id, Tel_No, Cr_User_Id, Cr_Dt)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, [new_id, name, short, address, loc_id, tel, cr_user_id, now])
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
                cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE {col}=%s", [inst_id])
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
    from django.db import connections
    with connections["default"].cursor() as cursor:
        cursor.execute("DELETE FROM eos_Mst_Cert_Institute WHERE Cert_Institute_Id=%s", [inst_id])
    return JsonResponse({"success": True})


# ── Email Notification Type Master ───────────────────────────────────────────

@require_permission("masters.email_notification_types", "view")
def email_notification_type_page(request):
    return render(request, "chatbot/masters/email_notification_type.html")

@require_GET
def email_notification_type_list_api(request):
    from django.db import connections
    with connections["default"].cursor() as cursor:
        cursor.execute("""
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
        cursor.execute("""
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
    cr_user_id = 1
    with connections["default"].cursor() as cursor:
        if type_id:
            cursor.execute("""
                UPDATE eos_Email_Notification_Type
                SET EN_Type_Name=%s, EN_Type_Subject=%s, EN_Description=%s,
                    EN_Type_Active=%s, Mod_User_Id=%s, Mod_Dt=%s
                WHERE EN_Type_Id=%s
            """, [name, subject, desc, active, cr_user_id, now, type_id])
            return JsonResponse({"success": True, "EN_Type_Id": type_id, "action": "updated"})
        else:
            cursor.execute("SELECT COALESCE(MAX(EN_Type_Id), 0) + 1 FROM eos_Email_Notification_Type")
            new_id = cursor.fetchone()[0]
            cursor.execute("""
                INSERT INTO eos_Email_Notification_Type
                    (EN_Type_Id, EN_Type_Name, EN_Type_Subject, EN_Description,
                     EN_Type_Active, Cr_User_Id, Cr_Dt)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, [new_id, name, subject, desc, "Y", cr_user_id, now])
            return JsonResponse({"success": True, "EN_Type_Id": new_id, "action": "inserted"})

@csrf_exempt
def email_notification_type_deactivate_api(request, type_id):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    from django.db import connections
    with connections["default"].cursor() as cursor:
        cursor.execute("""
            UPDATE eos_Email_Notification_Type
            SET EN_Type_Active='N', Mod_User_Id=%s, Mod_Dt=%s
            WHERE EN_Type_Id=%s
        """, [1, datetime.now(), type_id])
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

    q     = request.GET.get("q", "").strip()
    page  = max(int(request.GET.get("page", 1)), 1)
    limit = 50
    offset = (page - 1) * limit

    if q:
        like = f"%{q}%"
        where = "WHERE USER_NAME LIKE %s OR USER_LOGIN_ID LIKE %s"
        sql_counts = (f"SELECT COUNT(*), "
                      f"SUM(CASE WHEN USER_ACTIVE='Y' THEN 1 ELSE 0 END), "
                      f"SUM(CASE WHEN USER_ACTIVE!='Y' OR USER_ACTIVE IS NULL THEN 1 ELSE 0 END) "
                      f"FROM Mst_user {where}")
        sql_rows   = (f"SELECT USER_ID, USER_LOGIN_ID, USER_NAME, USER_EMAIL, USER_ACTIVE "
                      f"FROM Mst_user {where} ORDER BY USER_NAME LIMIT %s OFFSET %s")
        params_counts = [like, like]
        params_rows   = [like, like, limit, offset]
    else:
        sql_counts = ("SELECT COUNT(*), "
                      "SUM(CASE WHEN USER_ACTIVE='Y' THEN 1 ELSE 0 END), "
                      "SUM(CASE WHEN USER_ACTIVE!='Y' OR USER_ACTIVE IS NULL THEN 1 ELSE 0 END) "
                      "FROM Mst_user")
        sql_rows   = ("SELECT USER_ID, USER_LOGIN_ID, USER_NAME, USER_EMAIL, USER_ACTIVE "
                      "FROM Mst_user ORDER BY USER_NAME LIMIT %s OFFSET %s")
        params_counts = []
        params_rows   = [limit, offset]

    with _conn["default"].cursor() as cursor:
        cursor.execute(sql_counts, params_counts)
        counts_row = cursor.fetchone()
        total        = counts_row[0]
        active_count = int(counts_row[1] or 0)
        inactive_count = int(counts_row[2] or 0)
        cursor.execute(sql_rows, params_rows)
        rows = cursor.fetchall()

    from .models import UserProfile
    admin_ids = set(
        UserProfile.objects.filter(is_app_admin=True).values_list("user_login_id", flat=True)
    )

    users = [
        {
            "user_id":      r[0],
            "login_id":     r[1],
            "name":         r[2] or r[1],
            "email":        r[3] or "",
            "active":       r[4] == "Y",
            "is_app_admin": r[1] in admin_ids,
        }
        for r in rows
    ]
    return JsonResponse({
        "users": users, "page": page, "total": total,
        "active_count": active_count, "inactive_count": inactive_count,
        "has_more": offset + limit < total,
    })


@_require_app_admin
@require_GET
def admin_user_perms_api(request, login_id):
    """Return current permissions for one user."""
    from .models import UserPermission, UserProfile
    from .permissions import get_menu_registry

    try:
        profile = UserProfile.objects.get(user_login_id=login_id)
        is_admin = profile.is_app_admin
    except UserProfile.DoesNotExist:
        is_admin = False

    perm_rows = {
        p.menu_key: p
        for p in UserPermission.objects.filter(user_login_id=login_id)
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
def admin_user_perms_save_api(request, login_id):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    from .models import UserPermission, UserProfile
    from .permissions import get_menu_registry

    is_admin = bool(data.get("is_app_admin", False))
    profile, _ = UserProfile.objects.get_or_create(user_login_id=login_id)
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
            user_login_id=login_id,
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

    return JsonResponse({"success": True})


@_require_app_admin
@csrf_exempt
def admin_user_admin_toggle_api(request, login_id):
    """Toggle is_app_admin for a user."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    from .models import UserProfile
    profile, _ = UserProfile.objects.get_or_create(user_login_id=login_id)
    profile.is_app_admin = not profile.is_app_admin
    profile.save()
    return JsonResponse({"is_app_admin": profile.is_app_admin})

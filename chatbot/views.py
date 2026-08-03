import json
import threading
import uuid as _uuid_mod
from datetime import datetime
from pathlib import Path

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET, require_http_methods
from langchain_core.messages import HumanMessage, AIMessage

from .models import Conversation, Message
from .rag.chain import get_rag_chain
from .health import run_all as run_health_checks
from .analytics.router import route as analytics_route

_chain = None

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

def chat_page(request):
    return render(request, "chatbot/chat.html")


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

def rigs_page(request):
    return render(request, "chatbot/rigs/index.html")


def rig_detail_page(request, rig_id):
    return render(request, "chatbot/rigs/detail.html", {"rig_id": rig_id})


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
    return render(request, "chatbot/listings/index.html")


def listings_incidents_page(request):
    return render(request, "chatbot/listings/incidents.html")


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


@require_GET
def listings_certificates_page(request):
    return render(request, "chatbot/listings/certificates.html")


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

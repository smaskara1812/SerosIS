"""
Audit trail — records who did what, when, and (for edits) the field-level
before/after diff. Writes to cb_audit_log in the chathistory DB.

Design notes:
  * Best-effort: every public function swallows its own exceptions and logs
    them. Auditing must NEVER break the user's primary action.
  * Masters use raw SQL (not the ORM), so we snapshot the row via the same
    cursor before/after the write and diff the two. Audit/system columns
    (Cr_/Mod_ user + date) are excluded from diffs.
  * Entity → (table, pk_col, label_col) metadata lets snap()/diff work for any
    single-table master without per-API column lists. Human labels come from
    masters_registry so they stay in sync with the cards/sidebar.
"""
import datetime
import decimal
import logging

logger = logging.getLogger(__name__)

# Columns that are bookkeeping, not user data — never shown in a diff.
_SYSTEM_COLS = {"Cr_User_Id", "Cr_Dt", "Mod_User_Id", "Mod_Dt"}

# entity key → (table, pk_col, label_col). Single-table masters only; complex
# ones (job descriptions hdr/dtl, etc.) log via record_action() with an explicit label.
ENTITY_TABLES = {
    "masters.rigs":                     ("eos_Mst_Rig",                 "Rig_Id",              "Rig_Name"),
    "masters.operators":                ("eos_Mst_Operator",            "Operator_Id",         "Operator_Name"),
    "masters.contractors":              ("eos_Mst_Contractor",          "Contractor_Id",       "Contractor_Name"),
    "masters.cost_centres":             ("eos_Mst_Cost_Centre",         "Cost_Centre_Id",      "Cost_Centre_Name"),
    "masters.cost_centre_types":        ("eos_Mst_Cost_Centre_Type",    "Cost_Centre_Type_Id", "Cost_Centre_Type_Name"),
    "masters.email_notification_types": ("eos_Email_Notification_Type", "EN_Type_Id",          "EN_Type_Name"),
    "masters.cert_institutes":          ("eos_Mst_Cert_Institute",      "Cert_Institute_Id",   "Cert_Institute_Name"),
    "masters.competency":               ("eos_Mst_Competency",          "Competency_Id",       "Competency_Name"),
    "masters.rig_operations":           ("eos_Mst_Rig_Operation",       "Rig_Operation_Id",    "Rig_Operation_Name"),
    "masters.contact_exposure_types":   ("eos_Mst_Contact_Exposure_Type","Contact_Expo_Type_Id","Contact_Expo_Type_Name"),
    "masters.indicator_types":          ("eos_Mst_Indicator_Type",      "Indicator_Type_Id",   "Indicator_Type_Name"),
    "masters.indicator_subtypes":       ("eos_Mst_Indicator_Subtype",   "Indicator_Subtype_Id","Indicator_Subtype_Name"),
    "masters.parts_of_body":            ("eos_Mst_Parts_Of_Body",       "Part_Of_Body_Id",     "Part_Of_Body_Name"),
    "masters.qhse_categories":          ("eos_Mst_QHSE_Category",        "QHSE_Category_Id",    "QHSE_Category_Name"),
    "masters.hse_activities":           ("eos_Mst_HSE_Activity",         "HSE_Activity_Id",     "HSE_Activity_Name"),
    "masters.hse_consumables":          ("eos_Mst_HSE_Consumable",       "HSE_Consumable_Id",   "HSE_Consumable_Name"),
    "masters.hazard_types":             ("eos_Mst_Hazard_Type",          "Haz_Type_Id",         "Haz_Type_Name"),
    # These two have no single human-name column (they're FK combos) — label_col=None.
    "masters.travel_eligibility":       ("eos_Travel_Eligibility",       "Travel_Eligibility_Id", None),
    "masters.reporting_structure":      ("eos_Reporting_Structure",      "Reporting_Structure_Id", None),
    "masters.user_rig_mapping":         ("eos_Mst_User_Rig_Mapping",     "User_Rig_Mapping_Id", None),
    "masters.user_category_mapping":    ("eos_Mst_User_Fs_Catg_Mapping", "User_Fs_Catg_Mapping_Id", None),
    "masters.rig_to_email_mapping":     ("eos_Rig_To_Email_Mapping",     "Rig_To_Email_Mapping_Id", None),
    "masters.doc_to_sign_mapping":       ("eos_Doc_To_Sign_Mapping",     "Doc_To_Sign_Id", None),
    "masters.interviewer_mapping":       ("eos_Mst_Interviewer",         "Interviewer_Id", None),
    "masters.project_contract":          ("eos_Mst_Project_Contract",    "Prj_Contract_Id", None),
    "masters.project_drilling_rates":    ("eos_Prj_Drilling_Rate",       "Prj_Drilling_Rate_Id", None),
    "masters.drilling_operations":       ("eos_Mst_Drilling_Operations", "Drilling_Ops_Id", "Drilling_Ops_Name"),
    "masters.drilling_sections":         ("eos_Mst_Drilling_Section",    "Drilling_Section_Id", "Drilling_Section_Name"),
    # Job Descriptions: snap the section header; detail lines are logged via record_action.
    "masters.job_descriptions":         ("eos_Job_Description_Hdr",      "JD_Hdr_Id",           "JD_Hdr_Description"),
}

# Labels for non-master entities (masters come from masters_registry).
_EXTRA_LABELS = {
    "auth":              "Authentication",
    "admin.user_rights": "User Rights",
}


# ── identity ──────────────────────────────────────────────────────────────────
def current_user(request):
    """Return (user_id | None, username). user_id is the Mst_user USER_ID;
    None for a superuser with no cb_user_profile row."""
    try:
        if not getattr(request, "user", None) or not request.user.is_authenticated:
            return (None, "anonymous")
        username = request.user.username
        from .models import UserProfile
        try:
            uid = UserProfile.objects.get(user_login_id=username).user_id
        except UserProfile.DoesNotExist:
            uid = None
        return (uid, username)
    except Exception:
        logger.exception("audit.current_user failed")
        return (None, "unknown")


def ops_user_id(request):
    """Real Mst_user USER_ID for Cr_User_Id / Mod_User_Id on ops writes.
    Falls back to 1 (system) when the user has no profile (e.g. Django superuser)."""
    uid, _ = current_user(request)
    return uid if uid is not None else 1


# ── helpers ───────────────────────────────────────────────────────────────────
def entity_label(entity):
    # 1) masters registry (kept in sync with the cards/sidebar)
    try:
        from .masters_registry import all_items
        for it in all_items():
            if it["key"] == entity:
                return it["label"]
    except Exception:
        pass
    # 2) explicit non-master labels
    if entity in _EXTRA_LABELS:
        return _EXTRA_LABELS[entity]
    # 3) any other cb_menu key (listings, etc.)
    try:
        from .permissions import get_menu_registry
        m = get_menu_registry().get(entity)
        if m and m.get("label"):
            return m["label"]
    except Exception:
        pass
    return entity


def _norm(v):
    """Normalise a value for JSON storage and equality comparison."""
    if isinstance(v, (datetime.datetime, datetime.date)):
        return v.isoformat()
    if isinstance(v, decimal.Decimal):
        return str(v)
    if isinstance(v, bytes):
        try:
            return v.decode("utf-8", "replace")
        except Exception:
            return str(v)
    return v


def _client(request):
    if request is None:
        return ("", "")
    fwd = request.META.get("HTTP_X_FORWARDED_FOR", "")
    ip = (fwd.split(",")[0].strip() if fwd else request.META.get("REMOTE_ADDR", "")) or ""
    ua = (request.META.get("HTTP_USER_AGENT", "") or "")[:300]
    return (ip[:45], ua)


def snap(cursor, entity, pk_val):
    """Snapshot the current row (user columns only) as {col: value}, or None if
    new / not found. Uses the caller's (ops-DB) cursor."""
    if pk_val is None:
        return None
    meta = ENTITY_TABLES.get(entity)
    if not meta:
        return None
    table, pk_col, _label = meta
    try:
        # dbq() routes through the dialect translator (eos_X → eos.X, Mst_X →
        # dbo.Mst_X, etc. on SQL Server; a pass-through on MySQL), same choke
        # point every other raw query in the app uses. Audit WRITES use the
        # Django ORM, which is already backend-correct.
        from .db.sql import dbq
        dbq(cursor, f"SELECT * FROM {table} WHERE {pk_col}=%s", (pk_val,))
        row = cursor.fetchone()
        if not row:
            return None
        cols = [c[0] for c in cursor.description]
        return {c: _norm(v) for c, v in zip(cols, row) if c not in _SYSTEM_COLS}
    except Exception:
        logger.exception("audit.snap failed for %s", entity)
        return None


def _label_of(entity, row):
    meta = ENTITY_TABLES.get(entity)
    if meta and meta[2] and row:
        return row.get(meta[2])
    return None


def _diff(before, after):
    out = {}
    for k in set(before) | set(after):
        a, b = before.get(k), after.get(k)
        if a != b:
            out[k] = {"old": a, "new": b}
    return out


# ── public logging API ────────────────────────────────────────────────────────
def record_save(request, cursor, entity, pk_val, before):
    """After an insert/update: re-snapshot and log a create (all new values) or
    an update (field-level diff). `before` is the snap() taken before the write
    (None for a new record)."""
    try:
        after = snap(cursor, entity, pk_val) or {}
        if before is None:
            changes = {k: {"old": None, "new": v} for k, v in after.items()}
            _write(request, "create", entity, pk_val, _label_of(entity, after), changes or None)
        else:
            changes = _diff(before, after)
            _write(request, "update", entity, pk_val,
                   _label_of(entity, after) or _label_of(entity, before), changes or None)
    except Exception:
        logger.exception("audit.record_save failed for %s", entity)


def record_delete(request, entity, pk_val, before):
    """Log a hard delete. `before` is the snap() taken before the DELETE."""
    try:
        changes = {k: {"old": v, "new": None} for k, v in (before or {}).items()} or None
        _write(request, "delete", entity, pk_val, _label_of(entity, before), changes)
    except Exception:
        logger.exception("audit.record_delete failed for %s", entity)


def record_deactivate(request, entity, pk_val, before):
    """Log a soft-delete (Active flag flipped to 'N'). `before` is the snap()
    taken before the UPDATE."""
    try:
        changes = None
        if before:
            for k in before:
                if k.endswith("_Active"):
                    changes = {k: {"old": before[k], "new": "N"}}
                    break
        _write(request, "deactivate", entity, pk_val, _label_of(entity, before), changes)
    except Exception:
        logger.exception("audit.record_deactivate failed for %s", entity)


def record_action(request, action, entity, record_id=None, record_label=None, changes=None):
    """Generic logger (deactivate, export, permission_change, and complex masters)."""
    try:
        _write(request, action, entity, record_id, record_label, changes)
    except Exception:
        logger.exception("audit.record_action failed for %s/%s", entity, action)


def log_auth(action, username, request=None, extra=None):
    """Auth events from signal receivers (login / logout / login_failed)."""
    try:
        uid = None
        if username:
            try:
                from .models import UserProfile
                uid = UserProfile.objects.get(user_login_id=username).user_id
            except Exception:
                uid = None
        _create(uid, username or "", action, "auth", "Authentication", None, None, extra, request)
    except Exception:
        logger.exception("audit.log_auth failed")


# ── writers ───────────────────────────────────────────────────────────────────
def _write(request, action, entity, record_id, record_label, changes):
    uid, username = current_user(request)
    _create(uid, username, action, entity, entity_label(entity),
            record_id, record_label, changes, request)


def _create(uid, username, action, entity, ent_label, record_id, record_label, changes, request):
    from .models import CbAuditLog
    ip, ua = _client(request)
    CbAuditLog.objects.create(
        user_id=uid,
        username=(username or "")[:50],
        action=action,
        entity=entity,
        entity_label=(ent_label or "")[:80],
        record_id=("" if record_id is None else str(record_id))[:40],
        record_label=(record_label or "")[:200],
        changes=changes,
        ip=ip,
        user_agent=ua,
    )

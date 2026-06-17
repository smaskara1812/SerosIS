"""
Analytics tool functions for the Seros operational database.

Each function runs a pre-built, parameterised SQL query against Seros_Data
and returns a plain dict/list. No LLM touches SQL — ever.
"""

from django.db import connections

from chatbot.db.sql import maybe_translate

# ── Helpers ────────────────────────────────────────────────────────────────────

def _query(sql: str, params: tuple = ()) -> list[dict]:
    """Execute a read-only query on the operational DB and return rows as dicts."""
    # On MSSQL, translate MySQL-style SQL (CURDATE, DATEDIFF arg order,
    # INTERVAL, LIMIT, eos_* table names, etc.) — see chatbot/db/sql.py.
    sql, params = maybe_translate(sql, tuple(params))
    with connections["default"].cursor() as cur:
        cur.execute(sql, params)
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def _rig_id(rig_name: str) -> int | None:
    """Resolve a rig name or short name (case-insensitive) to its Rig_Id."""
    rows = _query("SELECT Rig_Id, Rig_Name, Rig_Short_Name FROM eos_Mst_Rig WHERE Rig_Type_Id IN (1,2)")
    term = rig_name.strip().lower()
    for r in rows:
        if (
            r["Rig_Name"].lower() == term
            or r["Rig_Short_Name"].lower() == term
            or term in r["Rig_Name"].lower()
        ):
            return r["Rig_Id"]
    return None


def _dept_id(dept_name: str) -> int | None:
    """Resolve a department name (case-insensitive) to its Dept_Id."""
    rows = _query("SELECT Dept_Id, Dept_Name FROM Mst_Department")
    term = dept_name.strip().lower()
    for r in rows:
        if r["Dept_Name"].lower() == term or term in r["Dept_Name"].lower():
            return r["Dept_Id"]
    return None


# ── Tool 1a: Count rigs ────────────────────────────────────────────────────────

def count_rigs() -> dict:
    """Return active/inactive rig counts only — no full listing."""
    rows = _query("SELECT Rig_Active FROM eos_Mst_Rig WHERE Rig_Type_Id IN (1,2)")
    active   = sum(1 for r in rows if r["Rig_Active"] == "Y")
    inactive = len(rows) - active
    return {
        "tool": "count_rigs",
        "total": len(rows),
        "active": active,
        "inactive": inactive,
    }


# ── Tool 1b: List rigs ─────────────────────────────────────────────────────────

def list_rigs(status: str = "all") -> dict:
    """
    List rigs.
    status: 'all' | 'active' | 'inactive'
    """
    rows = _query(
        "SELECT Rig_Id, Rig_Name, Rig_Short_Name, Rig_Active FROM eos_Mst_Rig "
        "WHERE Rig_Type_Id IN (1,2) ORDER BY Rig_Active DESC, Rig_Name"
    )
    if status == "active":
        rows = [r for r in rows if r["Rig_Active"] == "Y"]
    elif status == "inactive":
        rows = [r for r in rows if r["Rig_Active"] != "Y"]

    active   = [r for r in rows if r["Rig_Active"] == "Y"]
    inactive = [r for r in rows if r["Rig_Active"] != "Y"]
    return {
        "tool": "list_rigs",
        "filter_status": status,
        "total_shown": len(rows),
        "active_count": len(active),
        "inactive_count": len(inactive),
        "rigs": [
            {"id": r["Rig_Id"], "name": r["Rig_Name"], "short": r["Rig_Short_Name"],
             "active": r["Rig_Active"] == "Y"}
            for r in rows
        ],
    }


# ── Tool 2: Headcount ──────────────────────────────────────────────────────────

def get_headcount(rig: str | None = None, dept: str | None = None) -> dict:
    """
    Employee/crew headcount.
    - rig: crew physically on board that rig right now (Serv_Subtype_Id = 7 'On Board').
    - dept: active employees in that department.
    - none: total active employees + crew on board, fleet-wide.

    "On board" specifically means Serv_Subtype_Id = 7 — matches the Workforce
    dashboard's "Crew Currently On Board" definition. Earlier this counted any
    open service record (On Board + Off Board + On Leave + Standby, etc.),
    which inflated the figure and didn't match what "crew posted today" should
    mean.
    """
    if rig:
        rig_id = _rig_id(rig)
        if rig_id is None:
            return {"tool": "get_headcount", "error": f"Rig '{rig}' not found."}
        rows = _query("""
            SELECT r.Rig_Name, COUNT(DISTINCT sd.Fs_Emp_Id) AS crew_count
            FROM eos_Service_Details sd
            JOIN eos_Mst_Rig r ON sd.Rig_Id = r.Rig_Id AND r.Rig_Type_Id IN (1,2)
            WHERE sd.Rig_Id = %s AND sd.Serv_Subtype_To IS NULL AND sd.Serv_Subtype_Id = 7
        """, (rig_id,))
        return {
            "tool": "get_headcount",
            "filter": "rig",
            "rig_name": rows[0]["Rig_Name"] if rows else rig,
            "active_crew": rows[0]["crew_count"] if rows else 0,
        }

    if dept:
        dept_id = _dept_id(dept)
        if dept_id is None:
            return {"tool": "get_headcount", "error": f"Department '{dept}' not found."}
        rows = _query("""
            SELECT d.Dept_Name, COUNT(*) AS emp_count
            FROM Mst_Employee e
            JOIN Mst_Department d ON e.DEPT_ID = d.Dept_Id
            WHERE e.DEPT_ID = %s AND e.EMP_ACTIVE = 'Y'
        """, (dept_id,))
        return {
            "tool": "get_headcount",
            "filter": "department",
            "dept_name": rows[0]["Dept_Name"] if rows else dept,
            "active_employees": rows[0]["emp_count"] if rows else 0,
        }

    emp_rows  = _query("SELECT COUNT(*) AS cnt FROM Mst_Employee WHERE EMP_ACTIVE = 'Y'")
    crew_rows = _query("""
        SELECT COUNT(DISTINCT sd.Fs_Emp_Id) AS cnt
        FROM eos_Service_Details sd
        JOIN eos_Mst_Rig r ON sd.Rig_Id = r.Rig_Id AND r.Rig_Type_Id IN (1,2)
        WHERE sd.Serv_Subtype_To IS NULL AND sd.Serv_Subtype_Id = 7
    """)
    by_rig    = _query("""
        SELECT r.Rig_Name, COUNT(DISTINCT sd.Fs_Emp_Id) AS crew
        FROM eos_Service_Details sd
        JOIN eos_Mst_Rig r ON sd.Rig_Id = r.Rig_Id AND r.Rig_Type_Id IN (1,2)
        WHERE sd.Serv_Subtype_To IS NULL AND sd.Serv_Subtype_Id = 7
        GROUP BY r.Rig_Name ORDER BY crew DESC
    """)
    return {
        "tool": "get_headcount",
        "filter": "none",
        "total_active_employees": emp_rows[0]["cnt"],
        "active_rig_crew": crew_rows[0]["cnt"],
        "crew_by_rig": by_rig,
    }


# ── Tool 3a: Incident summary ──────────────────────────────────────────────────

def get_incident_summary(rig: str | None = None, year: int | None = None) -> dict:
    """Aggregate incident counts and severity, optionally by rig and/or year."""
    conditions = ["COALESCE(i.Marked_As_Deleted, '') != 'Y'"]
    params: list = []

    if rig:
        rig_id = _rig_id(rig)
        if rig_id is None:
            return {"tool": "get_incident_summary", "error": f"Rig '{rig}' not found."}
        conditions.append("i.Rig_Id = %s")
        params.append(rig_id)
    if year:
        conditions.append("YEAR(i.Incident_Date) = %s")
        params.append(year)

    where = " AND ".join(conditions)

    summary = _query(f"""
        SELECT COUNT(*) AS total_incidents,
               SUM(CASE WHEN i.Incident_Severity = 'H' THEN 1 ELSE 0 END) AS high_severity,
               SUM(CASE WHEN i.Incident_Severity = 'M' THEN 1 ELSE 0 END) AS medium_severity,
               SUM(CASE WHEN i.Incident_Severity = 'L' THEN 1 ELSE 0 END) AS low_severity,
               SUM(COALESCE(i.NPT_Hrs_Loss, 0))                            AS total_npt_hours,
               SUM(CASE WHEN i.Person_Injured = 'Y' THEN 1 ELSE 0 END)    AS with_injury
        FROM eos_Incident_Details i WHERE {where}
    """, tuple(params))

    by_rig = _query(f"""
        SELECT r.Rig_Name, COUNT(*) AS incidents
        FROM eos_Incident_Details i
        JOIN eos_Mst_Rig r ON i.Rig_Id = r.Rig_Id AND r.Rig_Type_Id IN (1,2)
        WHERE {where} GROUP BY r.Rig_Name ORDER BY incidents DESC
    """, tuple(params))

    by_year = _query(f"""
        SELECT YEAR(i.Incident_Date) AS year, COUNT(*) AS incidents
        FROM eos_Incident_Details i
        WHERE {where} GROUP BY year ORDER BY year DESC LIMIT 6
    """, tuple(params))

    return {
        "tool": "get_incident_summary",
        "filters": {"rig": rig, "year": year},
        "summary": summary[0] if summary else {},
        "by_rig": by_rig,
        "by_year": by_year,
    }


# ── Tool 3b: List recent incidents ────────────────────────────────────────────

def list_incidents(
    rig: str | None = None,
    year: int | None = None,
    limit: int = 5,
) -> dict:
    """
    Return the most recent incident records (not just counts).
    limit: number of rows to return (default 5, max 50).
    """
    limit = min(max(1, limit), 50)

    conditions = ["COALESCE(i.Marked_As_Deleted, '') != 'Y'"]
    params: list = []

    if rig:
        rig_id = _rig_id(rig)
        if rig_id is None:
            return {"tool": "list_incidents", "error": f"Rig '{rig}' not found."}
        conditions.append("i.Rig_Id = %s")
        params.append(rig_id)
    if year:
        conditions.append("YEAR(i.Incident_Date) = %s")
        params.append(year)

    where = " AND ".join(conditions)
    params.append(limit)

    rows = _query(f"""
        SELECT
            i.Incident_No,
            DATE(i.Incident_Date)        AS date,
            r.Rig_Name,
            i.Incident_Severity          AS severity,
            i.Person_Injured             AS person_injured,
            COALESCE(i.NPT_Hrs_Loss, 0)  AS npt_hours,
            LEFT(i.Incident_Descr, 200)  AS description
        FROM eos_Incident_Details i
        LEFT JOIN eos_Mst_Rig r ON i.Rig_Id = r.Rig_Id AND r.Rig_Type_Id IN (1,2)
        WHERE {where}
        ORDER BY i.Incident_Date DESC
        LIMIT %s
    """, tuple(params))

    severity_map = {"H": "High", "M": "Medium", "L": "Low"}
    for r in rows:
        r["severity"] = severity_map.get(r["severity"], r["severity"] or "Unknown")
        r["person_injured"] = r["person_injured"] == "Y"

    return {
        "tool": "list_incidents",
        "filters": {"rig": rig, "year": year, "limit": limit},
        "count_returned": len(rows),
        "incidents": rows,
    }


# ── Tool 4a: Hazard card summary ──────────────────────────────────────────────

def get_hazard_card_trend(rig: str | None = None, year: int | None = None) -> dict:
    """Hazard card aggregate counts and trend."""
    conditions = ["COALESCE(h.Marked_As_Deleted, '') != 'Y'"]
    params: list = []

    if rig:
        rig_id = _rig_id(rig)
        if rig_id is None:
            return {"tool": "get_hazard_card_trend", "error": f"Rig '{rig}' not found."}
        conditions.append("h.Rig_Id = %s")
        params.append(rig_id)
    if year:
        conditions.append("YEAR(h.Event_Dt) = %s")
        params.append(year)

    where = " AND ".join(conditions)

    summary = _query(f"""
        SELECT COUNT(*) AS total_cards,
               SUM(CASE WHEN h.Haz_ID_Card_Status = 'C' THEN 1 ELSE 0 END) AS closed,
               SUM(CASE WHEN h.Haz_ID_Card_Status != 'C' THEN 1 ELSE 0 END) AS open,
               SUM(CASE WHEN h.Timeout_For_Safety = 'Y' THEN 1 ELSE 0 END)  AS timeout_for_safety
        FROM eos_Hazard_ID_Card h WHERE {where}
    """, tuple(params))

    by_rig = _query(f"""
        SELECT r.Rig_Name, COUNT(*) AS cards,
               SUM(CASE WHEN h.Haz_ID_Card_Status = 'C' THEN 1 ELSE 0 END) AS closed
        FROM eos_Hazard_ID_Card h
        JOIN eos_Mst_Rig r ON h.Rig_Id = r.Rig_Id AND r.Rig_Type_Id IN (1,2)
        WHERE {where} GROUP BY r.Rig_Name ORDER BY cards DESC LIMIT 10
    """, tuple(params))

    by_year = _query(f"""
        SELECT YEAR(h.Event_Dt) AS year, COUNT(*) AS cards
        FROM eos_Hazard_ID_Card h
        WHERE {where} AND h.Event_Dt > '2010-01-01'
        GROUP BY year ORDER BY year DESC LIMIT 6
    """, tuple(params))

    return {
        "tool": "get_hazard_card_trend",
        "filters": {"rig": rig, "year": year},
        "summary": summary[0] if summary else {},
        "by_rig": by_rig,
        "by_year": by_year,
    }


# ── Tool 4b: List recent hazard cards ─────────────────────────────────────────

def list_hazard_cards(
    rig: str | None = None,
    year: int | None = None,
    status: str | None = None,
    limit: int = 10,
) -> dict:
    """
    Return individual hazard card records.
    status: 'open' | 'closed' | None (all)
    limit: number of rows (default 10, max 50)
    """
    limit = min(max(1, limit), 50)

    conditions = ["COALESCE(h.Marked_As_Deleted, '') != 'Y'"]
    params: list = []

    if rig:
        rig_id = _rig_id(rig)
        if rig_id is None:
            return {"tool": "list_hazard_cards", "error": f"Rig '{rig}' not found."}
        conditions.append("h.Rig_Id = %s")
        params.append(rig_id)
    if year:
        conditions.append("YEAR(h.Event_Dt) = %s")
        params.append(year)
    if status == "open":
        conditions.append("h.Haz_ID_Card_Status != 'C'")
    elif status == "closed":
        conditions.append("h.Haz_ID_Card_Status = 'C'")

    where = " AND ".join(conditions)
    params.append(limit)

    rows = _query(f"""
        SELECT
            h.Haz_ID_Card_No                                  AS card_no,
            DATE(h.Event_Dt)                                  AS event_date,
            r.Rig_Name,
            CASE WHEN h.Haz_ID_Card_Status = 'C'
                 THEN 'Closed' ELSE 'Open' END                AS status,
            CASE WHEN h.Timeout_For_Safety = 'Y'
                 THEN 'Yes' ELSE 'No' END                     AS timeout_for_safety,
            LEFT(h.Hazard_Desc, 150)                          AS hazard_description,
            LEFT(h.Action_Taken, 150)                         AS action_taken
        FROM eos_Hazard_ID_Card h
        LEFT JOIN eos_Mst_Rig r ON h.Rig_Id = r.Rig_Id AND r.Rig_Type_Id IN (1,2)
        WHERE {where}
        ORDER BY h.Event_Dt DESC
        LIMIT %s
    """, tuple(params))

    return {
        "tool": "list_hazard_cards",
        "filters": {"rig": rig, "year": year, "status": status, "limit": limit},
        "count_returned": len(rows),
        "cards": rows,
    }


# ── Tool 4d: Overdue / oldest open hazard cards ───────────────────────────────

def list_overdue_hazard_cards(rig: str | None = None, limit: int = 10) -> dict:
    """
    List open hazard cards sorted by age (oldest first).
    Covers both 'which cards are overdue' and 'which is the oldest open card'.
    Always current snapshot — no year filter.
    """
    limit = min(max(1, limit), 50)
    conditions = [
        "COALESCE(h.Marked_As_Deleted, '') != 'Y'",
        "h.Haz_ID_Card_Status != 'C'",
    ]
    params: list = []

    if rig:
        rig_id = _rig_id(rig)
        if rig_id is None:
            return {"tool": "list_overdue_hazard_cards", "error": f"Rig '{rig}' not found."}
        conditions.append("h.Rig_Id = %s")
        params.append(rig_id)

    where = " AND ".join(conditions)
    params.append(limit)

    rows = _query(f"""
        SELECT
            h.Haz_ID_Card_No                                  AS card_no,
            DATE(h.Event_Dt)                                  AS event_date,
            DATEDIFF(CURDATE(), h.Event_Dt)                   AS age_days,
            r.Rig_Name,
            w.Work_Location                                   AS work_location,
            t.Haz_Type_Name                                   AS hazard_type,
            CASE WHEN h.Timeout_For_Safety = 'Y'
                 THEN 'Yes' ELSE 'No' END                     AS tfs,
            LEFT(h.Hazard_Desc, 200)                          AS hazard_description,
            LEFT(h.Action_Taken, 150)                         AS action_taken
        FROM eos_Hazard_ID_Card h
        LEFT JOIN eos_Mst_Rig r            ON h.Rig_Id          = r.Rig_Id AND r.Rig_Type_Id IN (1,2)
        LEFT JOIN Mstx_Work_Location w     ON h.Work_Location_Id = w.Work_Location_Id
        LEFT JOIN eos_Mst_Hazard_Type t    ON h.Haz_Type_Id      = t.Haz_Type_Id
        WHERE {where}
        ORDER BY h.Event_Dt ASC
        LIMIT %s
    """, tuple(params))

    oldest = rows[0] if rows else None
    return {
        "tool": "list_overdue_hazard_cards",
        "filters": {"rig": rig, "limit": limit},
        "note": "Current snapshot — not year-filtered. Sorted oldest first.",
        "count_returned": len(rows),
        "oldest_card": oldest,
        "cards": rows,
    }


# ── Tool 4e: Corrective actions from incident investigations ──────────────────

def list_corrective_actions(
    rig: str | None = None,
    year: int | None = None,
    status: str | None = None,
    limit: int = 10,
) -> dict:
    """
    List corrective actions from incident investigations (eos_Incident_Actions).
    status: 'open' | 'closed' | 'overdue' | None (all)
    """
    limit = min(max(1, limit), 50)
    conditions = ["COALESCE(a.Marked_As_Deleted, '') != 'Y'"]
    params: list = []

    if rig:
        rig_id = _rig_id(rig)
        if rig_id is None:
            return {"tool": "list_corrective_actions", "error": f"Rig '{rig}' not found."}
        conditions.append("i.Rig_Id = %s")
        params.append(rig_id)
    if year:
        conditions.append("YEAR(i.Incident_Date) = %s")
        params.append(year)
    if status == "open":
        conditions.append("a.Action_Status = 'OP'")
    elif status == "closed":
        conditions.append("a.Action_Status = 'CL'")
    elif status == "overdue":
        conditions.append("a.Action_Status = 'OP' AND a.Target_Date IS NOT NULL AND a.Target_Date < CURDATE()")

    where = " AND ".join(conditions)
    params.append(limit)

    rows = _query(f"""
        SELECT
            a.Incident_Action_Id                              AS action_id,
            DATE(i.Incident_Date)                             AS incident_date,
            r.Rig_Name,
            CASE WHEN a.Action_Status = 'CL' THEN 'Closed'
                 WHEN a.Target_Date IS NOT NULL AND a.Target_Date < CURDATE()
                      THEN 'Overdue' ELSE 'Open' END          AS status,
            a.Target_Date,
            a.Completion_Dt                                   AS completed_date,
            LEFT(a.Action_Recommended, 250)                   AS action_recommended,
            LEFT(a.Action_Taken, 200)                         AS action_taken,
            a.Action_Party                                    AS responsible_party,
            CASE WHEN a.Target_Date IS NOT NULL AND a.Action_Status = 'OP'
                 THEN DATEDIFF(CURDATE(), a.Target_Date) ELSE NULL END AS days_overdue
        FROM eos_Incident_Actions a
        JOIN eos_Incident_Details i ON a.Incident_Id = i.Incident_Id
        LEFT JOIN eos_Mst_Rig r ON i.Rig_Id = r.Rig_Id AND r.Rig_Type_Id IN (1,2)
        WHERE {where}
        ORDER BY
            CASE WHEN a.Action_Status = 'OP' AND a.Target_Date < CURDATE() THEN 0
                 WHEN a.Action_Status = 'OP' THEN 1 ELSE 2 END,
            a.Target_Date ASC
        LIMIT %s
    """, tuple(params))

    return {
        "tool": "list_corrective_actions",
        "filters": {"rig": rig, "year": year, "status": status, "limit": limit},
        "count_returned": len(rows),
        "actions": rows,
    }


# ── Tool 5: Material cost ──────────────────────────────────────────────────────

def get_material_cost(rig: str | None = None, year: int | None = None) -> dict:
    """Material expenditure summary from eos_OPC_Material_Cost."""
    # Find the latest available year in the table
    latest_row = _query(
        "SELECT MAX(YEAR(Expense_Month)) AS latest_year FROM eos_OPC_Material_Cost"
    )
    latest_year = latest_row[0]["latest_year"] if latest_row else None

    # If requested year has no data, fall back to latest available year
    actual_year = year
    year_note = None
    if year and latest_year and year > latest_year:
        actual_year = latest_year
        year_note = f"No data found for {year}. Showing latest available year ({latest_year}) instead."

    conditions = ["COALESCE(m.Marked_As_Deleted, '') != 'Y'"]
    params: list = []

    if rig:
        rig_id = _rig_id(rig)
        if rig_id is None:
            return {"tool": "get_material_cost", "error": f"Rig '{rig}' not found."}
        conditions.append("cc.Rig_Id = %s")
        params.append(rig_id)
    if actual_year:
        conditions.append("YEAR(m.Expense_Month) = %s")
        params.append(actual_year)

    where = " AND ".join(conditions)

    summary = _query(f"""
        SELECT COUNT(*)                       AS total_items,
               ROUND(SUM(m.Total_Amt), 2)    AS total_cost,
               ROUND(AVG(m.Unit_Price), 2)   AS avg_unit_price,
               COUNT(DISTINCT m.Cost_Centre_Id) AS cost_centres
        FROM eos_OPC_Material_Cost m
        JOIN eos_Mst_Cost_Centre cc ON m.Cost_Centre_Id = cc.Cost_Centre_Id
        WHERE {where}
    """, tuple(params))

    by_rig = _query(f"""
        SELECT r.Rig_Name, COUNT(*) AS items, ROUND(SUM(m.Total_Amt), 2) AS total_cost
        FROM eos_OPC_Material_Cost m
        JOIN eos_Mst_Cost_Centre cc ON m.Cost_Centre_Id = cc.Cost_Centre_Id
        JOIN eos_Mst_Rig r ON cc.Rig_Id = r.Rig_Id AND r.Rig_Type_Id IN (1,2)
        WHERE {where} GROUP BY r.Rig_Name ORDER BY total_cost DESC LIMIT 10
    """, tuple(params))

    by_year = _query(f"""
        SELECT YEAR(m.Expense_Month) AS year, ROUND(SUM(m.Total_Amt), 2) AS total_cost
        FROM eos_OPC_Material_Cost m
        JOIN eos_Mst_Cost_Centre cc ON m.Cost_Centre_Id = cc.Cost_Centre_Id
        WHERE {where} GROUP BY year ORDER BY year DESC LIMIT 6
    """, tuple(params))

    return {
        "tool": "get_material_cost",
        "filters": {"rig": rig, "year": actual_year},
        "note": year_note,
        "latest_available_year": latest_year,
        "summary": summary[0] if summary else {},
        "by_rig": by_rig,
        "by_year": by_year,
    }


# ── Tool 6: Drilling hours ────────────────────────────────────────────────────

def get_drilling_hours(rig: str | None = None, year: int | None = None) -> dict:
    """Drilling operation hours from eos_Drilling_Dtl_Ops."""
    conditions = ["1=1"]
    params: list = []

    if rig:
        rig_id = _rig_id(rig)
        if rig_id is None:
            return {"tool": "get_drilling_hours", "error": f"Rig '{rig}' not found."}
        conditions.append("dh.Rig_Id = %s")
        params.append(rig_id)
    if year:
        conditions.append("YEAR(ops.Time_From) = %s")
        params.append(year)

    where = " AND ".join(conditions)

    summary = _query(f"""
        SELECT COUNT(*)                             AS total_operations,
               ROUND(SUM(ops.Duration), 1)         AS total_hours,
               ROUND(AVG(ops.Duration), 2)         AS avg_op_duration_hrs,
               COUNT(DISTINCT dh.Rig_Id)           AS rigs_involved
        FROM eos_Drilling_Dtl_Ops ops
        JOIN eos_Drilling_Dtl dd  ON ops.Drilling_Dtl_Id  = dd.Drilling_Dtl_Id
        JOIN eos_Drilling_Hdr dh  ON dd.Drilling_Hdr_Id   = dh.Drilling_Hdr_Id
        WHERE {where}
    """, tuple(params))

    by_rig = _query(f"""
        SELECT r.Rig_Name, COUNT(*) AS operations, ROUND(SUM(ops.Duration), 1) AS total_hours
        FROM eos_Drilling_Dtl_Ops ops
        JOIN eos_Drilling_Dtl dd  ON ops.Drilling_Dtl_Id  = dd.Drilling_Dtl_Id
        JOIN eos_Drilling_Hdr dh  ON dd.Drilling_Hdr_Id   = dh.Drilling_Hdr_Id
        JOIN eos_Mst_Rig r        ON dh.Rig_Id            = r.Rig_Id AND r.Rig_Type_Id IN (1,2)
        WHERE {where} GROUP BY r.Rig_Name ORDER BY total_hours DESC
    """, tuple(params))

    by_year = _query(f"""
        SELECT YEAR(ops.Time_From) AS year, COUNT(*) AS operations,
               ROUND(SUM(ops.Duration), 1) AS total_hours
        FROM eos_Drilling_Dtl_Ops ops
        JOIN eos_Drilling_Dtl dd  ON ops.Drilling_Dtl_Id  = dd.Drilling_Dtl_Id
        JOIN eos_Drilling_Hdr dh  ON dd.Drilling_Hdr_Id   = dh.Drilling_Hdr_Id
        WHERE {where} GROUP BY year ORDER BY year DESC LIMIT 6
    """, tuple(params))

    return {
        "tool": "get_drilling_hours",
        "filters": {"rig": rig, "year": year},
        "summary": summary[0] if summary else {},
        "by_rig": by_rig,
        "by_year": by_year,
    }


# ── Tool 7: Drilling Performance (ROP) ───────────────────────────────────────

def get_drilling_performance(rig: str | None = None, year: int | None = None) -> dict:
    """
    Drilling performance: Rate of Penetration (ROP) in metres per hour.

    Source: eos_Drilling_Dtl_Ops, Drilling_Ops_Id = 2 (Drill actual),
            only rows where Depth_To > Depth_From (actual progress).

    ROP (m/hr) = SUM(Depth_To - Depth_From) / SUM(Duration)
    Broken down by hole section and includes full operation hours breakdown.
    """
    drill_conds = [
        "ops.Drilling_Ops_Id = 2",
        "(ops.Depth_To - ops.Depth_From) > 0",
    ]
    drill_params: list = []

    all_conds: list = []
    all_params: list = []

    if rig:
        rig_id = _rig_id(rig)
        if rig_id is None:
            return {"tool": "get_drilling_performance", "error": f"Rig '{rig}' not found."}
        drill_conds.append("dd.Rig_Id = %s")
        drill_params.append(rig_id)
        all_conds.append("dd.Rig_Id = %s")
        all_params.append(rig_id)
    if year:
        drill_conds.append("YEAR(ops.Time_From) = %s")
        drill_params.append(year)
        all_conds.append("YEAR(ops.Time_From) = %s")
        all_params.append(year)

    drill_where = " AND ".join(drill_conds)
    all_where   = " AND ".join(all_conds) if all_conds else "1=1"

    # ── Overall ROP summary ────────────────────────────────────────────────────
    summary = _query(f"""
        SELECT
            ROUND(SUM(ops.Depth_To - ops.Depth_From), 1)                                       AS total_metres,
            ROUND(SUM(ops.Duration), 1)                                                          AS total_drill_hrs,
            ROUND(SUM(ops.Depth_To - ops.Depth_From) / NULLIF(SUM(ops.Duration), 0), 2)        AS rop_mhr,
            COUNT(*)                                                                              AS drill_operations,
            COUNT(DISTINCT dd.Rig_Id)                                                            AS rigs_covered
        FROM eos_Drilling_Dtl_Ops ops
        JOIN eos_Drilling_Dtl dd ON ops.Drilling_Dtl_Id = dd.Drilling_Dtl_Id
        WHERE {drill_where}
    """, tuple(drill_params))

    # ── By hole section ────────────────────────────────────────────────────────
    by_section = _query(f"""
        SELECT
            s.Drilling_Section_Name                                                              AS section,
            ROUND(SUM(ops.Depth_To - ops.Depth_From), 1)                                       AS metres,
            ROUND(SUM(ops.Duration), 1)                                                          AS drill_hrs,
            ROUND(SUM(ops.Depth_To - ops.Depth_From) / NULLIF(SUM(ops.Duration), 0), 2)        AS rop_mhr,
            COUNT(*)                                                                              AS operations
        FROM eos_Drilling_Dtl_Ops ops
        JOIN eos_Drilling_Dtl dd ON ops.Drilling_Dtl_Id = dd.Drilling_Dtl_Id
        JOIN eos_Mst_Drilling_Section s ON ops.Drilling_Section_Id = s.Drilling_Section_Id
        WHERE {drill_where}
        GROUP BY s.Drilling_Section_Id, s.Drilling_Section_Name
        ORDER BY metres DESC
    """, tuple(drill_params))

    # ── Full operation hours breakdown (all ops, not just drilling) ────────────
    ops_breakdown = _query(f"""
        SELECT
            mo.Drilling_Ops_Name                  AS operation,
            ROUND(SUM(ops.Duration), 1)            AS hours,
            COUNT(*)                               AS records
        FROM eos_Drilling_Dtl_Ops ops
        JOIN eos_Drilling_Dtl dd ON ops.Drilling_Dtl_Id = dd.Drilling_Dtl_Id
        JOIN eos_Mst_Drilling_Operations mo ON ops.Drilling_Ops_Id = mo.Drilling_Ops_Id
        WHERE {all_where}
        GROUP BY mo.Drilling_Ops_Id, mo.Drilling_Ops_Name
        ORDER BY hours DESC
    """, tuple(all_params))

    total_all_hrs = sum(float(r["hours"] or 0) for r in ops_breakdown)
    for r in ops_breakdown:
        r["pct"] = round(float(r["hours"] or 0) / total_all_hrs * 100, 1) if total_all_hrs else 0

    # ── Flat time: operations with zero depth progress ─────────────────────────
    # Rows where Duration > 0 but no new hole made (Depth_To = Depth_From).
    # Grouped by op type so the user can see *what* was consuming non-drilling time.
    flat_conds  = ["(ops.Depth_To - ops.Depth_From) = 0", "ops.Duration > 0"] + all_conds
    flat_time = _query(f"""
        SELECT
            mo.Drilling_Ops_Name                   AS operation,
            ROUND(SUM(ops.Duration), 1)             AS hours,
            COUNT(*)                                AS records
        FROM eos_Drilling_Dtl_Ops ops
        JOIN eos_Drilling_Dtl dd ON ops.Drilling_Dtl_Id = dd.Drilling_Dtl_Id
        JOIN eos_Mst_Drilling_Operations mo ON ops.Drilling_Ops_Id = mo.Drilling_Ops_Id
        WHERE {" AND ".join(flat_conds)}
        GROUP BY mo.Drilling_Ops_Id, mo.Drilling_Ops_Name
        ORDER BY hours DESC
        LIMIT 20
    """, tuple(all_params))

    total_flat_hrs = sum(float(r["hours"] or 0) for r in flat_time)
    for r in flat_time:
        r["pct"] = round(float(r["hours"] or 0) / total_flat_hrs * 100, 1) if total_flat_hrs else 0

    # Per-operation per-rig flat time — used for drill-down in the dashboard
    flat_time_rig_detail = _query(f"""
        SELECT
            mo.Drilling_Ops_Name               AS operation,
            r.Rig_Name,
            ROUND(SUM(ops.Duration), 1)         AS hours
        FROM eos_Drilling_Dtl_Ops ops
        JOIN eos_Drilling_Dtl dd ON ops.Drilling_Dtl_Id = dd.Drilling_Dtl_Id
        JOIN eos_Mst_Drilling_Operations mo ON ops.Drilling_Ops_Id = mo.Drilling_Ops_Id
        JOIN eos_Mst_Rig r ON dd.Rig_Id = r.Rig_Id AND r.Rig_Type_Id IN (1,2)
        WHERE {" AND ".join(flat_conds)}
        GROUP BY mo.Drilling_Ops_Id, mo.Drilling_Ops_Name, r.Rig_Id, r.Rig_Name
        ORDER BY mo.Drilling_Ops_Name, hours DESC
    """, tuple(all_params))

    # ── Metres drilled per location per rig (always all rigs, year-filtered) ───
    loc_conds  = ["ops.Drilling_Ops_Id = 2", "(ops.Depth_To - ops.Depth_From) > 0"]
    loc_params: list = []
    if year:
        loc_conds.append("YEAR(ops.Time_From) = %s")
        loc_params.append(year)

    locations_by_rig = _query(f"""
        SELECT
            r.Rig_Name,
            h.Location,
            h.Latitude,
            h.Longitude,
            DATE_FORMAT(h.First_Anchor_Down_Dt, '%%Y-%%m-%%d')  AS spud_dt,
            DATE_FORMAT(h.Drilling_Completion_Dt, '%%Y-%%m-%%d') AS completion_dt,
            ROUND(SUM(ops.Depth_To - ops.Depth_From), 1)                                       AS metres,
            ROUND(SUM(ops.Duration), 1)                                                          AS drill_hrs,
            ROUND(SUM(ops.Depth_To - ops.Depth_From) / NULLIF(SUM(ops.Duration), 0), 2)        AS rop_mhr
        FROM eos_Drilling_Dtl_Ops ops
        JOIN eos_Drilling_Dtl dd ON ops.Drilling_Dtl_Id = dd.Drilling_Dtl_Id
        JOIN eos_Drilling_Hdr h  ON dd.Drilling_Hdr_Id  = h.Drilling_Hdr_Id
        JOIN eos_Mst_Rig r       ON dd.Rig_Id           = r.Rig_Id AND r.Rig_Type_Id IN (1,2)
        WHERE {" AND ".join(loc_conds)}
        GROUP BY r.Rig_Id, r.Rig_Name, h.Drilling_Hdr_Id, h.Location,
                 h.Latitude, h.Longitude, h.First_Anchor_Down_Dt, h.Drilling_Completion_Dt
        ORDER BY r.Rig_Name, metres DESC
    """, tuple(loc_params))

    # ── ROP by rig (year-filtered, no rig filter — always shows all rigs) ──────
    rop_rig_conds  = ["ops.Drilling_Ops_Id = 2", "(ops.Depth_To - ops.Depth_From) > 0"]
    rop_rig_params: list = []
    if year:
        rop_rig_conds.append("YEAR(ops.Time_From) = %s")
        rop_rig_params.append(year)

    rop_by_rig = _query(f"""
        SELECT
            r.Rig_Name,
            ROUND(SUM(ops.Depth_To - ops.Depth_From), 1)                                       AS metres,
            ROUND(SUM(ops.Duration), 1)                                                          AS drill_hrs,
            ROUND(SUM(ops.Depth_To - ops.Depth_From) / NULLIF(SUM(ops.Duration), 0), 2)        AS rop_mhr,
            COUNT(*)                                                                              AS operations
        FROM eos_Drilling_Dtl_Ops ops
        JOIN eos_Drilling_Dtl dd ON ops.Drilling_Dtl_Id = dd.Drilling_Dtl_Id
        JOIN eos_Mst_Rig r ON dd.Rig_Id = r.Rig_Id AND r.Rig_Type_Id IN (1,2)
        WHERE {" AND ".join(rop_rig_conds)}
        GROUP BY r.Rig_Id, r.Rig_Name
        HAVING drill_hrs > 0
        ORDER BY rop_mhr DESC
    """, tuple(rop_rig_params))

    # ── Year-over-year ROP trend (no year filter) ──────────────────────────────
    yoy_conds = ["ops.Drilling_Ops_Id = 2", "(ops.Depth_To - ops.Depth_From) > 0"]
    yoy_params: list = []
    if rig:
        yoy_conds.append("dd.Rig_Id = %s")
        yoy_params.append(_rig_id(rig))

    yoy = _query(f"""
        SELECT
            YEAR(ops.Time_From)                                                                  AS yr,
            ROUND(SUM(ops.Depth_To - ops.Depth_From), 1)                                       AS total_metres,
            ROUND(SUM(ops.Duration), 1)                                                          AS drill_hrs,
            ROUND(SUM(ops.Depth_To - ops.Depth_From) / NULLIF(SUM(ops.Duration), 0), 2)        AS rop_mhr
        FROM eos_Drilling_Dtl_Ops ops
        JOIN eos_Drilling_Dtl dd ON ops.Drilling_Dtl_Id = dd.Drilling_Dtl_Id
        WHERE {" AND ".join(yoy_conds)}
        GROUP BY yr ORDER BY yr DESC LIMIT 6
    """, tuple(yoy_params))

    return {
        "tool": "get_drilling_performance",
        "filters": {"rig": rig, "year": year},
        "summary": summary[0] if summary else {},
        "by_section": by_section,
        "ops_breakdown": ops_breakdown,
        "flat_time": flat_time,
        "flat_time_total_hrs": round(total_flat_hrs, 1),
        "flat_time_rig_detail": flat_time_rig_detail,
        "locations_by_rig": locations_by_rig,
        "rop_by_rig": rop_by_rig,
        "yoy": list(reversed(yoy)),
    }


# ── Tool 8: Rig utilisation rate ─────────────────────────────────────────────

# Productive operations — time the rig is making progress (billable work)
_PRODUCTIVE_OPS = {2, 3, 4, 5, 6, 10, 11, 12, 13, 14, 15, 16, 17, 18, 20, 22, 26, 28, 29, 30, 31, 32, 33}
# NPT operation id
_NPT_OP_ID = 24


def get_rig_utilisation(
    rig: str | None = None,
    year: int | None = None,
    month: int | None = None,
) -> dict:
    """
    Rig utilisation from eos_Drilling_Dtl (daily logs).

    Utilisation % = Operating_Hrs / total_logged_hrs × 100
    where total = Operating + Standby + Repair + Zero_Rate + Rig_Move

    Returns monthly breakdown and summary stats.
    rig   : rig name or short name (required for single-rig view)
    year  : filter by year
    month : filter by month (1-12), only useful alongside year
    """
    conditions = ["dd.Cr_Status IS NOT NULL"]   # only submitted daily logs
    params: list = []

    if rig:
        rig_id = _rig_id(rig)
        if rig_id is None:
            return {"tool": "get_rig_utilisation", "error": f"Rig '{rig}' not found."}
        conditions.append("dd.Rig_Id = %s")
        params.append(rig_id)
    if year:
        conditions.append("YEAR(dd.Drilling_Dtl_Dt) = %s")
        params.append(year)
    if month:
        conditions.append("MONTH(dd.Drilling_Dtl_Dt) = %s")
        params.append(month)

    where = " AND ".join(conditions)

    # Monthly breakdown
    monthly = _query(f"""
        SELECT
            r.Rig_Name,
            DATE_FORMAT(dd.Drilling_Dtl_Dt, '%%Y-%%m')   AS month,
            COUNT(*)                                     AS days_logged,
            ROUND(SUM(COALESCE(dd.Operating_Hrs, 0)), 1)      AS operating_hrs,
            ROUND(SUM(COALESCE(dd.Standby_Hrs, 0)), 1)        AS standby_hrs,
            ROUND(SUM(COALESCE(dd.Repair_Service_Hrs, 0)), 1)  AS repair_hrs,
            ROUND(SUM(COALESCE(dd.Zero_Rate_Hrs, 0)), 1)       AS zero_rate_hrs,
            ROUND(SUM(COALESCE(dd.Rig_Move_Hrs, 0)), 1)        AS rig_move_hrs,
            ROUND(
                SUM(COALESCE(dd.Operating_Hrs, 0)) /
                NULLIF(
                    SUM(COALESCE(dd.Operating_Hrs, 0))
                    + SUM(COALESCE(dd.Standby_Hrs, 0))
                    + SUM(COALESCE(dd.Repair_Service_Hrs, 0))
                    + SUM(COALESCE(dd.Zero_Rate_Hrs, 0))
                    + SUM(COALESCE(dd.Rig_Move_Hrs, 0)),
                0) * 100, 1
            )                                            AS utilisation_pct
        FROM eos_Drilling_Dtl dd
        JOIN eos_Mst_Rig r ON dd.Rig_Id = r.Rig_Id AND r.Rig_Type_Id IN (1,2)
        WHERE {where}
        GROUP BY r.Rig_Name, month
        ORDER BY r.Rig_Name, month DESC
        LIMIT 2000
    """, tuple(params))

    # Overall summary
    summary = _query(f"""
        SELECT
            ROUND(SUM(COALESCE(dd.Operating_Hrs, 0)), 1)       AS total_operating_hrs,
            ROUND(SUM(COALESCE(dd.Standby_Hrs, 0)), 1)         AS total_standby_hrs,
            ROUND(SUM(COALESCE(dd.Repair_Service_Hrs, 0)), 1)   AS total_repair_hrs,
            ROUND(SUM(COALESCE(dd.Zero_Rate_Hrs, 0)), 1)        AS total_zero_rate_hrs,
            ROUND(SUM(COALESCE(dd.Rig_Move_Hrs, 0)), 1)         AS total_rig_move_hrs,
            ROUND(
                SUM(COALESCE(dd.Operating_Hrs, 0)) /
                NULLIF(
                    SUM(COALESCE(dd.Operating_Hrs, 0))
                    + SUM(COALESCE(dd.Standby_Hrs, 0))
                    + SUM(COALESCE(dd.Repair_Service_Hrs, 0))
                    + SUM(COALESCE(dd.Zero_Rate_Hrs, 0))
                    + SUM(COALESCE(dd.Rig_Move_Hrs, 0)),
                0) * 100, 1
            )                                                    AS avg_utilisation_pct,
            COUNT(DISTINCT dd.Rig_Id)                           AS rigs_covered
        FROM eos_Drilling_Dtl dd
        WHERE {where}
    """, tuple(params))

    # Best and worst months (only if monthly has data)
    best  = max(monthly, key=lambda r: r["utilisation_pct"] or 0) if monthly else None
    worst = min(monthly, key=lambda r: r["utilisation_pct"] or 0) if monthly else None

    return {
        "tool": "get_rig_utilisation",
        "display": "dashboard",          # signals the view to render a table
        "filters": {"rig": rig, "year": year, "month": month},
        "summary": summary[0] if summary else {},
        "best_month":  {"month": best["month"],  "utilisation_pct": best["utilisation_pct"],  "rig": best["Rig_Name"]}  if best  else None,
        "worst_month": {"month": worst["month"], "utilisation_pct": worst["utilisation_pct"], "rig": worst["Rig_Name"]} if worst else None,
        "monthly": monthly,
    }


# ── Tool 9: NPT Analysis ─────────────────────────────────────────────────────

def get_npt_analysis(rig: str | None = None, year: int | None = None) -> dict:
    """
    Non-Productive Time (NPT) analysis.

    Source A: eos_Drilling_Dtl_Ops where Drilling_Ops_Id = 24 ("Non productive time").
              Each row has Duration and Operation_Desc (free text) + Downtime_Reason
              from the joined eos_Drilling_Dtl daily log.
    Source B: Total logged hours from eos_Drilling_Dtl_Ops (all ops) — used to compute NPT%.
    Source C: eos_Incident_Details.NPT_Hrs_Loss — NPT caused by incidents.

    NPT% = SUM(NPT Duration) / SUM(all-ops Duration) × 100
    """
    conds:  list = ["ops.Drilling_Ops_Id = 24"]
    params: list = []

    all_conds:  list = []
    all_params: list = []

    inc_conds:  list = ["COALESCE(i.Marked_As_Deleted, '') != 'Y'", "i.NPT_Hrs_Loss > 0"]
    inc_params: list = []

    if rig:
        rig_id = _rig_id(rig)
        if rig_id is None:
            return {"tool": "get_npt_analysis", "error": f"Rig '{rig}' not found."}
        conds.append("dd.Rig_Id = %s")
        params.append(rig_id)
        all_conds.append("dd.Rig_Id = %s")
        all_params.append(rig_id)
        inc_conds.append("i.Rig_Id = %s")
        inc_params.append(rig_id)

    if year:
        conds.append("YEAR(ops.Time_From) = %s")
        params.append(year)
        all_conds.append("YEAR(ops.Time_From) = %s")
        all_params.append(year)
        inc_conds.append("YEAR(i.Incident_Date) = %s")
        inc_params.append(year)

    npt_where = " AND ".join(conds)
    all_where  = " AND ".join(all_conds) if all_conds else "1=1"

    # ── NPT summary ────────────────────────────────────────────────────────────
    npt_summary = _query(f"""
        SELECT
            ROUND(SUM(ops.Duration), 1)   AS total_npt_hrs,
            COUNT(*)                       AS npt_events,
            ROUND(AVG(ops.Duration), 2)   AS avg_event_hrs
        FROM eos_Drilling_Dtl_Ops ops
        JOIN eos_Drilling_Dtl dd ON ops.Drilling_Dtl_Id = dd.Drilling_Dtl_Id
        WHERE {npt_where}
    """, tuple(params))

    # ── Total logged hours (denominator for NPT%) ──────────────────────────────
    total_hrs_row = _query(f"""
        SELECT ROUND(SUM(ops.Duration), 1) AS total_hrs
        FROM eos_Drilling_Dtl_Ops ops
        JOIN eos_Drilling_Dtl dd ON ops.Drilling_Dtl_Id = dd.Drilling_Dtl_Id
        WHERE {all_where}
    """, tuple(all_params))

    total_hrs  = float(total_hrs_row[0]["total_hrs"] or 0) if total_hrs_row else 0
    npt_hrs    = float(npt_summary[0]["total_npt_hrs"] or 0) if npt_summary else 0
    npt_pct    = round(npt_hrs / total_hrs * 100, 2) if total_hrs else None

    # ── Monthly NPT trend ──────────────────────────────────────────────────────
    monthly = _query(f"""
        SELECT
            DATE_FORMAT(ops.Time_From, '%%Y-%%m')  AS month,
            ROUND(SUM(ops.Duration), 1)              AS npt_hrs,
            COUNT(*)                                 AS events
        FROM eos_Drilling_Dtl_Ops ops
        JOIN eos_Drilling_Dtl dd ON ops.Drilling_Dtl_Id = dd.Drilling_Dtl_Id
        WHERE {npt_where}
        GROUP BY month
        ORDER BY month
    """, tuple(params))

    # ── NPT by rig (always all rigs, year-filtered only) ──────────────────────
    rig_conds  = ["ops.Drilling_Ops_Id = 24"]
    rig_params: list = []
    if year:
        rig_conds.append("YEAR(ops.Time_From) = %s")
        rig_params.append(year)

    npt_by_rig = _query(f"""
        SELECT
            r.Rig_Name,
            ROUND(SUM(ops.Duration), 1)  AS npt_hrs,
            COUNT(*)                      AS events,
            ROUND(AVG(ops.Duration), 2)  AS avg_hrs
        FROM eos_Drilling_Dtl_Ops ops
        JOIN eos_Drilling_Dtl dd ON ops.Drilling_Dtl_Id = dd.Drilling_Dtl_Id
        JOIN eos_Mst_Rig r       ON dd.Rig_Id           = r.Rig_Id AND r.Rig_Type_Id IN (1,2)
        WHERE {" AND ".join(rig_conds)}
        GROUP BY r.Rig_Id, r.Rig_Name
        ORDER BY npt_hrs DESC
    """, tuple(rig_params))

    # ── Top downtime reasons (from daily log Downtime_Reason label) ────────────
    top_reasons = _query(f"""
        SELECT
            TRIM(dd.Downtime_Reason)         AS reason,
            ROUND(SUM(ops.Duration), 1)       AS npt_hrs,
            COUNT(*)                           AS events
        FROM eos_Drilling_Dtl_Ops ops
        JOIN eos_Drilling_Dtl dd ON ops.Drilling_Dtl_Id = dd.Drilling_Dtl_Id
        WHERE {npt_where}
          AND dd.Downtime_Reason IS NOT NULL
          AND TRIM(dd.Downtime_Reason) != ''
        GROUP BY TRIM(dd.Downtime_Reason)
        ORDER BY npt_hrs DESC
        LIMIT 15
    """, tuple(params))

    # ── Reason × Rig breakdown (drill-down layer 1) ───────────────────────────
    reason_rig_detail = _query(f"""
        SELECT
            TRIM(dd.Downtime_Reason)         AS reason,
            r.Rig_Name                        AS rig,
            ROUND(SUM(ops.Duration), 1)       AS npt_hrs,
            COUNT(*)                           AS events
        FROM eos_Drilling_Dtl_Ops ops
        JOIN eos_Drilling_Dtl dd ON ops.Drilling_Dtl_Id = dd.Drilling_Dtl_Id
        JOIN eos_Mst_Rig r       ON dd.Rig_Id           = r.Rig_Id AND r.Rig_Type_Id IN (1,2)
        WHERE {npt_where}
          AND dd.Downtime_Reason IS NOT NULL
          AND TRIM(dd.Downtime_Reason) != ''
        GROUP BY TRIM(dd.Downtime_Reason), r.Rig_Id, r.Rig_Name
        ORDER BY reason, npt_hrs DESC
    """, tuple(params))

    # ── Reason × Rig × Month (drill-down layer 2) ────────────────────────────
    reason_rig_monthly = _query(f"""
        SELECT
            TRIM(dd.Downtime_Reason)              AS reason,
            r.Rig_Name                             AS rig,
            DATE_FORMAT(ops.Time_From, '%%Y-%%m') AS month,
            ROUND(SUM(ops.Duration), 1)            AS npt_hrs,
            COUNT(*)                                AS events
        FROM eos_Drilling_Dtl_Ops ops
        JOIN eos_Drilling_Dtl dd ON ops.Drilling_Dtl_Id = dd.Drilling_Dtl_Id
        JOIN eos_Mst_Rig r       ON dd.Rig_Id           = r.Rig_Id AND r.Rig_Type_Id IN (1,2)
        WHERE {npt_where}
          AND dd.Downtime_Reason IS NOT NULL
          AND TRIM(dd.Downtime_Reason) != ''
        GROUP BY TRIM(dd.Downtime_Reason), r.Rig_Id, r.Rig_Name, month
        ORDER BY reason, r.Rig_Name, month
    """, tuple(params))

    # ── NPT from incidents (Source C) ──────────────────────────────────────────
    inc_npt = _query(f"""
        SELECT
            ROUND(SUM(i.NPT_Hrs_Loss), 1)  AS incident_npt_hrs,
            COUNT(*)                         AS incidents_with_npt
        FROM eos_Incident_Details i
        WHERE {" AND ".join(inc_conds)}
    """, tuple(inc_params))

    # ── Year-over-year NPT trend (no year filter) ──────────────────────────────
    yoy_conds  = ["ops.Drilling_Ops_Id = 24"]
    yoy_params: list = []
    if rig:
        yoy_conds.append("dd.Rig_Id = %s")
        yoy_params.append(_rig_id(rig))

    yoy = _query(f"""
        SELECT
            YEAR(ops.Time_From)             AS yr,
            ROUND(SUM(ops.Duration), 1)      AS npt_hrs,
            COUNT(*)                          AS events
        FROM eos_Drilling_Dtl_Ops ops
        JOIN eos_Drilling_Dtl dd ON ops.Drilling_Dtl_Id = dd.Drilling_Dtl_Id
        WHERE {" AND ".join(yoy_conds)}
        GROUP BY yr ORDER BY yr DESC LIMIT 6
    """, tuple(yoy_params))

    # ── Monthly NPT per rig (for drill-down: click rig → show its monthly trend) ─
    mrd_conds  = ["ops.Drilling_Ops_Id = 24"]
    mrd_params: list = []
    if year:
        mrd_conds.append("YEAR(ops.Time_From) = %s")
        mrd_params.append(year)

    monthly_rig_detail = _query(f"""
        SELECT
            r.Rig_Name                                   AS rig,
            DATE_FORMAT(ops.Time_From, '%%Y-%%m')        AS month,
            ROUND(SUM(ops.Duration), 1)                  AS npt_hrs,
            COUNT(*)                                      AS events
        FROM eos_Drilling_Dtl_Ops ops
        JOIN eos_Drilling_Dtl dd ON ops.Drilling_Dtl_Id = dd.Drilling_Dtl_Id
        JOIN eos_Mst_Rig r       ON dd.Rig_Id           = r.Rig_Id AND r.Rig_Type_Id IN (1,2)
        WHERE {" AND ".join(mrd_conds)}
        GROUP BY r.Rig_Id, r.Rig_Name, month
        ORDER BY r.Rig_Name, month
    """, tuple(mrd_params))

    return {
        "tool": "get_npt_analysis",
        "filters": {"rig": rig, "year": year},
        "summary": {
            "total_npt_hrs":    npt_hrs,
            "npt_events":       int(npt_summary[0]["npt_events"] or 0) if npt_summary else 0,
            "avg_event_hrs":    float(npt_summary[0]["avg_event_hrs"] or 0) if npt_summary else 0,
            "total_logged_hrs": total_hrs,
            "npt_pct":          npt_pct,
        },
        "monthly":     [{"month": r["month"], "npt_hrs": float(r["npt_hrs"] or 0), "events": int(r["events"])} for r in monthly],
        "npt_by_rig":  [{"rig": r["Rig_Name"], "npt_hrs": float(r["npt_hrs"] or 0), "events": int(r["events"]), "avg_hrs": float(r["avg_hrs"] or 0)} for r in npt_by_rig],
        "top_reasons":        [{"reason": r["reason"], "npt_hrs": float(r["npt_hrs"] or 0), "events": int(r["events"])} for r in top_reasons],
        "reason_rig_detail":  [{"reason": r["reason"], "rig": r["rig"], "npt_hrs": float(r["npt_hrs"] or 0), "events": int(r["events"])} for r in reason_rig_detail],
        "reason_rig_monthly": [{"reason": r["reason"], "rig": r["rig"], "month": r["month"], "npt_hrs": float(r["npt_hrs"] or 0), "events": int(r["events"])} for r in reason_rig_monthly],
        "incident_npt": {
            "incident_npt_hrs":     float(inc_npt[0]["incident_npt_hrs"] or 0) if inc_npt else 0,
            "incidents_with_npt":   int(inc_npt[0]["incidents_with_npt"] or 0) if inc_npt else 0,
        },
        "yoy": [{"yr": int(r["yr"]), "npt_hrs": float(r["npt_hrs"] or 0), "events": int(r["events"])} for r in reversed(yoy)],
        "monthly_rig_detail": [{"rig": r["rig"], "month": r["month"], "npt_hrs": float(r["npt_hrs"] or 0), "events": int(r["events"])} for r in monthly_rig_detail],
    }


# ── Tool 10: Drilling locations ───────────────────────────────────────────────

def get_rig_locations(rig: str | None = None, year: int | None = None) -> dict:
    """
    Locations (wells) drilled by Seros rigs.

    Source: eos_Drilling_Hdr (one row per well/location assignment).
    Year filter captures wells active at any point during the year:
        First_Anchor_Down_Dt <= end-of-year  AND
        (Drilling_Completion_Dt IS NULL  OR  YEAR(completion) >= year)

    Returns per-location detail with spud date, completion date, metres drilled,
    drilling hours, ROP, and coordinates. Ongoing wells have completion_dt = None.
    """
    conds:  list = []
    params: list = []

    if rig:
        rig_id = _rig_id(rig)
        if rig_id is None:
            return {"tool": "get_rig_locations", "error": f"Rig '{rig}' not found."}
        conds.append("h.Rig_Id = %s")
        params.append(rig_id)

    if year:
        # Include wells that were active at any point during the year
        conds.append("YEAR(h.First_Anchor_Down_Dt) <= %s")
        params.append(year)
        conds.append("(h.Drilling_Completion_Dt IS NULL OR YEAR(h.Drilling_Completion_Dt) >= %s)")
        params.append(year)

    where = ("WHERE " + " AND ".join(conds)) if conds else ""

    locations = _query(f"""
        SELECT
            r.Rig_Name,
            h.Location,
            h.Latitude,
            h.Longitude,
            DATE_FORMAT(h.First_Anchor_Down_Dt,   '%%Y-%%m-%%d') AS spud_dt,
            DATE_FORMAT(h.Drilling_Completion_Dt,  '%%Y-%%m-%%d') AS completion_dt,
            h.Total_Depth,
            ROUND(SUM(ops.Depth_To - ops.Depth_From), 1)                                    AS metres_drilled,
            ROUND(SUM(ops.Duration), 1)                                                       AS drill_hrs,
            ROUND(SUM(ops.Depth_To - ops.Depth_From) / NULLIF(SUM(ops.Duration), 0), 2)     AS rop_mhr
        FROM eos_Drilling_Hdr h
        JOIN eos_Mst_Rig r          ON h.Rig_Id           = r.Rig_Id AND r.Rig_Type_Id IN (1,2)
        LEFT JOIN eos_Drilling_Dtl dd  ON dd.Drilling_Hdr_Id = h.Drilling_Hdr_Id
        LEFT JOIN eos_Drilling_Dtl_Ops ops ON ops.Drilling_Dtl_Id = dd.Drilling_Dtl_Id
                                          AND ops.Drilling_Ops_Id = 2
                                          AND (ops.Depth_To - ops.Depth_From) > 0
        {where}
        GROUP BY r.Rig_Name, h.Drilling_Hdr_Id, h.Location,
                 h.Latitude, h.Longitude, h.First_Anchor_Down_Dt,
                 h.Drilling_Completion_Dt, h.Total_Depth
        ORDER BY h.First_Anchor_Down_Dt DESC
    """, tuple(params))

    ongoing   = [l for l in locations if not l["completion_dt"]]
    completed = [l for l in locations if l["completion_dt"]]

    return {
        "tool": "get_rig_locations",
        "filters": {"rig": rig, "year": year},
        "summary": {
            "total_locations": len(locations),
            "ongoing":         len(ongoing),
            "completed":       len(completed),
        },
        "locations": [
            {
                "rig":           r["Rig_Name"],
                "location":      r["Location"],
                "latitude":      r.get("Latitude") or "",
                "longitude":     r.get("Longitude") or "",
                "spud_dt":       r.get("spud_dt") or "",
                "completion_dt": r.get("completion_dt") or "",
                "status":        "Ongoing" if not r.get("completion_dt") else "Completed",
                "metres_drilled": float(r["metres_drilled"] or 0),
                "drill_hrs":      float(r["drill_hrs"]      or 0),
                "rop_mhr":        float(r["rop_mhr"]        or 0) if r["rop_mhr"] else None,
                "total_depth":    r.get("Total_Depth"),
            }
            for r in locations
        ],
    }


# ── Tool 11: HSE Dashboard ─────────────────────────────────────────────────────

def get_hse_dashboard(rig: str | None = None, year: int | None = None) -> dict:
    """
    HSE dashboard metrics:
    - submission_monthly: hazard card submissions per month (last 6 years)
    - inc_monthly: incident count per month (for ratio chart)
    - by_type: breakdown by hazard type (Positive Recognition / Unsafe Act / Unsafe Condition)
    - by_work_location: top 8 work locations by card count
    - by_dept: top 8 responsible departments by card count
    - card_ageing: open card age buckets (<30d, 30-60d, 60-90d, >90d)
    - oldest_open_cards: top 10 oldest open cards
    - closure_by_rig: corrective action closure rate per rig
    - summary: key KPIs
    """
    rig_id_val = None
    if rig:
        rig_id_val = _rig_id(rig)
        if rig_id_val is None:
            return {"tool": "get_hse_dashboard", "error": f"Rig '{rig}' not found."}

    haz_conds  = ["COALESCE(h.Marked_As_Deleted, '') != 'Y'"]
    inc_conds  = ["COALESCE(i.Marked_As_Deleted, '') != 'Y'"]
    haz_params: list = []
    inc_params: list = []

    if rig_id_val:
        haz_conds.append("h.Rig_Id = %s");  haz_params.append(rig_id_val)
        inc_conds.append("i.Rig_Id = %s");  inc_params.append(rig_id_val)
    if year:
        haz_conds.append("YEAR(h.Event_Dt) = %s");       haz_params.append(year)
        inc_conds.append("YEAR(i.Incident_Date) = %s");  inc_params.append(year)

    haz_where = " AND ".join(haz_conds)
    inc_where  = " AND ".join(inc_conds)

    # ── 1. Submission trend (last 6 years, monthly) ────────────────────────────
    submission_monthly = _query(f"""
        SELECT DATE_FORMAT(h.Event_Dt, '%%Y-%%m') AS month,
               COUNT(*) AS cards,
               SUM(CASE WHEN h.Haz_ID_Card_Status = 'C' THEN 1 ELSE 0 END) AS closed,
               SUM(CASE WHEN h.Haz_ID_Card_Status != 'C' THEN 1 ELSE 0 END) AS open_cnt,
               SUM(CASE WHEN h.Timeout_For_Safety = 'Y' THEN 1 ELSE 0 END) AS tfs
        FROM eos_Hazard_ID_Card h
        WHERE {haz_where} AND h.Event_Dt >= DATE_SUB(CURDATE(), INTERVAL 6 YEAR)
        GROUP BY month ORDER BY month
    """, tuple(haz_params))

    # ── 1b. Monthly breakdown by hazard type (for stacked bar) ────────────────
    submission_by_type_monthly = _query(f"""
        SELECT DATE_FORMAT(h.Event_Dt, '%%Y-%%m') AS month,
               t.Haz_Type_Name AS type_name,
               COUNT(*) AS cards
        FROM eos_Hazard_ID_Card h
        JOIN eos_Mst_Hazard_Type t ON h.Haz_Type_Id = t.Haz_Type_Id
        WHERE {haz_where} AND h.Event_Dt >= DATE_SUB(CURDATE(), INTERVAL 6 YEAR)
        GROUP BY month, t.Haz_Type_Id, t.Haz_Type_Name
        ORDER BY month
    """, tuple(haz_params))

    # ── 2. By hazard type ──────────────────────────────────────────────────────
    by_type = _query(f"""
        SELECT t.Haz_Type_Name AS type_name,
               t.Haz_Type_Class AS type_class,
               COUNT(*) AS cards,
               SUM(CASE WHEN h.Haz_ID_Card_Status = 'C' THEN 1 ELSE 0 END) AS closed,
               SUM(CASE WHEN h.Timeout_For_Safety = 'Y' THEN 1 ELSE 0 END) AS tfs_count
        FROM eos_Hazard_ID_Card h
        JOIN eos_Mst_Hazard_Type t ON h.Haz_Type_Id = t.Haz_Type_Id
        WHERE {haz_where}
        GROUP BY t.Haz_Type_Id, t.Haz_Type_Name, t.Haz_Type_Class
        ORDER BY cards DESC
    """, tuple(haz_params))

    # ── 3. By work location (top 8) ────────────────────────────────────────────
    by_work_location = _query(f"""
        SELECT w.Work_Location AS location,
               COUNT(*) AS cards,
               SUM(CASE WHEN h.Timeout_For_Safety = 'Y' THEN 1 ELSE 0 END) AS tfs_count
        FROM eos_Hazard_ID_Card h
        JOIN Mstx_Work_Location w ON h.Work_Location_Id = w.Work_Location_Id
        WHERE {haz_where}
        GROUP BY w.Work_Location_Id, w.Work_Location
        ORDER BY cards DESC LIMIT 8
    """, tuple(haz_params))

    # ── 3b. TFS by work location (ordered by TFS count, all locations) ────────
    tfs_by_location = _query(f"""
        SELECT w.Work_Location AS location,
               SUM(CASE WHEN h.Timeout_For_Safety = 'Y' THEN 1 ELSE 0 END) AS tfs_count,
               COUNT(*) AS total_cards,
               ROUND(
                 SUM(CASE WHEN h.Timeout_For_Safety = 'Y' THEN 1 ELSE 0 END) * 100.0 / COUNT(*),
                 1
               ) AS tfs_rate_pct
        FROM eos_Hazard_ID_Card h
        JOIN Mstx_Work_Location w ON h.Work_Location_Id = w.Work_Location_Id
        WHERE {haz_where}
        GROUP BY w.Work_Location_Id, w.Work_Location
        HAVING tfs_count > 0
        ORDER BY tfs_count DESC
        LIMIT 10
    """, tuple(haz_params))

    # ── 3c. TFS by rig ────────────────────────────────────────────────────────
    tfs_by_rig = _query(f"""
        SELECT r.Rig_Name AS rig,
               COUNT(*) AS total_cards,
               SUM(CASE WHEN h.Timeout_For_Safety = 'Y' THEN 1 ELSE 0 END) AS tfs_count,
               ROUND(
                 SUM(CASE WHEN h.Timeout_For_Safety = 'Y' THEN 1 ELSE 0 END) * 100.0 / COUNT(*),
                 1
               ) AS tfs_rate_pct,
               ROUND(AVG(
                 CASE WHEN h.Timeout_For_Safety = 'Y' AND h.Close_Out_Dt IS NOT NULL
                      THEN DATEDIFF(h.Close_Out_Dt, h.Event_Dt) END
               ), 1) AS avg_close_days_tfs
        FROM eos_Hazard_ID_Card h
        JOIN eos_Mst_Rig r ON h.Rig_Id = r.Rig_Id AND r.Rig_Type_Id IN (1,2)
        WHERE {haz_where}
        GROUP BY r.Rig_Name
        HAVING tfs_count > 0
        ORDER BY tfs_count DESC
    """, tuple(haz_params))

    # ── 4. By responsible department (top 8) ───────────────────────────────────
    by_dept = _query(f"""
        SELECT d.Dept_Name AS dept,
               COUNT(*) AS cards,
               SUM(CASE WHEN h.Haz_ID_Card_Status != 'C' THEN 1 ELSE 0 END) AS open_cnt
        FROM eos_Hazard_ID_Card h
        JOIN Mst_Department d ON h.Resp_Dept_Id = d.Dept_Id
        WHERE {haz_where}
        GROUP BY d.Dept_Id, d.Dept_Name
        ORDER BY cards DESC LIMIT 8
    """, tuple(haz_params))

    # ── 5. Incidents per month (for ratio chart) ───────────────────────────────
    inc_monthly = _query(f"""
        SELECT DATE_FORMAT(i.Incident_Date, '%%Y-%%m') AS month,
               COUNT(*) AS incidents
        FROM eos_Incident_Details i
        WHERE {inc_where}
        GROUP BY month ORDER BY month
    """, tuple(inc_params))

    # ── 6. Summary KPIs ────────────────────────────────────────────────────────
    haz_summary = _query(f"""
        SELECT COUNT(*) AS total_cards,
               SUM(CASE WHEN h.Haz_ID_Card_Status = 'C' THEN 1 ELSE 0 END) AS closed_cards,
               SUM(CASE WHEN h.Haz_ID_Card_Status != 'C' THEN 1 ELSE 0 END) AS open_cards,
               SUM(CASE WHEN h.Timeout_For_Safety = 'Y' THEN 1 ELSE 0 END) AS tfs_count,
               SUM(CASE WHEN h.Haz_ID_Card_Status != 'C'
                         AND DATEDIFF(CURDATE(), h.Event_Dt) > 30 THEN 1 ELSE 0 END) AS overdue_cards
        FROM eos_Hazard_ID_Card h WHERE {haz_where}
    """, tuple(haz_params))

    # ── 7. Open card ageing (always current snapshot, no year filter) ──────────
    age_conds  = ["COALESCE(h.Marked_As_Deleted, '') != 'Y'", "h.Haz_ID_Card_Status != 'C'"]
    age_params: list = []
    if rig_id_val:
        age_conds.append("h.Rig_Id = %s")
        age_params.append(rig_id_val)
    age_where = " AND ".join(age_conds)

    card_ageing = _query(f"""
        SELECT
            SUM(CASE WHEN DATEDIFF(CURDATE(), h.Event_Dt) < 30 THEN 1 ELSE 0 END)              AS lt_30,
            SUM(CASE WHEN DATEDIFF(CURDATE(), h.Event_Dt) BETWEEN 30 AND 59 THEN 1 ELSE 0 END) AS d30_60,
            SUM(CASE WHEN DATEDIFF(CURDATE(), h.Event_Dt) BETWEEN 60 AND 89 THEN 1 ELSE 0 END) AS d60_90,
            SUM(CASE WHEN DATEDIFF(CURDATE(), h.Event_Dt) >= 90 THEN 1 ELSE 0 END)             AS gt_90,
            COUNT(*) AS total_open,
            MAX(DATEDIFF(CURDATE(), h.Event_Dt)) AS max_age_days
        FROM eos_Hazard_ID_Card h WHERE {age_where}
    """, tuple(age_params))

    oldest_open_cards = _query(f"""
        SELECT h.Haz_ID_Card_No AS card_no,
               COALESCE(r.Rig_Name, 'Unknown') AS rig,
               DATE(h.Event_Dt) AS event_date,
               DATEDIFF(CURDATE(), h.Event_Dt) AS age_days
        FROM eos_Hazard_ID_Card h
        LEFT JOIN eos_Mst_Rig r ON h.Rig_Id = r.Rig_Id AND r.Rig_Type_Id IN (1,2)
        WHERE {age_where}
        ORDER BY age_days DESC LIMIT 10
    """, tuple(age_params))

    # ── 8. Corrective action closure ───────────────────────────────────────────
    act_conds  = ["COALESCE(a.Marked_As_Deleted, '') != 'Y'", "COALESCE(i.Marked_As_Deleted, '') != 'Y'"]
    act_params: list = []
    if rig_id_val:
        act_conds.append("i.Rig_Id = %s");  act_params.append(rig_id_val)
    if year:
        act_conds.append("YEAR(i.Incident_Date) = %s");  act_params.append(year)
    act_where = " AND ".join(act_conds)

    action_closure = _query(f"""
        SELECT
            COUNT(*) AS total_actions,
            SUM(CASE WHEN a.Action_Status = 'CL' THEN 1 ELSE 0 END) AS closed_actions,
            SUM(CASE WHEN a.Action_Status = 'CL' AND a.Completion_Dt IS NOT NULL
                          AND a.Completion_Dt <= a.Target_Date THEN 1 ELSE 0 END) AS on_time,
            SUM(CASE WHEN a.Action_Status != 'CL' AND a.Target_Date IS NOT NULL
                          AND a.Target_Date < CURDATE() THEN 1 ELSE 0 END) AS overdue
        FROM eos_Incident_Actions a
        JOIN eos_Incident_Details i ON a.Incident_Id = i.Incident_Id
        WHERE {act_where}
    """, tuple(act_params))

    closure_by_rig = _query(f"""
        SELECT r.Rig_Name,
               COUNT(*) AS total,
               SUM(CASE WHEN a.Action_Status = 'CL' THEN 1 ELSE 0 END) AS closed,
               SUM(CASE WHEN a.Action_Status != 'CL' AND a.Target_Date IS NOT NULL
                             AND a.Target_Date < CURDATE() THEN 1 ELSE 0 END) AS overdue
        FROM eos_Incident_Actions a
        JOIN eos_Incident_Details i ON a.Incident_Id = i.Incident_Id
        JOIN eos_Mst_Rig r ON i.Rig_Id = r.Rig_Id AND r.Rig_Type_Id IN (1,2)
        WHERE {act_where}
        GROUP BY r.Rig_Name ORDER BY total DESC
    """, tuple(act_params))

    s  = haz_summary[0]    if haz_summary    else {}
    ac = action_closure[0] if action_closure  else {}
    ag = card_ageing[0]    if card_ageing     else {}

    total_actions  = int(ac.get("total_actions")  or 0)
    closed_actions = int(ac.get("closed_actions") or 0)
    closure_rate   = round(closed_actions / total_actions * 100, 1) if total_actions else None

    total_cards  = int(s.get("total_cards") or 0)
    closed_cards = int(s.get("closed_cards") or 0)
    card_close_rate = round(closed_cards / total_cards * 100, 1) if total_cards else None

    return {
        "tool": "get_hse_dashboard",
        "filters": {"rig": rig, "year": year},
        "summary": {
            "total_cards":       total_cards,
            "open_cards":        int(s.get("open_cards")    or 0),
            "closed_cards":      closed_cards,
            "card_close_rate":   card_close_rate,
            "tfs_count":         int(s.get("tfs_count")     or 0),
            "overdue_cards":     int(s.get("overdue_cards") or 0),
            "total_actions":     total_actions,
            "closed_actions":    closed_actions,
            "overdue_actions":   int(ac.get("overdue")      or 0),
            "on_time_actions":   int(ac.get("on_time")      or 0),
            "closure_rate_pct":  closure_rate,
            "max_card_age_days": int(ag.get("max_age_days") or 0),
        },
        "submission_monthly":         submission_monthly,
        "submission_by_type_monthly": submission_by_type_monthly,
        "by_type":                    by_type,
        "by_work_location":           by_work_location,
        "tfs_by_rig":                 tfs_by_rig,
        "tfs_by_location":            tfs_by_location,
        "by_dept":                    by_dept,
        "inc_monthly":                inc_monthly,
        "card_ageing": {
            "lt_30":      int(ag.get("lt_30")      or 0),
            "d30_60":     int(ag.get("d30_60")     or 0),
            "d60_90":     int(ag.get("d60_90")     or 0),
            "gt_90":      int(ag.get("gt_90")      or 0),
            "total_open": int(ag.get("total_open") or 0),
        },
        "oldest_open_cards": oldest_open_cards,
        "closure_by_rig":    closure_by_rig,
    }


# ── Tool 5: Workforce dashboard ─────────────────────────────────────────────────

def get_workforce_dashboard(rig: str | None = None, year: int | None = None) -> dict:
    """
    Workforce dashboard metrics:
    - departures_by_rig / departures_by_rank: attrition via Final Settlement
      (Serv_Subtype_Id = 13 — the only subtype that means an employee left
      Seros for good; On Board/Off Board rows are routine rotation, not attrition)
    - tenure_by_rig: avg career length (first On Board to Final Settlement)
    - rotation_compliance_by_rig: actual sign-off date vs planned Appx_End_Dt
    - current_rotation_by_rig: live snapshot of who's on board now + overdue count
    - cert_expiry: individual crew certificate expiry buckets (fleet-wide —
      eos_Fs_Certificates has no rig linkage)
    - summary: key KPIs
    """
    rig_id_val = None
    if rig:
        rig_id_val = _rig_id(rig)
        if rig_id_val is None:
            return {"tool": "get_workforce_dashboard", "error": f"Rig '{rig}' not found."}

    dep_conds  = ["sd.Serv_Subtype_Id = 13"]
    dep_params: list = []
    if rig_id_val:
        dep_conds.append("sd.Rig_Id = %s"); dep_params.append(rig_id_val)
    if year:
        dep_conds.append("YEAR(sd.Serv_Subtype_From) = %s"); dep_params.append(year)
    dep_where = " AND ".join(dep_conds)

    # ── 1. Departures (attrition) by rig ───────────────────────────────────────
    departures_by_rig = _query(f"""
        SELECT r.Rig_Name AS rig, COUNT(*) AS departures
        FROM eos_Service_Details sd
        JOIN eos_Mst_Rig r ON sd.Rig_Id = r.Rig_Id AND r.Rig_Type_Id IN (1,2)
        WHERE {dep_where}
        GROUP BY r.Rig_Name ORDER BY departures DESC
    """, tuple(dep_params))

    # ── 1b. Departures by rank (top 10) ─────────────────────────────────────────
    departures_by_rank = _query(f"""
        SELECT mr.rank_name AS rank_name, COUNT(*) AS departures
        FROM eos_Service_Details sd
        JOIN eos_Mst_Rig r ON sd.Rig_Id = r.Rig_Id AND r.Rig_Type_Id IN (1,2)
        JOIN Mst_Rank mr ON sd.Rank_Id = mr.rank_id
        WHERE {dep_where}
        GROUP BY mr.rank_name ORDER BY departures DESC LIMIT 10
    """, tuple(dep_params))

    # ── 2. Average tenure by rig (closed careers only) ─────────────────────────
    tenure_conds  = ["fs.Serv_Subtype_Id = 13"]
    tenure_params: list = []
    if rig_id_val:
        tenure_conds.append("fs.Rig_Id = %s"); tenure_params.append(rig_id_val)
    if year:
        tenure_conds.append("YEAR(fs.Serv_Subtype_From) = %s"); tenure_params.append(year)
    tenure_where = " AND ".join(tenure_conds)

    tenure_by_rig = _query(f"""
        SELECT r.Rig_Name AS rig,
               ROUND(AVG(DATEDIFF(fs.Serv_Subtype_From, j.first_join)), 0) AS avg_tenure_days,
               COUNT(*) AS sample_size
        FROM eos_Service_Details fs
        JOIN (
            SELECT Fs_Emp_Id, MIN(Serv_Subtype_From) AS first_join
            FROM eos_Service_Details WHERE Serv_Subtype_Id = 7
            GROUP BY Fs_Emp_Id
        ) j ON j.Fs_Emp_Id = fs.Fs_Emp_Id
        JOIN eos_Mst_Rig r ON fs.Rig_Id = r.Rig_Id AND r.Rig_Type_Id IN (1,2)
        WHERE {tenure_where}
        GROUP BY r.Rig_Name
        ORDER BY avg_tenure_days DESC
    """, tuple(tenure_params))

    # ── 3. Rotation compliance by rig (completed On Board cycles) ──────────────
    rot_conds  = [
        "sd.Serv_Subtype_Id = 7",
        "sd.Serv_Subtype_To IS NOT NULL",
        "sd.Appx_End_Dt IS NOT NULL",
    ]
    rot_params: list = []
    if rig_id_val:
        rot_conds.append("sd.Rig_Id = %s"); rot_params.append(rig_id_val)
    if year:
        rot_conds.append("YEAR(sd.Serv_Subtype_From) = %s"); rot_params.append(year)
    rot_where = " AND ".join(rot_conds)

    rotation_compliance_by_rig = _query(f"""
        SELECT r.Rig_Name AS rig,
               COUNT(*) AS completed,
               SUM(CASE WHEN sd.Serv_Subtype_To <= sd.Appx_End_Dt THEN 1 ELSE 0 END) AS on_time,
               ROUND(SUM(CASE WHEN sd.Serv_Subtype_To <= sd.Appx_End_Dt THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS compliance_pct,
               ROUND(AVG(DATEDIFF(sd.Serv_Subtype_To, sd.Appx_End_Dt)), 1) AS avg_overrun_days
        FROM eos_Service_Details sd
        JOIN eos_Mst_Rig r ON sd.Rig_Id = r.Rig_Id AND r.Rig_Type_Id IN (1,2)
        WHERE {rot_where}
        GROUP BY r.Rig_Name
        ORDER BY compliance_pct ASC
    """, tuple(rot_params))

    # ── 4. Current rotation status (live snapshot — no year filter) ────────────
    # Includes every open On Board record, even very old ones that look like
    # abandoned data entries — surfaced as-is so data-quality gaps are visible
    # rather than silently hidden.
    cur_conds  = ["sd.Serv_Subtype_Id = 7", "sd.Serv_Subtype_To IS NULL"]
    cur_params: list = []
    if rig_id_val:
        cur_conds.append("sd.Rig_Id = %s"); cur_params.append(rig_id_val)
    cur_where = " AND ".join(cur_conds)

    current_rotation_by_rig = _query(f"""
        SELECT r.Rig_Name AS rig,
               COUNT(*) AS on_board,
               SUM(CASE WHEN sd.Appx_End_Dt IS NOT NULL AND sd.Appx_End_Dt < CURDATE() THEN 1 ELSE 0 END) AS overdue,
               ROUND(AVG(DATEDIFF(CURDATE(), sd.Serv_Subtype_From)), 0) AS avg_days_on_board,
               ROUND(AVG(CASE WHEN sd.Appx_End_Dt IS NOT NULL AND sd.Appx_End_Dt < CURDATE()
                              THEN DATEDIFF(CURDATE(), sd.Appx_End_Dt) END), 0) AS avg_days_overdue,
               MAX(CASE WHEN sd.Appx_End_Dt IS NOT NULL AND sd.Appx_End_Dt < CURDATE()
                        THEN DATEDIFF(CURDATE(), sd.Appx_End_Dt) END) AS max_days_overdue
        FROM eos_Service_Details sd
        JOIN eos_Mst_Rig r ON sd.Rig_Id = r.Rig_Id AND r.Rig_Type_Id IN (1,2)
        WHERE {cur_where}
        GROUP BY r.Rig_Name
        ORDER BY overdue DESC
    """, tuple(cur_params))

    # ── 4b. Crew roster — current crew per rig with designation breakdown ──────
    # Note: Appx_End_Dt is set once when a hitch starts and is rarely updated
    # going forward — in practice every populated value is already in the
    # past (240 of 253 open records) or null. "Due within 7 days" will almost
    # always be 0 as a result; it's kept for when/if that data practice improves.
    roster_due_conds = list(cur_conds) + [
        "sd.Appx_End_Dt IS NOT NULL",
        "sd.Appx_End_Dt BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 7 DAY)",
    ]
    roster_due_where = " AND ".join(roster_due_conds)

    due_7d_by_rig = _query(f"""
        SELECT r.Rig_Name AS rig, COUNT(*) AS due_7d
        FROM eos_Service_Details sd
        JOIN eos_Mst_Rig r ON sd.Rig_Id = r.Rig_Id AND r.Rig_Type_Id IN (1,2)
        WHERE {roster_due_where}
        GROUP BY r.Rig_Name
    """, tuple(cur_params))
    due_7d_map = {row["rig"]: int(row["due_7d"]) for row in due_7d_by_rig}

    designations_by_rig = _query(f"""
        SELECT r.Rig_Name AS rig, mr.rank_name AS rank_name, COUNT(*) AS cnt
        FROM eos_Service_Details sd
        JOIN eos_Mst_Rig r ON sd.Rig_Id = r.Rig_Id AND r.Rig_Type_Id IN (1,2)
        LEFT JOIN Mst_Rank mr ON sd.Rank_Id = mr.rank_id
        WHERE {cur_where}
        GROUP BY r.Rig_Name, mr.rank_name
        ORDER BY r.Rig_Name, cnt DESC
    """, tuple(cur_params))

    designations_map: dict = {}
    for row in designations_by_rig:
        designations_map.setdefault(row["rig"], []).append(
            {"rank_name": row["rank_name"] or "Unspecified", "cnt": int(row["cnt"])}
        )

    crew_roster_by_rig = [
        {
            "rig": row["rig"],
            "on_board": int(row["on_board"]),
            "overdue": int(row["overdue"]),
            "due_7d": due_7d_map.get(row["rig"], 0),
            "top_designations": designations_map.get(row["rig"], [])[:5],
        }
        for row in current_rotation_by_rig
    ]

    # ── 4c. Workforce composition — where the headcount actually comes from.
    # "On board" (crew_on_board above) is the narrow, precise figure; this
    # breaks out the wider population of everyone with any currently-open
    # service record, split by rig type plus non-rig assignments (office,
    # repair yard, well service) and non-"On Board" statuses (off board
    # between hitches, leave, standby, etc.) — the gap that explains why a
    # raw headcount query can land far higher than "crew on board now."
    composition_rows = _query("""
        SELECT
            COALESCE(rt.Rig_Type_Name, 'Unassigned / Non-Rig') AS category,
            sd.Serv_Subtype_Id = 7                              AS is_on_board,
            COUNT(DISTINCT sd.Fs_Emp_Id)                        AS cnt
        FROM eos_Service_Details sd
        LEFT JOIN eos_Mst_Rig r      ON sd.Rig_Id = r.Rig_Id
        LEFT JOIN Mst_Rig_Type rt    ON r.Rig_Type_Id = rt.Rig_Type_Id
        WHERE sd.Serv_Subtype_To IS NULL
        GROUP BY category, is_on_board
    """)
    workforce_composition = []
    for row in composition_rows:
        workforce_composition.append({
            "category": row["category"],
            "status": "On Board" if row["is_on_board"] else "Other Status",
            "cnt": int(row["cnt"]),
        })

    # ── 5. Crew cert expiry (fleet-wide — no rig linkage in source table) ──────
    cert_buckets = _query("""
        SELECT
            SUM(CASE WHEN Fs_Cert_Valid_Till < CURDATE() THEN 1 ELSE 0 END) AS expired,
            SUM(CASE WHEN Fs_Cert_Valid_Till >= CURDATE()
                          AND Fs_Cert_Valid_Till < CURDATE() + INTERVAL 30 DAY THEN 1 ELSE 0 END) AS due_30,
            SUM(CASE WHEN Fs_Cert_Valid_Till >= CURDATE() + INTERVAL 30 DAY
                          AND Fs_Cert_Valid_Till < CURDATE() + INTERVAL 90 DAY THEN 1 ELSE 0 END) AS due_90,
            SUM(CASE WHEN Fs_Cert_Valid_Till >= CURDATE() + INTERVAL 90 DAY THEN 1 ELSE 0 END) AS healthy
        FROM eos_Fs_Certificates
        WHERE Fs_Cert_Active = 'Y' AND Fs_Cert_Valid_Till IS NOT NULL
    """)

    cert_expiring_by_type = _query("""
        SELECT mc.cert_name AS cert_name, COUNT(*) AS cnt
        FROM eos_Fs_Certificates fc
        JOIN Mst_Cert mc ON fc.Cert_Id = mc.cert_id
        WHERE fc.Fs_Cert_Active = 'Y' AND fc.Fs_Cert_Valid_Till IS NOT NULL
          AND fc.Fs_Cert_Valid_Till < CURDATE() + INTERVAL 90 DAY
        GROUP BY mc.cert_name ORDER BY cnt DESC LIMIT 10
    """)

    # ── 6. Summary KPIs ──────────────────────────────────────────────────────
    total_departures = sum(int(r["departures"]) for r in departures_by_rig)

    tenure_days_list = [int(r["avg_tenure_days"]) for r in tenure_by_rig if r.get("avg_tenure_days") is not None]
    avg_tenure_days  = round(sum(tenure_days_list) / len(tenure_days_list), 0) if tenure_days_list else None

    total_completed = sum(int(r["completed"]) for r in rotation_compliance_by_rig)
    total_on_time   = sum(int(r["on_time"])   for r in rotation_compliance_by_rig)
    rotation_compliance_pct = round(total_on_time / total_completed * 100, 1) if total_completed else None

    crew_on_board     = sum(int(r["on_board"]) for r in current_rotation_by_rig)
    overdue_rotations = sum(int(r["overdue"])  for r in current_rotation_by_rig)

    # Weighted average overdue days across rigs (weighted by each rig's overdue count)
    _overdue_day_sum = sum(
        int(r["overdue"]) * float(r["avg_days_overdue"])
        for r in current_rotation_by_rig
        if r.get("avg_days_overdue") is not None and int(r["overdue"])
    )
    avg_days_overdue = round(_overdue_day_sum / overdue_rotations, 0) if overdue_rotations else None

    cb = cert_buckets[0] if cert_buckets else {}

    return {
        "tool": "get_workforce_dashboard",
        "filters": {"rig": rig, "year": year},
        "summary": {
            "total_departures":        total_departures,
            "avg_tenure_days":         avg_tenure_days,
            "rotation_compliance_pct": rotation_compliance_pct,
            "crew_on_board":           crew_on_board,
            "overdue_rotations":       overdue_rotations,
            "avg_days_overdue":        avg_days_overdue,
            "certs_expired":           int(cb.get("expired") or 0),
            "certs_due_30":            int(cb.get("due_30")  or 0),
        },
        "departures_by_rig":          departures_by_rig,
        "departures_by_rank":         departures_by_rank,
        "tenure_by_rig":              tenure_by_rig,
        "rotation_compliance_by_rig": rotation_compliance_by_rig,
        "current_rotation_by_rig":    current_rotation_by_rig,
        "crew_roster_by_rig":         crew_roster_by_rig,
        "workforce_composition":      workforce_composition,
        "cert_expiry_buckets": {
            "expired": int(cb.get("expired") or 0),
            "due_30":  int(cb.get("due_30")  or 0),
            "due_90":  int(cb.get("due_90")  or 0),
            "healthy": int(cb.get("healthy") or 0),
        },
        "cert_expiring_by_type": cert_expiring_by_type,
    }


# ── Tool 5b: List overdue crew rotations ────────────────────────────────────────

def list_overdue_crew_rotations(rig: str | None = None, limit: int = 10) -> dict:
    """
    List crew currently on board whose planned rotation date has passed.
    Includes every open On Board record, even very old ones that look like
    abandoned data entries — surfaced as-is rather than silently filtered.
    Always current snapshot — no year filter.
    """
    limit = min(max(1, limit), 50)
    conditions = [
        "sd.Serv_Subtype_Id = 7",
        "sd.Serv_Subtype_To IS NULL",
        "sd.Appx_End_Dt IS NOT NULL",
        "sd.Appx_End_Dt < CURDATE()",
    ]
    params: list = []

    if rig:
        rig_id = _rig_id(rig)
        if rig_id is None:
            return {"tool": "list_overdue_crew_rotations", "error": f"Rig '{rig}' not found."}
        conditions.append("sd.Rig_Id = %s")
        params.append(rig_id)

    where = " AND ".join(conditions)
    params.append(limit)

    rows = _query(f"""
        SELECT
            CONCAT(e.Fs_Emp_Fname, ' ', COALESCE(e.Fs_Emp_Lname, '')) AS employee_name,
            r.Rig_Name,
            mr.rank_name                                       AS rank_name,
            DATE(sd.Serv_Subtype_From)                         AS joined_date,
            DATE(sd.Appx_End_Dt)                               AS planned_end_date,
            DATEDIFF(CURDATE(), sd.Appx_End_Dt)                AS days_overdue,
            DATEDIFF(CURDATE(), sd.Serv_Subtype_From)           AS days_on_board
        FROM eos_Service_Details sd
        JOIN eos_Mst_Rig r            ON sd.Rig_Id = r.Rig_Id AND r.Rig_Type_Id IN (1,2)
        LEFT JOIN eos_Mst_Fs_Employee e ON sd.Fs_Emp_Id = e.Fs_Emp_Id
        LEFT JOIN Mst_Rank mr          ON sd.Rank_Id = mr.rank_id
        WHERE {where}
        ORDER BY days_overdue DESC
        LIMIT %s
    """, tuple(params))

    most_overdue = rows[0] if rows else None
    return {
        "tool": "list_overdue_crew_rotations",
        "filters": {"rig": rig, "limit": limit},
        "note": "Current snapshot — not year-filtered. Includes records that may be stale data entries never closed out, not necessarily real crew still on the rig. Sorted most overdue first.",
        "count_returned": len(rows),
        "most_overdue": most_overdue,
        "crew": rows,
    }


# ── Tool 5c: List expiring crew certificates ────────────────────────────────────

def list_expiring_crew_certificates(status: str | None = None, limit: int = 10) -> dict:
    """
    List individual crew certificates that are expired or expiring soon.
    status: 'expired' | 'due_30' | 'due_90' | None (expired + due within 90 days)
    Fleet-wide — eos_Fs_Certificates has no rig linkage, so no rig filter.
    """
    limit = min(max(1, limit), 50)
    conditions = ["fc.Fs_Cert_Active = 'Y'", "fc.Fs_Cert_Valid_Till IS NOT NULL"]
    params: list = []

    if status == "expired":
        conditions.append("fc.Fs_Cert_Valid_Till < CURDATE()")
    elif status == "due_30":
        conditions.append("fc.Fs_Cert_Valid_Till >= CURDATE()")
        conditions.append("fc.Fs_Cert_Valid_Till < CURDATE() + INTERVAL 30 DAY")
    elif status == "due_90":
        conditions.append("fc.Fs_Cert_Valid_Till >= CURDATE()")
        conditions.append("fc.Fs_Cert_Valid_Till < CURDATE() + INTERVAL 90 DAY")
    else:
        conditions.append("fc.Fs_Cert_Valid_Till < CURDATE() + INTERVAL 90 DAY")

    where = " AND ".join(conditions)
    params.append(limit)

    # Expired: most-recently-expired first (most actionable). Due soon: soonest first.
    # Expired (or the mixed expired+due_90 default): most-recently-expired /
    # soonest-due first — most actionable. due_30/due_90 alone: soonest first.
    order_by = "fc.Fs_Cert_Valid_Till ASC" if status in ("due_30", "due_90") else "fc.Fs_Cert_Valid_Till DESC"

    rows = _query(f"""
        SELECT
            CONCAT(e.Fs_Emp_Fname, ' ', COALESCE(e.Fs_Emp_Lname, '')) AS employee_name,
            mc.cert_name                                       AS cert_name,
            DATE(fc.Fs_Cert_Dt)                                AS issued_date,
            DATE(fc.Fs_Cert_Valid_Till)                        AS expiry_date,
            DATEDIFF(CURDATE(), fc.Fs_Cert_Valid_Till)         AS days_since_expiry
        FROM eos_Fs_Certificates fc
        LEFT JOIN eos_Mst_Fs_Employee e ON fc.Fs_Emp_Id = e.Fs_Emp_Id
        LEFT JOIN Mst_Cert mc           ON fc.Cert_Id = mc.cert_id
        WHERE {where}
        ORDER BY {order_by}
        LIMIT %s
    """, tuple(params))

    return {
        "tool": "list_expiring_crew_certificates",
        "filters": {"status": status, "limit": limit},
        "note": "Fleet-wide — individual crew certs only, no rig linkage available in source data.",
        "count_returned": len(rows),
        "certificates": rows,
    }


"""
Paginated, searchable, sortable listing queries for the dedicated Listings
pages (separate from tools.py, which serves the chatbot and caps results at
50 rows for narration). Every query here is fixed/parameterised — no LLM
ever touches SQL. Search terms are always passed as bound parameters.
"""

from .tools import _query, _rig_id

PAGE_SIZE_CHOICES = (25, 50, 75, 100)
DEFAULT_PAGE_SIZE = 50


def _clean_page(page: int | None) -> int:
    return max(1, page or 1)


def _clean_page_size(page_size: int | None) -> int:
    if page_size in PAGE_SIZE_CHOICES:
        return page_size
    return DEFAULT_PAGE_SIZE


def _paginate(total: int, page: int, page_size: int) -> dict:
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = min(page, total_pages)
    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
    }


# ── Incident Listing ─────────────────────────────────────────────────────────

INCIDENT_SORT_COLUMNS = {
    "date":            "i.Incident_Date",
    "severity":        "i.Incident_Severity",
    "npt_hours":       "i.NPT_Hrs_Loss",
    "financial_loss":  "i.Financial_Loss_Amt",
}


def get_incident_listing(
    page: int | None = None,
    page_size: int | None = None,
    rig: str | None = None,
    year: int | None = None,
    severity: str | None = None,       # 'H' | 'M' | 'L'
    person_injured: str | None = None, # 'Y' | 'N'
    incident_type: str | None = None,  # Incident_Type_Id (str digits)
    search: str | None = None,
    sort: str | None = None,
    sort_dir: str | None = None,
) -> dict:
    page      = _clean_page(page)
    page_size = _clean_page_size(page_size)

    conditions = ["COALESCE(i.Marked_As_Deleted, '') != 'Y'"]
    params: list = []

    if rig:
        rig_id = _rig_id(rig)
        if rig_id is None:
            return {"error": f"Rig '{rig}' not found."}
        conditions.append("i.Rig_Id = %s")
        params.append(rig_id)
    if year:
        conditions.append("YEAR(i.Incident_Date) = %s")
        params.append(year)
    if severity in ("H", "M", "L"):
        conditions.append("i.Incident_Severity = %s")
        params.append(severity)
    if person_injured in ("Y", "N"):
        conditions.append("COALESCE(i.Person_Injured, 'N') = %s")
        params.append(person_injured)
    if incident_type:
        conditions.append("i.Incident_Type_Id = %s")
        params.append(incident_type)
    if search:
        conditions.append("""(
            i.Incident_Descr   LIKE %s OR
            i.Corrective_Action LIKE %s OR
            i.Preventive_Action LIKE %s OR
            i.Comments          LIKE %s OR
            i.Emp_Name           LIKE %s
        )""")
        like = f"%{search}%"
        params.extend([like, like, like, like, like])

    where = " AND ".join(conditions)

    total_rows = _query(f"""
        SELECT COUNT(*) AS cnt
        FROM eos_Incident_Details i
        WHERE {where}
    """, tuple(params))
    total = total_rows[0]["cnt"] if total_rows else 0

    sort_col = INCIDENT_SORT_COLUMNS.get(sort, "i.Incident_Date")
    sort_dir = "ASC" if sort_dir == "asc" else "DESC"
    offset   = (page - 1) * page_size

    rows = _query(f"""
        SELECT
            i.Incident_Id                AS id,
            i.Incident_No,
            DATE(i.Incident_Date)        AS date,
            COALESCE(r.Rig_Name, 'Unknown') AS rig,
            i.Incident_Severity          AS severity,
            it.Incident_Type             AS incident_type,
            i.Person_Injured             AS person_injured,
            COALESCE(i.NPT_Hrs_Loss, 0)  AS npt_hours,
            COALESCE(i.Manhours_Loss, 0) AS manhours_loss,
            i.Financial_Loss_Amt         AS financial_loss,
            LEFT(i.Incident_Descr, 140)  AS summary,
            i.Incident_Descr             AS description,
            ic.Incident_Cause_Desc       AS immediate_cause,
            i.Immediate_Cause_Descr      AS immediate_cause_detail,
            i.Corrective_Action          AS corrective_action,
            i.Preventive_Action          AS preventive_action,
            i.Comments                   AS comments,
            i.Emp_Name                   AS employee_name,
            i.Rank_Name                  AS rank_name,
            w.Work_Location               AS work_location,
            i.Drilling_Superintendent    AS drilling_superintendent,
            i.Safety_Officer             AS safety_officer,
            i.Reported_By                AS reported_by
        FROM eos_Incident_Details i
        LEFT JOIN eos_Mst_Rig r          ON i.Rig_Id = r.Rig_Id AND r.Rig_Type_Id IN (1,2)
        LEFT JOIN Mstx_Incident_Type it  ON i.Incident_Type_Id = it.Incident_Type_Id
        LEFT JOIN Mstx_Incident_Cause ic ON i.Immediate_Incident_Cause_Id = ic.Incident_Cause_Id
        LEFT JOIN Mstx_Work_Location w   ON i.Work_Location_Id = w.Work_Location_Id
        WHERE {where}
        ORDER BY {sort_col} {sort_dir}
        LIMIT %s OFFSET %s
    """, tuple(params) + (page_size, offset))

    severity_map = {"H": "High", "M": "Medium", "L": "Low"}
    for r in rows:
        r["severity"] = severity_map.get(r["severity"], r["severity"] or "Unknown")
        r["person_injured"] = r["person_injured"] == "Y"

    return {
        "rows": rows,
        **_paginate(total, page, page_size),
    }


# ── Hazard Card Listing ──────────────────────────────────────────────────────

HAZARD_SORT_COLUMNS = {
    "date":   "h.Event_Dt",
    "status": "h.Haz_ID_Card_Status",
    # Sort by the actual computed age, not Event_Dt — sorting Event_Dt DESC
    # gives the newest (smallest-age) cards first, the opposite of "age desc".
    "age":    "DATEDIFF(COALESCE(h.Close_Out_Dt, CURDATE()), h.Event_Dt)",
}


def get_hazard_card_listing(
    page: int | None = None,
    page_size: int | None = None,
    rig: str | None = None,
    year: int | None = None,
    hazard_type: str | None = None,   # Haz_Type_Id (str digits)
    status: str | None = None,        # 'open' | 'closed'
    tfs: str | None = None,           # 'Y' | 'N'
    work_location: str | None = None, # Work_Location_Id (str digits)
    search: str | None = None,
    sort: str | None = None,
    sort_dir: str | None = None,
) -> dict:
    page      = _clean_page(page)
    page_size = _clean_page_size(page_size)

    conditions = ["COALESCE(h.Marked_As_Deleted, '') != 'Y'"]
    params: list = []

    if rig:
        rig_id = _rig_id(rig)
        if rig_id is None:
            return {"error": f"Rig '{rig}' not found."}
        conditions.append("h.Rig_Id = %s")
        params.append(rig_id)
    if year:
        conditions.append("YEAR(h.Event_Dt) = %s")
        params.append(year)
    if hazard_type:
        conditions.append("h.Haz_Type_Id = %s")
        params.append(hazard_type)
    if status == "open":
        conditions.append("h.Haz_ID_Card_Status != 'C'")
    elif status == "closed":
        conditions.append("h.Haz_ID_Card_Status = 'C'")
    if tfs in ("Y", "N"):
        conditions.append("h.Timeout_For_Safety = %s")
        params.append(tfs)
    if work_location:
        conditions.append("h.Work_Location_Id = %s")
        params.append(work_location)
    if search:
        conditions.append("""(
            h.Hazard_Desc       LIKE %s OR
            h.Action_Taken      LIKE %s OR
            h.Reported_By_Name  LIKE %s
        )""")
        like = f"%{search}%"
        params.extend([like, like, like])

    where = " AND ".join(conditions)

    total_rows = _query(f"""
        SELECT COUNT(*) AS cnt
        FROM eos_Hazard_ID_Card h
        WHERE {where}
    """, tuple(params))
    total = total_rows[0]["cnt"] if total_rows else 0

    sort_col = HAZARD_SORT_COLUMNS.get(sort, "h.Event_Dt")
    sort_dir = "ASC" if sort_dir == "asc" else "DESC"
    offset   = (page - 1) * page_size

    rows = _query(f"""
        SELECT
            h.Haz_Card_Id                       AS id,
            h.Haz_ID_Card_No                     AS card_no,
            DATE(h.Event_Dt)                     AS date,
            COALESCE(r.Rig_Name, 'Unknown')      AS rig,
            t.Haz_Type_Name                      AS hazard_type,
            w.Work_Location                       AS work_location,
            h.Haz_ID_Card_Status                 AS status,
            h.Timeout_For_Safety                 AS tfs,
            LEFT(h.Hazard_Desc, 140)             AS summary,
            h.Hazard_Desc                        AS description,
            h.Action_Taken                       AS action_taken,
            d.Dept_Name                          AS resp_dept,
            mr.rank_name                         AS resp_rank,
            h.Reported_By_Name                   AS reported_by,
            DATE(h.Close_Out_Dt)                 AS close_out_date,
            DATEDIFF(COALESCE(h.Close_Out_Dt, CURDATE()), h.Event_Dt) AS age_days
        FROM eos_Hazard_ID_Card h
        LEFT JOIN eos_Mst_Rig r         ON h.Rig_Id = r.Rig_Id AND r.Rig_Type_Id IN (1,2)
        LEFT JOIN eos_Mst_Hazard_Type t ON h.Haz_Type_Id = t.Haz_Type_Id
        LEFT JOIN Mstx_Work_Location w  ON h.Work_Location_Id = w.Work_Location_Id
        LEFT JOIN Mst_Department d      ON h.Resp_Dept_Id = d.Dept_Id
        LEFT JOIN Mst_Rank mr           ON h.Resp_Rank_Id = mr.rank_id
        WHERE {where}
        ORDER BY {sort_col} {sort_dir}
        LIMIT %s OFFSET %s
    """, tuple(params) + (page_size, offset))

    for r in rows:
        r["status_label"] = "Closed" if r["status"] == "C" else "Open"
        r["tfs"] = r["tfs"] == "Y"

    return {
        "rows": rows,
        **_paginate(total, page, page_size),
    }


# ── Employee (Crew) Listing ──────────────────────────────────────────────────
# Source: eos_Mst_Fs_Employee — field-service crew master (the people who
# actually work on rigs). Distinct from Mst_Employee, which is the
# company-wide HR master spanning every business unit (not rig-specific).

EMPLOYEE_SORT_COLUMNS = {
    "name":   "e.Fs_Emp_Lname",
    "doj":    "e.Fs_Emp_Doj",
    "rank":   "mr.rank_order",
}


def get_employee_listing(
    page: int | None = None,
    page_size: int | None = None,
    rig: str | None = None,
    rank: str | None = None,       # Rank_Id (str digits)
    category: str | None = None,   # Fs_Category_Id (str digits)
    emp_type: str | None = None,   # Emp_Type_Id (str digits)
    status: str | None = None,     # 'active' | 'inactive'
    gender: str | None = None,     # 'M' | 'F'
    search: str | None = None,
    sort: str | None = None,
    sort_dir: str | None = None,
) -> dict:
    page      = _clean_page(page)
    page_size = _clean_page_size(page_size)

    conditions = ["1=1"]
    params: list = []

    if rig:
        rig_id = _rig_id(rig)
        if rig_id is None:
            return {"error": f"Rig '{rig}' not found."}
        conditions.append("e.Rig_Id = %s")
        params.append(rig_id)
    if rank:
        conditions.append("e.Rank_Id = %s")
        params.append(rank)
    if category:
        conditions.append("e.Fs_Category_Id = %s")
        params.append(category)
    if emp_type:
        conditions.append("e.Emp_Type_Id = %s")
        params.append(emp_type)
    if status == "active":
        conditions.append("e.Fs_Emp_Active = 'Y'")
    elif status == "inactive":
        conditions.append("COALESCE(e.Fs_Emp_Active, '') != 'Y'")
    if gender in ("M", "F"):
        conditions.append("e.Gender = %s")
        params.append(gender)
    if search:
        conditions.append("""(
            e.Fs_Emp_Fname        LIKE %s OR
            e.Fs_Emp_Lname        LIKE %s OR
            e.Fs_Emp_Email_Pers   LIKE %s OR
            e.Fs_Emp_Email_Official LIKE %s OR
            e.Fs_Emp_Mobile_No    LIKE %s OR
            CAST(e.Fs_Emp_Staff_Id AS CHAR) LIKE %s
        )""")
        like = f"%{search}%"
        params.extend([like, like, like, like, like, like])

    where = " AND ".join(conditions)

    total_rows = _query(f"""
        SELECT COUNT(*) AS cnt
        FROM eos_Mst_Fs_Employee e
        WHERE {where}
    """, tuple(params))
    total = total_rows[0]["cnt"] if total_rows else 0

    sort_col = EMPLOYEE_SORT_COLUMNS.get(sort, "e.Fs_Emp_Lname")
    sort_dir = "DESC" if sort_dir == "desc" else "ASC"
    offset   = (page - 1) * page_size

    rows = _query(f"""
        SELECT
            e.Fs_Emp_Id                          AS id,
            CONCAT_WS(' ', e.Fs_Emp_Fname, NULLIF(e.Fs_Emp_Mname, ''), e.Fs_Emp_Lname) AS name,
            mr.rank_name                         AS rank_name,
            COALESCE(r.Rig_Name, 'Unassigned')   AS rig,
            fc.fs_category_name                  AS category,
            et.emp_type_name                     AS emp_type,
            e.Fs_Emp_Active                       AS active,
            e.Gender                             AS gender,
            DATE(e.Fs_Emp_Dob)                   AS dob,
            DATE(e.Fs_Emp_Doj)                   AS doj,
            DATE(e.Hire_Dt)                      AS hire_date,
            DATE(e.Fs_Emp_Dol)                   AS dol,
            DATE(e.Off_Hire_Dt)                  AS off_hire_date,
            e.Fs_Emp_Mobile_No                   AS mobile,
            e.Fs_Emp_Email_Pers                  AS email_personal,
            e.Fs_Emp_Email_Official               AS email_official,
            e.Blood_Group                        AS blood_group,
            e.Key_Personnel                      AS key_personnel,
            e.Fs_Emp_Staff_Id                    AS staff_id,
            e.Permanent_Addr                     AS permanent_address,
            e.PP_No                              AS passport_no,
            DATE(e.PP_Valid_Till)                AS passport_valid_till,
            e.CDC_No                             AS cdc_no,
            DATE(e.CDC_Valid_Till)                AS cdc_valid_till
        FROM eos_Mst_Fs_Employee e
        LEFT JOIN eos_Mst_Rig r    ON e.Rig_Id = r.Rig_Id AND r.Rig_Type_Id IN (1,2)
        LEFT JOIN Mst_Rank mr      ON e.Rank_Id = mr.rank_id
        LEFT JOIN Mst_Fs_Category fc ON e.Fs_Category_Id = fc.fs_category_id
        LEFT JOIN Mst_Emp_Type et ON e.Emp_Type_Id = et.emp_type_id
        WHERE {where}
        ORDER BY {sort_col} {sort_dir}
        LIMIT %s OFFSET %s
    """, tuple(params) + (page_size, offset))

    for r in rows:
        r["active"] = r["active"] == "Y"
        r["key_personnel"] = r["key_personnel"] == "Y"

    return {
        "rows": rows,
        **_paginate(total, page, page_size),
    }

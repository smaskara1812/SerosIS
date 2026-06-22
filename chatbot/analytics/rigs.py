from .tools import _query


def get_rig_snapshot(rig_id: int, year: int) -> dict:
    """Quick cross-domain KPIs for the overview tab — one query per domain."""
    inc = _query("""
        SELECT COUNT(*) AS total,
               SUM(CASE WHEN it.Incident_Abrv = 'LTI' THEN 1 ELSE 0 END) AS lti
        FROM eos_Incident_Details i
        JOIN Mstx_Incident_Type it ON it.Incident_Type_Id = i.Incident_Type_Id
        WHERE i.Rig_Id = %s AND YEAR(i.Incident_Date) = %s
          AND COALESCE(i.Marked_As_Deleted,'') != 'Y'
    """, (rig_id, year))

    haz = _query("""
        SELECT COUNT(*) AS total,
               SUM(CASE WHEN Haz_ID_Card_Status = 'O' THEN 1 ELSE 0 END) AS open
        FROM eos_Hazard_ID_Card
        WHERE Rig_Id = %s AND YEAR(Event_Dt) = %s AND Marked_As_Deleted != 'Y'
    """, (rig_id, year))

    crew = _query("""
        SELECT COUNT(DISTINCT sd.Fs_Emp_Id) AS on_board
        FROM eos_Service_Details sd
        WHERE sd.Rig_Id = %s AND sd.Serv_Subtype_To IS NULL AND sd.Serv_Subtype_Id = 7
    """, (rig_id,))

    inv = _query("""
        SELECT SUM(i.Invoice_Amt) AS total_spend,
               COUNT(*) AS invoice_count
        FROM eos_Invoice_Hdr i
        JOIN eos_Mst_Cost_Centre cc ON cc.Cost_Centre_Id = i.Cost_Centre_Id
        WHERE cc.Rig_Id = %s AND YEAR(i.Invoice_Dt) = %s
          AND COALESCE(i.Marked_As_Deleted,'') != 'Y'
    """, (rig_id, year))

    ops = _query("""
        SELECT
            ROUND(SUM(Operating_Hrs), 1) AS operating_hrs,
            ROUND(
                100.0 * SUM(Operating_Hrs) / NULLIF(
                    SUM(Operating_Hrs + COALESCE(Standby_Hrs,0)
                        + COALESCE(Repair_Service_Hrs,0) + COALESCE(Repair_Rate_Hrs,0)
                        + COALESCE(Zero_Rate_Hrs,0) + COALESCE(Rig_Move_Hrs,0))
                , 0), 1
            ) AS utilisation_pct
        FROM eos_Drilling_Dtl
        WHERE Rig_Id = %s AND YEAR(Drilling_Dtl_Dt) = %s
    """, (rig_id, year))

    mr = _query("""
        SELECT COUNT(*) AS total,
               SUM(CASE WHEN g.Grn_Hdr_Id IS NOT NULL THEN 1 ELSE 0 END) AS fulfilled
        FROM eos_Material_Requisition_Hdr m
        LEFT JOIN eos_GRN_Hdr g ON g.MR_Hdr_Id = m.MR_Hdr_Id
        WHERE m.Rig_id = %s AND YEAR(m.MR_Dt) = %s
    """, (rig_id, year))

    return {
        "incidents": dict(inc[0]) if inc else {},
        "hazards":   dict(haz[0]) if haz else {},
        "crew":      dict(crew[0]) if crew else {},
        "invoices":  dict(inv[0]) if inv else {},
        "ops":       dict(ops[0]) if ops else {},
        "mr":        dict(mr[0]) if mr else {},
    }


def get_rig_crew_groups(rig_id: int) -> dict:
    """Active crew group assignments with employee names."""
    groups = _query("""
        SELECT DISTINCT cg.Crew_Grp_Id, cg.Crew_Grp_Name, cg.Hitch
        FROM eos_Mst_Crew_Grp cg
        WHERE cg.Rig_Id = %s
        ORDER BY cg.Crew_Grp_Name
    """, (rig_id,))

    members = _query("""
        SELECT
            cg.Crew_Grp_Name AS group_name,
            CONCAT(
                COALESCE(e.Fs_Emp_Fname, ''), ' ',
                COALESCE(e.Fs_Emp_Mname, ''), ' ',
                e.Fs_Emp_Lname
            ) AS emp_name,
            sd.Serv_Subtype_Id,
            sst.Serv_Subtype_Name AS status,
            cd.Crew_Grp_From      AS assigned_from
        FROM eos_Crew_Grp_Dtl cd
        JOIN eos_Mst_Crew_Grp   cg  ON cg.Crew_Grp_Id  = cd.Crew_Grp_Id
        JOIN eos_Mst_Fs_Employee e   ON e.Fs_Emp_Id     = cd.Fs_Emp_Id
        LEFT JOIN eos_Service_Details sd
               ON sd.Fs_Emp_Id = cd.Fs_Emp_Id
              AND sd.Rig_Id    = cd.Rig_Id
              AND sd.Serv_Subtype_To IS NULL
        LEFT JOIN Mst_Serv_Subtype sst ON sst.Serv_Subtype_Id = sd.Serv_Subtype_Id
        WHERE cd.Rig_Id = %s AND cd.Crew_Grp_To IS NULL
        ORDER BY cg.Crew_Grp_Name, e.Fs_Emp_Lname
    """, (rig_id,))

    return {
        "groups":  [dict(g) for g in groups],
        "members": [dict(m) for m in members],
    }


def get_rigs_list() -> list:
    return _query("""
        SELECT
            r.Rig_Id,
            r.Rig_Name,
            r.Rig_Short_Name,
            r.Rig_Active,
            r.Rig_Built_Dt,
            rt.Rig_Type_Name,
            rs.Rig_Subtype_Name
        FROM eos_Mst_Rig r
        JOIN Mst_Rig_Type    rt ON rt.Rig_Type_Id    = r.Rig_Type_Id
        JOIN Mst_Rig_Subtype rs ON rs.Rig_Subtype_Id = r.Rig_Subtype_Id
        WHERE r.Rig_Type_Id IN (1, 2)
        ORDER BY r.Rig_Active DESC, rt.Rig_Type_Name, r.Rig_Name
    """)


def get_rig_overview(rig_id: int) -> dict:
    rows = _query("""
        SELECT
            r.Rig_Id,
            r.Rig_Name,
            r.Rig_Short_Name,
            r.Rig_Active,
            r.Rig_Built_Dt,
            r.Rig_Tel_No,
            r.Rig_Email_Id,
            rt.Rig_Type_Name,
            rs.Rig_Subtype_Name,
            s.Camp_Office_Addr,
            s.Site_From,
            l.Location_Name
        FROM eos_Mst_Rig r
        JOIN Mst_Rig_Type    rt ON rt.Rig_Type_Id    = r.Rig_Type_Id
        JOIN Mst_Rig_Subtype rs ON rs.Rig_Subtype_Id = r.Rig_Subtype_Id
        LEFT JOIN eos_Rig_Site_Mapping s ON s.Rig_Id = r.Rig_Id AND s.Site_To IS NULL
        LEFT JOIN Mst_Location         l ON l.Location_Id = s.Location_Id
        WHERE r.Rig_Id = %s
    """, (rig_id,))
    return dict(rows[0]) if rows else {}


def get_rig_people(rig_id: int, year: int) -> dict:
    onboard = _query("""
        SELECT
            sst.Serv_Subtype_Name,
            COUNT(DISTINCT sd.Fs_Emp_Id) AS crew_count
        FROM eos_Service_Details sd
        JOIN Mst_Serv_Subtype sst ON sst.Serv_Subtype_Id = sd.Serv_Subtype_Id
        WHERE sd.Rig_Id = %s AND sd.Serv_Subtype_To IS NULL
        GROUP BY sst.Serv_Subtype_Name
        ORDER BY crew_count DESC
    """, (rig_id,))

    pob_trend = _query("""
        SELECT
            DATE_FORMAT(POB_Month, '%%Y-%%m') AS month,
            POB_Manhours_EOSIL                AS seros_hrs,
            POB_Manhours_TP                   AS tp_hrs,
            (POB_Manhours_EOSIL + POB_Manhours_TP) AS total_hrs
        FROM eos_Monthly_POB_Summary
        WHERE Rig_Id = %s AND YEAR(POB_Month) = %s
        ORDER BY POB_Month
    """, (rig_id, year))

    # Average daily POB from drilling log (month buckets)
    daily_pob = _query("""
        SELECT
            DATE_FORMAT(Drilling_Dtl_Dt, '%%Y-%%m') AS month,
            ROUND(AVG(
                POB_Operator + POB_Essar
                + COALESCE(POB_Essar_Serv, 0)
                + COALESCE(POB_Others, 0)
            ), 0) AS avg_pob
        FROM eos_Drilling_Dtl
        WHERE Rig_Id = %s AND YEAR(Drilling_Dtl_Dt) = %s
        GROUP BY DATE_FORMAT(Drilling_Dtl_Dt, '%%Y-%%m'),
                 YEAR(Drilling_Dtl_Dt), MONTH(Drilling_Dtl_Dt)
        ORDER BY YEAR(Drilling_Dtl_Dt), MONTH(Drilling_Dtl_Dt)
    """, (rig_id, year))

    rotations = _query("""
        SELECT
            cg.Crew_Grp_Name  AS crew_group,
            rcg.Crew_Grp_Name AS relieving_group,
            rot.Crew_Grp_On_Dt  AS on_date,
            rot.Crew_Grp_Off_Dt AS off_date
        FROM eos_Crew_Grp_Rotation rot
        JOIN eos_Mst_Crew_Grp cg  ON cg.Crew_Grp_Id  = rot.Crew_Grp_Id
        JOIN eos_Mst_Crew_Grp rcg ON rcg.Crew_Grp_Id = rot.Relieving_Crew_Grp_Id
        WHERE cg.Rig_Id = %s AND rot.Crew_Grp_On_Dt >= CURDATE()
        ORDER BY rot.Crew_Grp_On_Dt
        LIMIT 6
    """, (rig_id,))

    return {
        "onboard":    [dict(r) for r in onboard],
        "pob_trend":  [dict(r) for r in pob_trend],
        "daily_pob":  [dict(r) for r in daily_pob],
        "rotations":  [dict(r) for r in rotations],
    }


def get_rig_safety(rig_id: int, year: int) -> dict:
    inc_kpi = _query("""
        SELECT
            COUNT(*)                                             AS total,
            SUM(CASE WHEN it.Incident_Abrv = 'LTI' THEN 1 ELSE 0 END) AS lti,
            SUM(CASE WHEN it.Incident_Abrv = 'FAC' THEN 1 ELSE 0 END) AS fac,
            SUM(CASE WHEN it.Incident_Abrv = 'MTC' THEN 1 ELSE 0 END) AS mtc,
            SUM(COALESCE(i.NPT_Hrs_Loss, 0))       AS total_npt_hrs,
            SUM(COALESCE(i.Financial_Loss_BC_Amt, 0)) AS financial_loss
        FROM eos_Incident_Details i
        JOIN Mstx_Incident_Type it ON it.Incident_Type_Id = i.Incident_Type_Id
        WHERE i.Rig_Id = %s
          AND YEAR(i.Incident_Date) = %s
          AND COALESCE(i.Marked_As_Deleted, '') != 'Y'
    """, (rig_id, year))

    inc_trend = _query("""
        SELECT
            DATE_FORMAT(i.Incident_Date, '%%Y-%%m') AS month,
            COUNT(*) AS total,
            SUM(CASE WHEN i.Incident_Severity IN ('H','1') THEN 1 ELSE 0 END) AS high_sev,
            SUM(COALESCE(i.NPT_Hrs_Loss, 0)) AS npt_hrs
        FROM eos_Incident_Details i
        WHERE i.Rig_Id = %s
          AND YEAR(i.Incident_Date) = %s
          AND COALESCE(i.Marked_As_Deleted, '') != 'Y'
        GROUP BY DATE_FORMAT(i.Incident_Date, '%%Y-%%m'),
                 YEAR(i.Incident_Date), MONTH(i.Incident_Date)
        ORDER BY YEAR(i.Incident_Date), MONTH(i.Incident_Date)
    """, (rig_id, year))

    inc_by_type = _query("""
        SELECT
            it.Incident_Type AS type,
            it.Incident_Abrv AS abrv,
            COUNT(*) AS count
        FROM eos_Incident_Details i
        JOIN Mstx_Incident_Type it ON it.Incident_Type_Id = i.Incident_Type_Id
        WHERE i.Rig_Id = %s
          AND YEAR(i.Incident_Date) = %s
          AND COALESCE(i.Marked_As_Deleted, '') != 'Y'
        GROUP BY it.Incident_Type, it.Incident_Abrv
        ORDER BY count DESC
    """, (rig_id, year))

    inc_recent = _query("""
        SELECT
            DATE(i.Incident_Date) AS date,
            it.Incident_Type      AS type,
            it.Incident_Abrv      AS abrv,
            i.Incident_Descr      AS description,
            i.Incident_Severity   AS severity,
            COALESCE(i.NPT_Hrs_Loss, 0) AS npt_hrs
        FROM eos_Incident_Details i
        JOIN Mstx_Incident_Type it ON it.Incident_Type_Id = i.Incident_Type_Id
        WHERE i.Rig_Id = %s
          AND YEAR(i.Incident_Date) = %s
          AND COALESCE(i.Marked_As_Deleted, '') != 'Y'
        ORDER BY i.Incident_Date DESC
        LIMIT 10
    """, (rig_id, year))

    haz_kpi = _query("""
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN Haz_ID_Card_Status = 'C' THEN 1 ELSE 0 END) AS closed,
            SUM(CASE WHEN Haz_ID_Card_Status = 'O' THEN 1 ELSE 0 END) AS open,
            ROUND(100.0 * SUM(CASE WHEN Haz_ID_Card_Status = 'C' THEN 1 ELSE 0 END)
                  / NULLIF(COUNT(*), 0), 1)                           AS close_rate_pct,
            ROUND(AVG(CASE WHEN Close_Out_Dt IS NOT NULL
                           THEN DATEDIFF(Close_Out_Dt, Event_Dt) END), 1) AS avg_closeout_days
        FROM eos_Hazard_ID_Card
        WHERE Rig_Id = %s
          AND YEAR(Event_Dt) = %s
          AND Marked_As_Deleted != 'Y'
    """, (rig_id, year))

    haz_trend = _query("""
        SELECT
            DATE_FORMAT(Event_Dt, '%%Y-%%m') AS month,
            COUNT(*) AS raised,
            SUM(CASE WHEN Haz_ID_Card_Status = 'C' THEN 1 ELSE 0 END) AS closed
        FROM eos_Hazard_ID_Card
        WHERE Rig_Id = %s
          AND YEAR(Event_Dt) = %s
          AND Marked_As_Deleted != 'Y'
        GROUP BY DATE_FORMAT(Event_Dt, '%%Y-%%m'),
                 YEAR(Event_Dt), MONTH(Event_Dt)
        ORDER BY YEAR(Event_Dt), MONTH(Event_Dt)
    """, (rig_id, year))

    haz_by_type = _query("""
        SELECT
            ht.Haz_Type_Name AS type,
            COUNT(*) AS count,
            SUM(CASE WHEN h.Haz_ID_Card_Status = 'C' THEN 1 ELSE 0 END) AS closed,
            ROUND(AVG(CASE WHEN h.Close_Out_Dt IS NOT NULL
                           THEN DATEDIFF(h.Close_Out_Dt, h.Event_Dt) END), 1) AS avg_close_days
        FROM eos_Hazard_ID_Card h
        JOIN eos_Mst_Hazard_Type ht ON ht.Haz_Type_Id = h.Haz_Type_Id
        WHERE h.Rig_Id = %s
          AND YEAR(h.Event_Dt) = %s
          AND h.Marked_As_Deleted != 'Y'
        GROUP BY ht.Haz_Type_Name
        ORDER BY count DESC
    """, (rig_id, year))

    haz_recent = _query("""
        SELECT
            DATE(h.Event_Dt)       AS date,
            h.Hazard_Desc          AS description,
            ht.Haz_Type_Name       AS hazard_type,
            h.Haz_ID_Card_Status   AS status,
            DATE(h.Close_Out_Dt)   AS closed_date,
            DATEDIFF(COALESCE(h.Close_Out_Dt, CURDATE()), h.Event_Dt) AS days_open
        FROM eos_Hazard_ID_Card h
        JOIN eos_Mst_Hazard_Type ht ON ht.Haz_Type_Id = h.Haz_Type_Id
        WHERE h.Rig_Id = %s
          AND YEAR(h.Event_Dt) = %s
          AND h.Marked_As_Deleted != 'Y'
        ORDER BY h.Event_Dt DESC
        LIMIT 10
    """, (rig_id, year))

    drills = _query("""
        SELECT
            DATE(d.Drill_Dt)         AS date,
            d.Drill_Location         AS location,
            hd1.HSE_Drill_Name       AS drill_type,
            d.No_Of_Participants     AS participants,
            d.Initial_Response_Time  AS response_time
        FROM eos_HSE_Drill_Record_Hdr d
        JOIN eos_Mst_HSE_Drill hd1 ON hd1.HSE_Drill_Id = d.HSE_Drill_Id_1
        WHERE d.Rig_Id = %s AND YEAR(d.Drill_Dt) = %s
        ORDER BY d.Drill_Dt DESC
    """, (rig_id, year))

    return {
        "incidents": {
            "kpi":     dict(inc_kpi[0]) if inc_kpi else {},
            "trend":   [dict(r) for r in inc_trend],
            "by_type": [dict(r) for r in inc_by_type],
            "recent":  [dict(r) for r in inc_recent],
        },
        "hazards": {
            "kpi":     dict(haz_kpi[0]) if haz_kpi else {},
            "trend":   [dict(r) for r in haz_trend],
            "by_type": [dict(r) for r in haz_by_type],
            "recent":  [dict(r) for r in haz_recent],
        },
        "drills": [dict(r) for r in drills],
    }


def get_rig_finance(rig_id: int, year: int) -> dict:
    inv_kpi = _query("""
        SELECT
            COUNT(*)                              AS invoice_count,
            SUM(i.Invoice_Amt)                    AS total_spend,
            SUM(CASE WHEN i.L3_Approval_Status = 'A' THEN i.Invoice_Amt END) AS approved_spend,
            SUM(CASE WHEN i.L3_Approval_Status = 'R' THEN i.Invoice_Amt END) AS rejected_spend,
            SUM(CASE WHEN i.L3_Approval_Status NOT IN ('A','R')
                          OR i.L3_Approval_Status IS NULL
                     THEN i.Invoice_Amt END)      AS pending_spend,
            ROUND(AVG(CASE WHEN i.L3_Approval_Dt IS NOT NULL
                           THEN DATEDIFF(i.L3_Approval_Dt, i.Invoice_Dt) END), 1) AS avg_approval_days
        FROM eos_Invoice_Hdr i
        JOIN eos_Mst_Cost_Centre cc ON cc.Cost_Centre_Id = i.Cost_Centre_Id
        WHERE cc.Rig_Id = %s AND YEAR(i.Invoice_Dt) = %s
          AND COALESCE(i.Marked_As_Deleted, '') != 'Y'
    """, (rig_id, year))

    inv_trend = _query("""
        SELECT
            DATE_FORMAT(i.Invoice_Dt, '%%Y-%%m') AS month,
            COUNT(*)           AS count,
            SUM(i.Invoice_Amt) AS spend,
            SUM(CASE WHEN i.L3_Approval_Status = 'A' THEN i.Invoice_Amt END) AS approved
        FROM eos_Invoice_Hdr i
        JOIN eos_Mst_Cost_Centre cc ON cc.Cost_Centre_Id = i.Cost_Centre_Id
        WHERE cc.Rig_Id = %s AND YEAR(i.Invoice_Dt) = %s
          AND COALESCE(i.Marked_As_Deleted, '') != 'Y'
        GROUP BY DATE_FORMAT(i.Invoice_Dt, '%%Y-%%m'),
                 YEAR(i.Invoice_Dt), MONTH(i.Invoice_Dt)
        ORDER BY YEAR(i.Invoice_Dt), MONTH(i.Invoice_Dt)
    """, (rig_id, year))

    top_vendors = _query("""
        SELECT
            v.Vendor_Name,
            COUNT(*)           AS invoice_count,
            SUM(i.Invoice_Amt) AS total_spend
        FROM eos_Invoice_Hdr i
        JOIN eos_Mst_Cost_Centre cc ON cc.Cost_Centre_Id = i.Cost_Centre_Id
        JOIN Mstx_Vendor          v ON v.Vendor_Id       = i.Vendor_Id
        WHERE cc.Rig_Id = %s AND YEAR(i.Invoice_Dt) = %s
          AND COALESCE(i.Marked_As_Deleted, '') != 'Y'
        GROUP BY v.Vendor_Name
        ORDER BY total_spend DESC
        LIMIT 8
    """, (rig_id, year))

    # Per-level average processing days + pending count
    funnel = _query("""
        SELECT
            SUM(CASE WHEN i.L1_Approval_Status NOT IN ('A','R') OR i.L1_Approval_Status IS NULL THEN 1 ELSE 0 END) AS pending_l1,
            SUM(CASE WHEN i.L1_Approval_Status = 'A'
                      AND (i.L2_Approval_Status NOT IN ('A','R') OR i.L2_Approval_Status IS NULL) THEN 1 ELSE 0 END) AS pending_l2,
            SUM(CASE WHEN i.L2_Approval_Status = 'A'
                      AND (i.L3_Approval_Status NOT IN ('A','R') OR i.L3_Approval_Status IS NULL) THEN 1 ELSE 0 END) AS pending_l3,
            SUM(CASE WHEN i.L3_Approval_Status = 'A' THEN 1 ELSE 0 END) AS fully_approved,
            ROUND(AVG(CASE WHEN i.L1_Approval_Dt IS NOT NULL
                           THEN DATEDIFF(i.L1_Approval_Dt, i.Invoice_Dt) END), 1) AS avg_l1_days,
            ROUND(AVG(CASE WHEN i.L2_Approval_Dt IS NOT NULL AND i.L1_Approval_Dt IS NOT NULL
                           THEN DATEDIFF(i.L2_Approval_Dt, i.L1_Approval_Dt) END), 1) AS avg_l2_days,
            ROUND(AVG(CASE WHEN i.L3_Approval_Dt IS NOT NULL AND i.L2_Approval_Dt IS NOT NULL
                           THEN DATEDIFF(i.L3_Approval_Dt, i.L2_Approval_Dt) END), 1) AS avg_l3_days
        FROM eos_Invoice_Hdr i
        JOIN eos_Mst_Cost_Centre cc ON cc.Cost_Centre_Id = i.Cost_Centre_Id
        WHERE cc.Rig_Id = %s AND YEAR(i.Invoice_Dt) = %s
          AND COALESCE(i.Marked_As_Deleted, '') != 'Y'
    """, (rig_id, year))

    mr_kpi = _query("""
        SELECT
            COUNT(*) AS total_mrs,
            SUM(CASE WHEN g.Grn_Hdr_Id IS NOT NULL THEN 1 ELSE 0 END) AS fulfilled,
            SUM(CASE WHEN g.Grn_Hdr_Id IS NULL     THEN 1 ELSE 0 END) AS pending,
            ROUND(AVG(CASE WHEN g.Receipt_Dt IS NOT NULL
                           THEN DATEDIFF(g.Receipt_Dt, m.MR_Dt) END), 1) AS avg_days
        FROM eos_Material_Requisition_Hdr m
        LEFT JOIN eos_GRN_Hdr g ON g.MR_Hdr_Id = m.MR_Hdr_Id
        WHERE m.Rig_id = %s AND YEAR(m.MR_Dt) = %s
    """, (rig_id, year))

    mr_by_priority = _query("""
        SELECT
            m.Priority,
            COUNT(*) AS total,
            SUM(CASE WHEN g.Grn_Hdr_Id IS NOT NULL THEN 1 ELSE 0 END) AS fulfilled,
            ROUND(100.0 * SUM(CASE WHEN g.Grn_Hdr_Id IS NOT NULL THEN 1 ELSE 0 END)
                  / NULLIF(COUNT(*), 0), 0)                             AS fill_pct,
            ROUND(AVG(CASE WHEN g.Receipt_Dt IS NOT NULL
                           THEN DATEDIFF(g.Receipt_Dt, m.MR_Dt) END), 1) AS avg_days
        FROM eos_Material_Requisition_Hdr m
        LEFT JOIN eos_GRN_Hdr g ON g.MR_Hdr_Id = m.MR_Hdr_Id
        WHERE m.Rig_id = %s AND YEAR(m.MR_Dt) = %s
        GROUP BY m.Priority
        ORDER BY avg_days DESC
    """, (rig_id, year))

    mr_trend = _query("""
        SELECT
            DATE_FORMAT(m.MR_Dt, '%%Y-%%m') AS month,
            COUNT(*) AS raised,
            SUM(CASE WHEN g.Grn_Hdr_Id IS NOT NULL THEN 1 ELSE 0 END) AS fulfilled
        FROM eos_Material_Requisition_Hdr m
        LEFT JOIN eos_GRN_Hdr g ON g.MR_Hdr_Id = m.MR_Hdr_Id
        WHERE m.Rig_id = %s AND YEAR(m.MR_Dt) = %s
        GROUP BY DATE_FORMAT(m.MR_Dt, '%%Y-%%m'),
                 YEAR(m.MR_Dt), MONTH(m.MR_Dt)
        ORDER BY YEAR(m.MR_Dt), MONTH(m.MR_Dt)
    """, (rig_id, year))

    return {
        "invoices": {
            "kpi":         dict(inv_kpi[0]) if inv_kpi else {},
            "trend":       [dict(r) for r in inv_trend],
            "top_vendors": [dict(r) for r in top_vendors],
            "funnel":      dict(funnel[0]) if funnel else {},
        },
        "mrs": {
            "kpi":         dict(mr_kpi[0]) if mr_kpi else {},
            "by_priority": [dict(r) for r in mr_by_priority],
            "trend":       [dict(r) for r in mr_trend],
        },
    }


def get_rig_operations(rig_id: int, year: int) -> dict:
    drill_kpi = _query("""
        SELECT
            ROUND(SUM(Operating_Hrs), 1)                         AS operating_hrs,
            ROUND(SUM(COALESCE(Standby_Hrs, 0)), 1)             AS standby_hrs,
            ROUND(SUM(COALESCE(Repair_Service_Hrs, 0)), 1)      AS repair_hrs,
            ROUND(SUM(COALESCE(Repair_Rate_Hrs, 0)), 1)         AS repair_rate_hrs,
            ROUND(SUM(COALESCE(Zero_Rate_Hrs, 0)), 1)           AS zero_rate_hrs,
            ROUND(SUM(COALESCE(Rig_Move_Hrs, 0)), 1)            AS rig_move_hrs,
            SUM(Consumption_Diesel)                              AS total_diesel,
            COUNT(DISTINCT Drilling_Dtl_Dt)                     AS operating_days,
            ROUND(
                100.0 * SUM(Operating_Hrs) / NULLIF(
                    SUM(Operating_Hrs
                        + COALESCE(Standby_Hrs,0)
                        + COALESCE(Repair_Service_Hrs,0)
                        + COALESCE(Repair_Rate_Hrs,0)
                        + COALESCE(Zero_Rate_Hrs,0)
                        + COALESCE(Rig_Move_Hrs,0))
                , 0), 1
            ) AS utilisation_pct
        FROM eos_Drilling_Dtl
        WHERE Rig_Id = %s AND YEAR(Drilling_Dtl_Dt) = %s
    """, (rig_id, year))

    drill_trend = _query("""
        SELECT
            DATE_FORMAT(Drilling_Dtl_Dt, '%%Y-%%m') AS month,
            ROUND(SUM(Operating_Hrs), 1)             AS operating_hrs,
            ROUND(SUM(COALESCE(Standby_Hrs, 0)), 1) AS standby_hrs,
            ROUND(SUM(COALESCE(Repair_Service_Hrs, 0)
                    + COALESCE(Repair_Rate_Hrs, 0)), 1) AS repair_hrs,
            ROUND(SUM(COALESCE(Zero_Rate_Hrs, 0)
                    + COALESCE(Rig_Move_Hrs, 0)), 1) AS other_hrs,
            ROUND(
                100.0 * SUM(Operating_Hrs) / NULLIF(
                    SUM(Operating_Hrs
                        + COALESCE(Standby_Hrs,0)
                        + COALESCE(Repair_Service_Hrs,0)
                        + COALESCE(Repair_Rate_Hrs,0)
                        + COALESCE(Zero_Rate_Hrs,0)
                        + COALESCE(Rig_Move_Hrs,0))
                , 0), 1
            ) AS utilisation_pct
        FROM eos_Drilling_Dtl
        WHERE Rig_Id = %s AND YEAR(Drilling_Dtl_Dt) = %s
        GROUP BY DATE_FORMAT(Drilling_Dtl_Dt, '%%Y-%%m'),
                 YEAR(Drilling_Dtl_Dt), MONTH(Drilling_Dtl_Dt)
        ORDER BY YEAR(Drilling_Dtl_Dt), MONTH(Drilling_Dtl_Dt)
    """, (rig_id, year))

    npt_kpi = _query("""
        SELECT
            ROUND(SUM(ops.Duration), 1) AS total_npt_hrs,
            COUNT(*)                    AS npt_events,
            ROUND(AVG(ops.Duration), 2) AS avg_event_hrs
        FROM eos_Drilling_Dtl_Ops ops
        JOIN eos_Drilling_Dtl dd ON dd.Drilling_Dtl_Id = ops.Drilling_Dtl_Id
        WHERE dd.Rig_Id = %s
          AND YEAR(ops.Time_From) = %s
          AND ops.Drilling_Ops_Id = 24
    """, (rig_id, year))

    # Total logged hours for NPT% denominator
    total_hrs_row = _query("""
        SELECT ROUND(SUM(ops.Duration), 1) AS total_hrs
        FROM eos_Drilling_Dtl_Ops ops
        JOIN eos_Drilling_Dtl dd ON dd.Drilling_Dtl_Id = ops.Drilling_Dtl_Id
        WHERE dd.Rig_Id = %s AND YEAR(ops.Time_From) = %s
    """, (rig_id, year))

    total_ops_hrs = float(total_hrs_row[0]["total_hrs"] or 0) if total_hrs_row else 0
    npt_hrs_val   = float(npt_kpi[0]["total_npt_hrs"] or 0) if npt_kpi else 0
    npt_pct       = round(npt_hrs_val / total_ops_hrs * 100, 2) if total_ops_hrs else None

    npt_reasons = _query("""
        SELECT
            COALESCE(NULLIF(TRIM(dd.Downtime_Reason), ''), 'Unspecified') AS reason,
            ROUND(SUM(ops.Duration), 1) AS npt_hrs,
            COUNT(*)                    AS events,
            ROUND(AVG(ops.Duration), 1) AS avg_hrs
        FROM eos_Drilling_Dtl_Ops ops
        JOIN eos_Drilling_Dtl dd ON dd.Drilling_Dtl_Id = ops.Drilling_Dtl_Id
        WHERE dd.Rig_Id = %s
          AND YEAR(ops.Time_From) = %s
          AND ops.Drilling_Ops_Id = 24
        GROUP BY COALESCE(NULLIF(TRIM(dd.Downtime_Reason), ''), 'Unspecified')
        ORDER BY npt_hrs DESC
        LIMIT 10
    """, (rig_id, year))

    npt_trend = _query("""
        SELECT
            DATE_FORMAT(ops.Time_From, '%%Y-%%m') AS month,
            ROUND(SUM(ops.Duration), 1) AS npt_hrs,
            COUNT(*) AS events
        FROM eos_Drilling_Dtl_Ops ops
        JOIN eos_Drilling_Dtl dd ON dd.Drilling_Dtl_Id = ops.Drilling_Dtl_Id
        WHERE dd.Rig_Id = %s
          AND YEAR(ops.Time_From) = %s
          AND ops.Drilling_Ops_Id = 24
        GROUP BY DATE_FORMAT(ops.Time_From, '%%Y-%%m'),
                 YEAR(ops.Time_From), MONTH(ops.Time_From)
        ORDER BY YEAR(ops.Time_From), MONTH(ops.Time_From)
    """, (rig_id, year))

    wells = _query("""
        SELECT
            dh.Location,
            dh.Latitude,
            dh.Longitude,
            dh.Total_Water_Depth,
            dh.Total_Depth,
            DATE(dh.First_Anchor_Down_Dt) AS anchor_date,
            dh.Tot_Operating_Hrs,
            dh.Tot_Standby_Hrs,
            dh.Tot_Repair_Service_Hrs,
            dh.Tot_Consumption_Diesel
        FROM eos_Drilling_Hdr dh
        WHERE dh.Rig_Id = %s
        ORDER BY dh.First_Anchor_Down_Dt DESC
        LIMIT 5
    """, (rig_id,))

    kpi = dict(npt_kpi[0]) if npt_kpi else {}
    kpi["npt_pct"] = npt_pct

    return {
        "drilling": {
            "kpi":   dict(drill_kpi[0]) if drill_kpi else {},
            "trend": [dict(r) for r in drill_trend],
        },
        "npt": {
            "kpi":     kpi,
            "reasons": [dict(r) for r in npt_reasons],
            "trend":   [dict(r) for r in npt_trend],
        },
        "wells": [dict(r) for r in wells],
    }

from .tools import _query
import statistics as _stats


def get_haz_hotspot_data() -> dict:
    """All data for the Hazard Hotspot dashboard panel."""

    # Fleet KPIs — all-time, no year filter
    kpi = _query("""
        SELECT
            COUNT(*)                                                          AS total,
            SUM(CASE WHEN Haz_ID_Card_Status = 'O' THEN 1 ELSE 0 END)       AS open,
            ROUND(100.0 * SUM(CASE WHEN Haz_ID_Card_Status = 'C' THEN 1 ELSE 0 END)
                  / NULLIF(COUNT(*), 0), 1)                                   AS close_rate,
            ROUND(AVG(CASE WHEN Close_Out_Dt IS NOT NULL
                           AND DATEDIFF(Close_Out_Dt, Event_Dt) >= 0
                           THEN DATEDIFF(Close_Out_Dt, Event_Dt) END), 1)    AS avg_close_days,
            MAX(CASE WHEN Haz_ID_Card_Status = 'O'
                     THEN DATEDIFF(CURDATE(), Event_Dt) END)                  AS max_open_days,
            SUM(CASE WHEN Haz_ID_Card_Status = 'O'
                      AND DATEDIFF(CURDATE(), Event_Dt) > 30
                     THEN 1 ELSE 0 END)                                       AS overdue_30
        FROM eos_Hazard_ID_Card
        WHERE Marked_As_Deleted != 'Y'
    """)
    fleet_kpi = dict(kpi[0]) if kpi else {}

    # Heatmap: rig × month, last 24 months
    heatmap = _query("""
        SELECT
            r.Rig_Short_Name                          AS rig,
            DATE_FORMAT(h.Event_Dt, '%%Y-%%m')        AS month,
            COUNT(*)                                   AS count
        FROM eos_Hazard_ID_Card h
        JOIN eos_Mst_Rig r ON r.Rig_Id = h.Rig_Id
        WHERE h.Marked_As_Deleted != 'Y'
          AND r.Rig_Type_Id IN (1, 2)
          AND h.Event_Dt >= DATE_SUB(CURDATE(), INTERVAL 24 MONTH)
        GROUP BY r.Rig_Short_Name,
                 DATE_FORMAT(h.Event_Dt, '%%Y-%%m'),
                 YEAR(h.Event_Dt), MONTH(h.Event_Dt)
        ORDER BY YEAR(h.Event_Dt), MONTH(h.Event_Dt), r.Rig_Short_Name
    """)

    # Category Pareto — all time, top 15
    type_rows = _query("""
        SELECT
            ht.Haz_Type_Name                              AS type,
            COUNT(*)                                       AS count,
            SUM(CASE WHEN h.Haz_ID_Card_Status = 'O' THEN 1 ELSE 0 END) AS open,
            ROUND(AVG(CASE WHEN h.Close_Out_Dt IS NOT NULL
                           THEN DATEDIFF(h.Close_Out_Dt, h.Event_Dt)
                      END), 1)                             AS avg_close_days
        FROM eos_Hazard_ID_Card h
        JOIN eos_Mst_Hazard_Type ht ON ht.Haz_Type_Id = h.Haz_Type_Id
        WHERE h.Marked_As_Deleted != 'Y'
        GROUP BY ht.Haz_Type_Name
        ORDER BY count DESC
        LIMIT 15
    """)
    pareto = [dict(r) for r in type_rows]
    total_p = sum(r['count'] for r in pareto) or 1
    cumul = 0
    for r in pareto:
        cumul += r['count']
        r['cumul_pct'] = round(cumul / total_p * 100, 1)

    # Close-out performance by rig.
    # Wrapped in a subquery so avg_close_days is a real column in the outer scope —
    # SQL Server does not resolve SELECT-clause aliases inside ORDER BY expressions
    # (only as bare top-level sort keys), so the NULL-sort trick must reference a
    # proper derived-table column rather than the inner alias.
    closeout = _query("""
        SELECT * FROM (
            SELECT
                r.Rig_Short_Name                                               AS rig,
                COUNT(*)                                                        AS total,
                SUM(CASE WHEN h.Haz_ID_Card_Status = 'O' THEN 1 ELSE 0 END)  AS open,
                ROUND(100.0 * SUM(CASE WHEN h.Haz_ID_Card_Status = 'C' THEN 1 ELSE 0 END)
                      / NULLIF(COUNT(*), 0), 1)                                 AS close_rate,
                ROUND(AVG(CASE WHEN h.Close_Out_Dt IS NOT NULL
                               AND DATEDIFF(h.Close_Out_Dt, h.Event_Dt) >= 0
                               THEN DATEDIFF(h.Close_Out_Dt, h.Event_Dt)
                          END), 1)                                              AS avg_close_days,
                SUM(CASE WHEN h.Close_Out_Dt IS NOT NULL
                          AND DATEDIFF(h.Close_Out_Dt, h.Event_Dt) < 0
                         THEN 1 ELSE 0 END)                                     AS bad_date_count,
                MAX(CASE WHEN h.Haz_ID_Card_Status = 'O'
                         THEN DATEDIFF(CURDATE(), h.Event_Dt) END)              AS max_open_age
            FROM eos_Hazard_ID_Card h
            JOIN eos_Mst_Rig r ON r.Rig_Id = h.Rig_Id
            WHERE h.Marked_As_Deleted != 'Y' AND r.Rig_Type_Id IN (1, 2)
            GROUP BY r.Rig_Short_Name
        ) sub
        ORDER BY (avg_close_days IS NULL), avg_close_days DESC
    """)

    # Open hazard age distribution (current snapshot)
    age_dist = _query("""
        SELECT
            CASE
                WHEN DATEDIFF(CURDATE(), Event_Dt) <=  7 THEN '0-7d'
                WHEN DATEDIFF(CURDATE(), Event_Dt) <= 14 THEN '8-14d'
                WHEN DATEDIFF(CURDATE(), Event_Dt) <= 30 THEN '15-30d'
                WHEN DATEDIFF(CURDATE(), Event_Dt) <= 60 THEN '31-60d'
                WHEN DATEDIFF(CURDATE(), Event_Dt) <= 90 THEN '61-90d'
                ELSE '90+d'
            END AS bucket,
            COUNT(*) AS count
        FROM eos_Hazard_ID_Card
        WHERE Haz_ID_Card_Status = 'O' AND Marked_As_Deleted != 'Y'
        GROUP BY bucket
        ORDER BY MIN(DATEDIFF(CURDATE(), Event_Dt))
    """)

    # Monthly hazards by rig — last 24 months (for stacked control chart)
    monthly_rig_rows = _query("""
        SELECT
            DATE_FORMAT(h.Event_Dt, '%%Y-%%m') AS month,
            r.Rig_Short_Name                   AS rig,
            COUNT(*)                            AS count
        FROM eos_Hazard_ID_Card h
        JOIN eos_Mst_Rig r ON r.Rig_Id = h.Rig_Id
        WHERE h.Marked_As_Deleted != 'Y'
          AND r.Rig_Type_Id IN (1, 2)
          AND h.Event_Dt >= DATE_SUB(CURDATE(), INTERVAL 24 MONTH)
        GROUP BY DATE_FORMAT(h.Event_Dt, '%%Y-%%m'),
                 YEAR(h.Event_Dt), MONTH(h.Event_Dt),
                 r.Rig_Short_Name
        ORDER BY YEAR(h.Event_Dt), MONTH(h.Event_Dt), r.Rig_Short_Name
    """)
    monthly_rig = [dict(r) for r in monthly_rig_rows]

    # Compute UCL/LCL from monthly fleet totals (sum across rigs per month)
    _month_totals: dict = {}
    for row in monthly_rig:
        _month_totals[row['month']] = _month_totals.get(row['month'], 0) + row['count']
    _totals_list = list(_month_totals.values())
    if len(_totals_list) > 1:
        _mean = _stats.mean(_totals_list)
        _std  = _stats.stdev(_totals_list)
        ucl   = round(_mean + 2 * _std, 1)
        lcl   = round(max(0.0, _mean - 2 * _std), 1)
        mean  = round(_mean, 1)
    elif _totals_list:
        mean = ucl = lcl = _totals_list[0]
    else:
        mean = ucl = lcl = 0

    # Current open hazard exposure by rig (actionable snapshot)
    exposure_rows = _query("""
        SELECT
            r.Rig_Short_Name                                                   AS rig,
            SUM(CASE WHEN h.Haz_ID_Card_Status = 'O' THEN 1 ELSE 0 END)      AS open,
            SUM(CASE WHEN h.Haz_ID_Card_Status = 'O'
                      AND DATEDIFF(CURDATE(), h.Event_Dt) > 30
                     THEN 1 ELSE 0 END)                                        AS overdue_30,
            MAX(CASE WHEN h.Haz_ID_Card_Status = 'O'
                     THEN DATEDIFF(CURDATE(), h.Event_Dt) END)                 AS oldest_open_days
        FROM eos_Hazard_ID_Card h
        JOIN eos_Mst_Rig r ON r.Rig_Id = h.Rig_Id
        WHERE h.Marked_As_Deleted != 'Y' AND r.Rig_Type_Id IN (1, 2)
        GROUP BY r.Rig_Short_Name
        ORDER BY open DESC
    """)

    # Crew tenure risk — hazards relative to how long crew had been on rig
    try:
        tenure_rows = _query("""
            SELECT
                CASE
                    WHEN DATEDIFF(h.Event_Dt, cd.Crew_Grp_From) <  0  THEN NULL
                    WHEN DATEDIFF(h.Event_Dt, cd.Crew_Grp_From) <= 14 THEN '0-14d'
                    WHEN DATEDIFF(h.Event_Dt, cd.Crew_Grp_From) <= 28 THEN '15-28d'
                    WHEN DATEDIFF(h.Event_Dt, cd.Crew_Grp_From) <= 56 THEN '29-56d'
                    ELSE '57+d'
                END                              AS tenure_bucket,
                COUNT(DISTINCT h.Haz_Id)         AS hazard_count,
                COUNT(DISTINCT cd.Fs_Emp_Id)     AS crew_count,
                ROUND(
                    COUNT(DISTINCT h.Haz_Id) * 1.0
                    / NULLIF(COUNT(DISTINCT cd.Fs_Emp_Id), 0), 3
                )                                AS rate_per_person
            FROM eos_Hazard_ID_Card h
            JOIN eos_Mst_Rig r ON r.Rig_Id = h.Rig_Id
            JOIN eos_Crew_Grp_Dtl cd ON cd.Rig_Id = h.Rig_Id
              AND cd.Crew_Grp_From <= h.Event_Dt
              AND (cd.Crew_Grp_To IS NULL OR cd.Crew_Grp_To > h.Event_Dt)
            WHERE h.Marked_As_Deleted != 'Y'
              AND r.Rig_Type_Id IN (1, 2)
              AND h.Event_Dt >= DATE_SUB(CURDATE(), INTERVAL 2 YEAR)
            GROUP BY tenure_bucket
            HAVING tenure_bucket IS NOT NULL
            ORDER BY MIN(DATEDIFF(h.Event_Dt, cd.Crew_Grp_From))
        """)
        crew_tenure = [dict(r) for r in tenure_rows]
    except Exception:
        crew_tenure = []

    return {
        "fleet_kpi":     fleet_kpi,
        "heatmap":       [dict(r) for r in heatmap],
        "pareto":        pareto,
        "closeout":      [dict(r) for r in closeout],
        "age_dist":      [dict(r) for r in age_dist],
        "monthly_by_rig": {"rows": monthly_rig, "mean": mean, "ucl": ucl, "lcl": lcl},
        "open_exposure":  [dict(r) for r in exposure_rows],
        "crew_tenure":    crew_tenure,
    }

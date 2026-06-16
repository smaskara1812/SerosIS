# Analytics Tools

Pre-built query functions for the Seros operational database (`Seros_Data`).
No LLM generates SQL — every query is a fixed, parameterised Python function.

---

## Architecture

```
User question
    ↓
router.py  — keyword/pattern matching (no LLM)
    ↓
tools.py   — parameterised SQL query → dict result
    ↓
LLM        — narrates the result using ONLY the returned data (strict, no hallucination)
```

**Note on speed:** DB queries complete in ~0.05s. Response latency comes entirely from the LLM narration step.

---

## Tools

### 1a. `count_rigs()`
Returns active/inactive rig counts only — no listing.

| Filter | Type | Description |
|--------|------|-------------|
| *(none)* | — | Always returns total / active / inactive counts |

**Returns:** `total`, `active`, `inactive`

**Example triggers:**
- "how many rigs do we have"
- "count of rigs" / "total rigs"

---

### 1b. `list_rigs(status)`
Lists rigs with id, name, short name, and active flag.

| Filter | Type | Options | Default |
|--------|------|---------|---------|
| `status` | `str` | `'all'` / `'active'` / `'inactive'` | `'all'` |

**Returns:** total shown, active count, inactive count, list of rigs

**Example triggers:**
- "list all rigs" / "which rigs are available"
- "list active rigs" / "show inactive rigs"

---

### 2. `get_headcount(rig, dept)`
Employee and crew headcount. Source: `eos_Service_Details` (`Serv_Subtype_Id = 7` 'On Board', `Serv_Subtype_To IS NULL`) joined to `eos_Mst_Rig` (`Rig_Type_Id IN (1,2)`).

**"On board" means physically on the rig right now** — matches the Workforce dashboard's "Crew Currently On Board" definition exactly. This used to count any open service record (On Board + Off Board + On Leave + Standby Wages, etc.) and didn't filter out Office/Repair Yard/Well Service entries, which inflated the figure (462 vs. the correct 248) and didn't match what "crew posted today" should mean.

| Filter | Type | Description |
|--------|------|-------------|
| `rig` | `str \| None` | Crew currently on board that rig |
| `dept` | `str \| None` | Active employees in that department |
| *(none)* | — | Total active employees + crew on board, broken down by rig |

**Returns:** counts, crew breakdown by rig (when no filter)

**Example triggers:**
- "how many employees are there"
- "headcount on DR01" / "crew on Axom Rhino"
- "staff in HR department"

---

### 3a. `get_incident_summary(rig, year)`
Aggregate incident counts and severity breakdown.

| Filter | Type | Description |
|--------|------|-------------|
| `rig` | `str \| None` | Filter by rig name or short name |
| `year` | `int \| None` | Filter by year (supports "this year", "last year") |
| *(none)* | — | All incidents across all rigs and years |

**Returns:** total incidents, severity H/M/L counts, total NPT hours, injury count, by-rig breakdown, year trend (last 6)

**Example triggers:**
- "incident summary for SR03"
- "how many accidents this year"
- "injuries on EE01"

---

### 3b. `list_incidents(rig, year, limit)`
Returns individual incident records (most recent first).

| Filter | Type | Description | Default |
|--------|------|-------------|---------|
| `rig` | `str \| None` | Filter by rig name | — |
| `year` | `int \| None` | Filter by year | — |
| `limit` | `int` | Number of records to return (max 50) | `5` |

**Returns:** list of incidents with date, rig, severity, injury flag, NPT hours, description

**Example triggers:**
- "show 5 recent incidents on Axom Rhino in 2026"
- "list last 10 accidents on EE01"

---

### 4a. `get_hazard_card_trend(rig, year)`
Aggregate hazard card counts, open/closed breakdown, year trend.

| Filter | Type | Description |
|--------|------|-------------|
| `rig` | `str \| None` | Filter by rig name |
| `year` | `int \| None` | Filter by year |
| *(none)* | — | All hazard cards |

**Returns:** total cards, open count, closed count, timeout-for-safety count, by-rig top 10, year trend (last 6)

**Example triggers:**
- "unsafe acts on Axom Rhino in 2025"
- "hazard card trend for DR01"
- "how many safety cards were submitted this year"

---

### 4b. `list_hazard_cards(rig, year, status, limit)`
Returns individual hazard card records (most recent first).

| Filter | Type | Options | Default |
|--------|------|---------|---------|
| `rig` | `str \| None` | Rig name | — |
| `year` | `int \| None` | Year | — |
| `status` | `str \| None` | `'open'` / `'closed'` / `None` (all) | `None` |
| `limit` | `int` | Records to return (max 50) | `10` |

**Returns:** list of hazard cards with card no, date, rig, status, timeout flag, hazard description, action taken

**Example triggers:**
- "show open hazard cards on EE01"
- "list recent hazard cards for DR01 in 2025"
- "show closed hazard cards on Axom Rhino"

---

### 4c. `list_overdue_hazard_cards(rig, limit)`
Open hazard cards sorted oldest first — identifies the longest-outstanding safety observations. **No year filter** — always a current snapshot.

| Filter | Type | Description | Default |
|--------|------|-------------|---------|
| `rig` | `str \| None` | Filter by rig name | — |
| `limit` | `int` | Records to return (max 50) | `10` |

**Returns:** `oldest_card` (the single oldest), `cards` list — each with card no, event date, age in days, rig, work location, hazard type, TFS flag, hazard description, action taken

**Example triggers:**
- "which is the oldest open hazard card"
- "show overdue hazard cards on DR01"
- "list outstanding cards on Axom Rhino"
- "which cards have been open the longest"

---

### 4d. `list_corrective_actions(rig, year, status, limit)`
Corrective actions from incident investigations (`eos_Incident_Actions`), sorted with overdue first.

| Filter | Type | Options | Default |
|--------|------|---------|---------|
| `rig` | `str \| None` | Rig name | — |
| `year` | `int \| None` | Year of the parent incident | — |
| `status` | `str \| None` | `'open'` / `'closed'` / `'overdue'` / `None` | `None` |
| `limit` | `int` | Records to return (max 50) | `10` |

**Returns:** list of actions with: incident date, rig, action recommended, action taken, responsible party, target date, completion date, status, days overdue

**Example triggers:**
- "show overdue corrective actions"
- "what corrective actions are pending on EE01"
- "list open actions from 2025 incidents"
- "what action was recommended after incidents on DR01"
- "who is responsible for outstanding actions"

---

### 4e. `get_hse_dashboard(rig, year)`
Comprehensive HSE overview — the same data that powers the HSE section of the analytics dashboard.
Sources: `eos_Hazard_ID_Card`, `eos_Incident_Actions`, `eos_Incident_Details`, `eos_Mst_Hazard_Type`, `Mstx_Work_Location`, `Mst_Department`.

| Filter | Type | Description |
|--------|------|-------------|
| `rig` | `str \| None` | Filter by rig name |
| `year` | `int \| None` | Filter by year (card ageing is always current snapshot) |
| *(none)* | — | All rigs, all years |

**Returns:**
- `summary` — `total_cards`, `open_cards`, `closed_cards`, `card_close_rate`, `tfs_count`, `overdue_cards`, `total_actions`, `closed_actions`, `overdue_actions`, `on_time_actions`, `closure_rate_pct`, `max_card_age_days`
- `submission_monthly` — monthly card counts with `open`, `closed`, `tfs` (timeout-for-safety) breakdown
- `by_type` — cards split by hazard type (Positive Recognition / Unsafe Act / Unsafe Condition) with class and count
- `by_work_location` — top 8 work locations by submission count
- `by_dept` — top 8 responsible departments with open/closed split
- `card_ageing` — open card age buckets: `0-7d`, `8-30d`, `31-90d`, `>90d`
- `inc_monthly` — monthly incident counts (for incident-to-hazard ratio overlay)
- `haz_summary` — raw KPI values (same as summary, aliased key)
- `action_closure` — action closure KPIs per year
- `closure_by_rig` — per-rig breakdown of closed / open / overdue actions

**Hazard types:**
- **Positive Recognition** — safe behaviour observed and recognised
- **Unsafe Act** — observed behaviour that could cause harm
- **Unsafe Condition** — physical condition that could cause harm

**Example triggers:**
- "hse overview for DR01 in 2025"
- "what is the card closure rate this year"
- "show corrective action closure rate"
- "overdue hazard cards"
- "card submission rate by type"
- "incident to hazard ratio"
- "how many positive recognitions were submitted"

---

### 5. `get_material_cost(rig, year)`
Material expenditure from `eos_OPC_Material_Cost`.

| Filter | Type | Description |
|--------|------|-------------|
| `rig` | `str \| None` | Filter by rig (via cost centre join) |
| `year` | `int \| None` | Filter by expense year |
| *(none)* | — | All material costs |

**Returns:** total items, total cost, average unit price, by-rig breakdown (top 10), year trend (last 6)

**Example triggers:**
- "material cost for EE02 last year"
- "spare parts expenditure this year"
- "how much was spent on materials in 2024"

---

### 6. `get_drilling_hours(rig, year)`
Total drilling operation hours from `eos_Drilling_Dtl_Ops`.
Counts all operation types (not just drill-actual) — use `get_drilling_performance` for ROP analysis.

| Filter | Type | Description |
|--------|------|-------------|
| `rig` | `str \| None` | Filter by rig name |
| `year` | `int \| None` | Filter by year |
| *(none)* | — | All drilling operations |

**Returns:** total operations, total hours, average operation duration, by-rig breakdown, year trend (last 6)

**Example triggers:**
- "total drilling time on EE01 this year"
- "drilling hours for Axom Rhino in 2025"

---

### 7. `get_drilling_performance(rig, year)`
Rate of Penetration (ROP) and drilling efficiency analysis from `eos_Drilling_Dtl_Ops`.

**Formula:** `ROP (m/hr) = SUM(Depth_To − Depth_From) / SUM(Duration)`  
Only counts `Drilling_Ops_Id = 2` (Drill Actual) rows where `Depth_To > Depth_From` (forward progress only — backreaming/pullback excluded).

All ROP values are **weighted averages** (not mean of per-operation speeds).

| Filter | Type | Description |
|--------|------|-------------|
| `rig` | `str \| None` | Filter by rig name |
| `year` | `int \| None` | Filter by year |
| *(none)* | — | All rigs, all years |

**Returns:**
- `summary` — overall ROP, total metres, total drill hours, operation count
- `by_section` — ROP and metres per hole section (surface, intermediate, production, etc.)
- `ops_breakdown` — all operation types with hours and % of total time (shows how much is drilling vs trips vs cementing etc.)
- `flat_time` — operations with zero depth progress (hours consumed without making new hole), grouped by op type
- `flat_time_total_hrs` — total flat time hours
- `flat_time_rig_detail` — flat time broken down by operation + rig (for drill-down)
- `locations_by_rig` — metres, ROP, and dates per location for each rig (dashboard drill-down data)
- `rop_by_rig` — per-rig ROP comparison for the selected year (always all rigs)
- `yoy` — year-over-year ROP trend (last 6 years, rig-filtered but no year filter)

**Two metrics explained:**
- **Rig Utilisation %** (from `get_rig_utilisation`) — is the rig working vs idle/broken? (daily log level)
- **Drill Actual % of ops** (from this tool) — of all operation-hours, how much is the bit actually cutting new rock? These are complementary, not contradictory.

**Example triggers:**
- "rate of penetration for DR01 in 2026"
- "ROP for Axom Rhino this year"
- "metres drilled per hour on EE01"
- "drilling performance for 2025"
- "which hole section has the best ROP"
- "flat time analysis for DR01"
- "how much time is spent on non-drilling operations"

---

### 8. `get_rig_utilisation(rig, year, month)`
Rig utilisation breakdown from `eos_Drilling_Dtl` daily logs.

**Formula:** `utilisation_pct = Operating_Hrs / (Operating + Standby + Repair + Zero_Rate + Rig_Move) × 100`

| Filter | Type | Description |
|--------|------|-------------|
| `rig` | `str \| None` | Filter by rig name or short name |
| `year` | `int \| None` | Filter by year |
| `month` | `int \| None` | Filter by month (1–12) |

**Returns:** summary stats, monthly breakdown (up to 2000 rows), best/worst months  
**Special:** `"display": "dashboard"` → frontend renders a colour-coded table panel below the LLM narration

**Colour coding:**
- ≥ 80% utilisation → green
- 60–79% → amber
- < 60% → red

**Example triggers:**
- "rig utilisation for DR01 in 2025"
- "show utilisation of Axom Rhino this year"
- "operating hours and uptime for EE01"
- "zero rate hours for SR03"
- "standby hours breakdown for 2026"

---

### 9. `get_rig_locations(rig, year)`
Locations (wells/drill sites) where Seros rigs have drilled.
Source: `eos_Drilling_Hdr` (one row per well assignment) joined with actual drilling ops for metres.

**Year filter logic:** includes wells that were active at any point during the year —  
`First_Anchor_Down_Dt <= end-of-year AND (completion_dt IS NULL OR YEAR(completion_dt) >= year)`  
This captures both newly spudded wells and carry-over wells still drilling from the previous year.

**Metres drilled** counts only `Drilling_Ops_Id = 2` (Drill Actual, forward progress only) — consistent with `get_drilling_performance`.

| Filter | Type | Description |
|--------|------|-------------|
| `rig` | `str \| None` | Filter by rig name |
| `year` | `int \| None` | Wells active during this year |
| *(none)* | — | All locations across all rigs |

**Returns:**
- `summary` — total locations, ongoing count, completed count
- `locations` — per-well list with: rig, location name, latitude, longitude, spud date, completion date, status (Ongoing/Completed), metres drilled, drill hours, ROP

**Example triggers:**
- "where did DR01 drill in 2026"
- "which locations is Axom Rhino drilling"
- "drilling locations for EE01 this year"
- "which well is SR03 currently on"
- "where has DR01 been drilling"
- "coordinates of EE01 drill site"
- "active wells this year"
- "ongoing drilling locations"

---

### 10. `get_npt_analysis(rig, year)`
Non-Productive Time analysis from `eos_Drilling_Dtl_Ops` (operations with `Drilling_Ops_Id = 24`).

**Formula:** `NPT% = SUM(NPT operation Duration) / SUM(all operation Duration) × 100`

Downtime reasons come from the `eos_Drilling_Dtl.Downtime_Reason` field (joined on the daily log record that contains the NPT operation).

| Filter | Type | Description |
|--------|------|-------------|
| `rig` | `str \| None` | Filter by rig name or short name |
| `year` | `int \| None` | Filter by year |
| *(none)* | — | All NPT across all rigs and years |

**Returns:**
- `summary` — `total_npt_hrs`, `npt_events`, `avg_event_hrs`, `total_logged_hrs`, `npt_pct`
- `monthly` — monthly trend: `month` (YYYY-MM), `npt_hrs`, `events`
- `npt_by_rig` — per-rig comparison (always all rigs, year-filtered): `rig`, `npt_hrs`, `events`, `avg_hrs`
- `top_reasons` — top 15 downtime reasons by hours: `reason`, `npt_hrs`, `events`
- `incident_npt` — NPT hours sourced from incident records (`NPT_Hrs_Loss`): `incident_npt_hrs`, `incidents_with_npt`
- `yoy` — year-over-year trend (last 6 years, rig-filtered): `yr`, `npt_hrs`, `events`
- `monthly_rig_detail` — (rig × month) rows for dashboard drill-down on NPT by Rig chart: `rig`, `month`, `npt_hrs`, `events`
- `reason_rig_detail` — (reason × rig) rows for Top Causes drill-down layer 1: `reason`, `rig`, `npt_hrs`, `events`
- `reason_rig_monthly` — (reason × rig × month) rows for Top Causes drill-down layer 2: `reason`, `rig`, `month`, `npt_hrs`, `events`

**Note:** Dashboard displays NPT time in **days** (÷24). The tool returns raw hours; conversion is done in the frontend. `avg_event_hrs` stays in hours since values are sub-day.

**Three NPT sources explained:**
- **Source A** (`Drilling_Ops_Id = 24`) — operation-level NPT from the daily drilling log. Primary metric.
- **Source B** (`Downtime_Reason` on daily log) — descriptive label for grouping and root-cause analysis.
- **Source C** (`NPT_Hrs_Loss` from incidents) — NPT attributed to safety incidents. Separate figure, not double-counted.

**Example triggers:**
- "NPT analysis for DR01"
- "non-productive time breakdown for Axom Rhino this year"
- "what caused NPT on EE01 in 2025"
- "what are the most frequent NPT reasons"
- "top NPT causes for SR01 in 2026"
- "downtime reasons analysis"
- "what is causing the most NPT"
- "NPT summary for 2025"
- "NPT hours trend year over year"
- "NPT by rig comparison 2026"
- "lost time analysis"

---

### 11a. `get_workforce_dashboard(rig, year)`
Comprehensive Workforce overview — powers the Workforce section of the analytics dashboard.
Sources: `eos_Service_Details`, `eos_Mst_Rig`, `Mst_Rank`, `eos_Fs_Certificates`, `Mst_Cert`.

**Table/column reference — what each metric is actually built from:**

| Metric | Table(s) | Key columns | Notes |
|--------|----------|-------------|-------|
| Departures (attrition) | `eos_Service_Details` | `Serv_Subtype_Id = 13` ('Final Settlement'), `Rig_Id`, `Rank_Id`, `Serv_Subtype_From` | The **only** subtype that means an employee left Seros for good. Routine rotation (`Serv_Subtype_Id` 7 'On Board' / 10 'Off Board') is excluded — those are not attrition. |
| Average tenure | `eos_Service_Details` | `MIN(Serv_Subtype_From)` where `Serv_Subtype_Id = 7` (career start) vs. the `Serv_Subtype_From` of the matching `Serv_Subtype_Id = 13` row (career end) | Closed careers only — crew still employed have no tenure value yet. |
| Rotation compliance | `eos_Service_Details` | `Serv_Subtype_Id = 7`, `Serv_Subtype_To` (actual sign-off), `Appx_End_Dt` (planned sign-off) | Compliance = signed off on/before `Appx_End_Dt`. Only rows with both dates populated count (96% coverage from 2013 onward; 2012 has only 68% coverage). |
| Current rotation status (live) | `eos_Service_Details` | `Serv_Subtype_Id = 7`, `Serv_Subtype_To IS NULL`, `Appx_End_Dt` | Includes every open On Board record as-is, including a handful from 2013/2020/2022 that were likely never closed out. Those show as extreme "days overdue" outliers — surfaced intentionally rather than filtered, so the data-quality gap stays visible to management. |
| Certificate expiry | `eos_Fs_Certificates`, `Mst_Cert` | `Fs_Cert_Active = 'Y'`, `Fs_Cert_Valid_Till`, `Cert_Id` → `cert_name` | `Fs_Cert_Active='Y'` means "this is the current cert record on file," **not** "not expired" — 354 of the active rows are already past their `Fs_Cert_Valid_Till` date with no renewal logged. Fleet-wide only; this table has no rig linkage. |

| Filter | Type | Description |
|--------|------|-------------|
| `rig` | `str \| None` | Filter by rig name (only `Rig_Type_Id` 1/2 — Offshore/Onshore — ever returned; rigs of type 3/4/5 — Repair Yard, Office, Well Service — are excluded everywhere) |
| `year` | `int \| None` | Filter by year (current rotation status and cert expiry are always live snapshots, not year-filtered) |

**Returns:**
- `summary` — `total_departures`, `avg_tenure_days`, `rotation_compliance_pct`, `crew_on_board`, `overdue_rotations`, `avg_days_overdue`, `certs_expired`, `certs_due_30`
- `departures_by_rig` — final settlements per rig
- `departures_by_rank` — top 10 ranks by final settlement count, fleet-wide
- `tenure_by_rig` — avg tenure in days per rig, with `sample_size`
- `rotation_compliance_by_rig` — `completed`, `on_time`, `compliance_pct`, `avg_overrun_days` per rig
- `current_rotation_by_rig` — `on_board`, `overdue`, `avg_days_on_board`, `avg_days_overdue`, `max_days_overdue` per rig
- `crew_roster_by_rig` — live crew roster per rig: `on_board`, `overdue`, `due_7d` (rotations planned within 7 days — almost always 0, see caveat below), `top_designations` (top 5 ranks with counts)
- `cert_expiry_buckets` — `expired`, `due_30`, `due_90`, `healthy` counts
- `cert_expiring_by_type` — top 10 certificate types by expired/due-soon count

**Example triggers:**
- "workforce overview"
- "crew attrition by rig"
- "average tenure for DR01"
- "rotation compliance this year"
- "certificate expiry status"
- "who is leaving"

---

### 11b. `list_overdue_crew_rotations(rig, limit)`
Named crew currently on board whose planned rotation date has passed. Sourced from `eos_Service_Details` joined to `eos_Mst_Fs_Employee` (name) and `Mst_Rank`. Same 180-day staleness filter as the dashboard's live snapshot — always current, no year filter.

| Filter | Type | Description | Default |
|--------|------|-------------|---------|
| `rig` | `str \| None` | Filter by rig name | — |
| `limit` | `int` | Records to return (max 50) | `10` |

**Returns:** `most_overdue` (the single most-overdue record), `crew` list — each with employee name, rig, rank, joined date, planned end date, days overdue, days on board

**Caveat:** "Overdue" here may include logging delays (crew who already rotated off but whose `Off Board` record hasn't been entered yet), not necessarily a real live staffing crisis — surface as a list to investigate, not a confirmed incident count.

**Example triggers:**
- "who is overdue for rotation"
- "show overdue crew on DR01"
- "which crew member hasn't rotated off"

---

### 11c. `list_expiring_crew_certificates(status, limit)`
Named individual crew certificates that are expired or expiring soon. Sourced from `eos_Fs_Certificates` joined to `eos_Mst_Fs_Employee` (name) and `Mst_Cert` (cert name). Fleet-wide — no rig filter available (source table has no `Rig_Id`).

| Filter | Type | Options | Default |
|--------|------|---------|---------|
| `status` | `str \| None` | `'expired'` / `'due_30'` / `'due_90'` / `None` (expired + due within 90 days) | `None` |
| `limit` | `int` | Records to return (max 50) | `10` |

**Returns:** list of certificates with employee name, cert name, issued date, expiry date, days since expiry

**Sort order:** `expired` sorts most-recently-expired first (most actionable); `due_30`/`due_90` sort soonest-expiring first.

**Example triggers:**
- "which certificates are expired"
- "list expiring certificates"
- "who needs certificate renewal"

---

## Router (`router.py`)

### Rig name matching
Case-insensitive, partial match supported:
- `"axom rhino"` / `"rhino"` → Axom Rhino
- `"dr01"`, `"ee01"`, `"sr03"`, `"sk02"`, `"wr01"` etc.
- `"wildcat"` / `"essar wildcat"` → Essar Wildcat

### Year extraction
| User says | Resolves to |
|-----------|-------------|
| `"2024"`, `"in 2023"` | That year |
| `"this year"`, `"current year"` | Current calendar year |
| `"last year"`, `"previous year"` | Previous calendar year |

### Limit extraction
Picks up numbers in phrases like "show 5", "last 10", "top 20", "recent 3".
Default is 5 for incident listing, 10 for hazard card listing.

### Follow-up context
The router accepts an optional `context` dict `{"tool": ..., "rig": ..., "year": ...}` extracted
from recent chat history. This lets follow-up questions like "show breakdown" or "give me more detail"
re-route to the same tool with the same filters without the user repeating the rig/year.

**Rig inheritance rules** (applied in `_extract_analytics_context` in `views.py`):
- If the current message names a specific rig → use that rig, ignore history
- If the current message contains "all rigs", "overall", "across all", etc. → clear rig, return all rigs
- If the current message is a short follow-up (≤10 words, no rig named) → inherit rig from recent history
- Otherwise (fresh question, >10 words, no rig named) → no rig filter, returns all rigs

### Routing priority (top to bottom)
1. Rig count / listing
2. Headcount
3. **NPT analysis** (must appear before incident blocks — both match "npt")
4. Incident listing → Incident summary
5. Overdue/oldest open hazard cards (specific records)
6. Corrective actions from incident investigations (specific records)
7. **HSE dashboard overview** (broad HSE KPIs, card rates, ageing, action closure)
8. Overdue crew rotations (specific records)
9. Expiring crew certificates (specific records)
10. **Workforce dashboard overview** (broad workforce KPIs — attrition, tenure, rotation, certs)
11. Hazard card listing → Hazard card summary (individual records / trend)
12. Material cost
13. Rig utilisation (+ follow-up context)
14. Drilling performance / ROP (+ follow-up context)
15. Rig locations (+ follow-up context)
16. Drilling hours
17. Fallback → RAG pipeline (service manuals)

### Fallback
If no analytics intent is matched → question goes to the **RAG pipeline** (service manuals).

---

## No-Hallucination Guarantee

The LLM narration prompt enforces:
1. Only use numbers and facts in the returned data
2. If a field is null/missing → say "not available", do not guess
3. No mention of SQL, databases, tools, or JSON
4. Answer only what the data says — nothing more

---

## Adding a New Tool

1. Add a function in `tools.py` with a fixed SQL query and a `"tool"` key in its return dict
2. Add intent keywords in `router.py` (check for conflicts with existing blocks — order matters)
3. Optionally update `_extract_analytics_context()` in `views.py` if follow-up routing is needed
4. Update this README with the new tool, its filters, return fields, and example triggers

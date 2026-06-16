# Seros Operational Database - Analytics Schema Overview

**Database:** Seros_Data (MySQL)
**Source:** Converted from MSSQL (518 tables, ~1.23M rows)
**Date:** 2026-06-12

---

## 0. Data Summary (from live exploration)

### Key Dimensions
- **29 rigs** (most active: Axom Rhino, EE01, DR01, SR-series, SK-series)
- **31 cost centres** (mapped 1:1 to rigs)
- **318 companies** in the group (active: ESTIL, EOL, EPIL, TMS, OGDSL, etc.)
- **222 departments** (Management, Finance, HR, IT, Procurement, Fleet Personnel, etc.)
- **123 ranks** (crew designations)
- **27,920 employees** in master (12,194 active, 15,726 inactive/exited)
- **3,273 floating staff** (offshore crew)

### Data Freshness (date ranges)
| Domain | Earliest | Latest |
|--------|----------|--------|
| Drilling operations | Oct 2020 | Apr 2026 |
| Hazard ID cards | ~2012 | Apr 2026 |
| Incidents | Apr 2012 | Apr 2026 |
| Invoices | ~2019 | Jun 2025 |
| Material requisitions | Apr 2019 | Apr 2026 |
| Employee joins | 1967 | Jul 2025 |
| FS contracts | Feb 2007 | Mar 2025 |
| FS exits | 2014 | 2026 (37 YTD) |
| GRNs | 2015 | 2025 |

### Key Numbers
| Metric | Value |
|--------|-------|
| Total material cost (all time) | ~INR 713M |
| Average monthly FS salary | INR 52,681 |
| Active crew postings (current) | 438 across 11 rigs |
| Top rig by crew | Axom Rhino (109), EE01 (100), DR01 (81) |
| Drilling hours 2025 YTD | ~24,600 hrs across 7 rigs |
| FS exits 2025 YTD | 473 |
| Hazard cards 2025 YTD | 503 |
| Material requisitions (81% Urgent priority) | 3,016 total |
| Invoices 2024 | ~INR 234M across 6 rigs |

### Primary Join Columns
| Column | Role | Used in |
|--------|------|---------|
| `Rig_Id` | Central hub | 65+ tables |
| `Cost_Centre_Id` | Rig ↔ Finance link | 18 tables |
| `Fs_Emp_Id` | Floating staff ID | 40+ tables |
| `Company_Id` / `COMPANY_ID` | Company dimension | 30 tables |
| `Dept_Id` / `DEPT_ID` | Department dimension | 15 tables |
| `Prj_Contract_Id` | Project contract ref | 10+ tables |
| `Vendor_Id` | Vendor dimension | Invoices, GRN, vendor master |
| `Rank_Id` | Crew rank | Contracts, service details, incidents |

---

## 1. Schema Domains & Key Tables

### 1.1 Workforce & HR

| Table | Rows | Description |
|-------|------|-------------|
| `Mst_Employee` | 27,920 | Employee master — names, grades, departments, locations |
| `eos_Service_Details` | 76,688 | Service history per employee (postings, durations, status changes) |
| `hr_Emp_Service_Details` | 28,650 | HR-side service records |
| `eos_Fs_Emp_Cur_Status` | 3,273 | Current status of floating staff (active, on leave, etc.) |
| `eos_Mst_Fs_Employee` | 3,273 | Floating staff master data |
| `eos_Fs_Official_Info` | 3,273 | Official info for floating staff (passport, visa, etc.) |
| `eos_Fs_Contract_Hdr` / `_Dtl` | 1,671 / 7,736 | Contract headers and line items for floating staff |
| `eos_Crew_Grp_Dtl` | 5,518 | Crew group assignments (who is in which crew) |
| `eos_Crew_Grp_Rotation` | 3,757 | Crew rotation schedules |
| `eos_Crew_Travel_Dtl` | 4,110 | Crew travel records (mobilisation/demobilisation) |
| `hr_Emp_Exit_Dtl` | 1,903 | Employee exit records (resignations, terminations) |
| `Wkg_Probable_Exit` | 22,655 | Probable/predicted exit tracking |
| `eos_Fs_Emp_Hiring` | 959 | Floating staff hiring pipeline |
| `eos_Fs_New_Appl_Dtl` | 3,560 | New applicant details |
| `eos_Fs_Certificates` | 662 | Staff certifications |
| `Mst_Rank` | 123 | Rank/designation master |
| `Mst_Working_Designation` | 238 | Working designation master |
| `Mst_Department` | 222 | Department master |

**Potential insights:**
- Headcount trends over time (joins vs exits)
- Attrition rate by department, rank, rig, or location
- Average tenure and service duration
- Crew rotation efficiency (gaps, overlaps)
- Certification expiry alerts and compliance rates
- Hiring pipeline funnel (applications to onboarding)
- Floating staff utilisation rate

---

### 1.2 Operations & Drilling

| Table | Rows | Description |
|-------|------|-------------|
| `eos_Drilling_Dtl_Ops` | 38,898 | Day-to-day drilling operations data |
| `eos_Drilling_Dtl` | 7,734 | Drilling activity details |
| `eos_Drilling_Hdr` | 349 | Drilling job headers |
| `eos_Mst_Rig` | 29 | Rig master list (names, types, locations) |
| `eos_Mst_Cost_Centre` | 31 | Cost centres (typically 1:1 with rigs) |
| `eos_Mst_Project_Contract` | 65 | Project contracts |
| `eos_Mst_Project_Contract_Dtl` | 78 | Contract details (rates, durations) |
| `eos_Mst_Rig_Operation` | 44 | Types of rig operations |
| `eos_Mst_Drilling_Operations` | 34 | Drilling operation categories |
| `eos_Mst_Drilling_Section` | 10 | Drilling sections |
| `eos_Prj_Drilling_Rate` | 162 | Drilling rate schedules |
| `eos_Lock_Transaction_Dtl` | 3,110 | Transaction locking (period close tracking) |

**Potential insights:**
- Rig utilisation rate (productive vs non-productive time)
- Drilling performance by rig, operator, or well
- Operational downtime analysis
- Contract performance vs budgeted rates
- Cost centre wise expenditure trends

---

### 1.3 Health, Safety & Environment (HSE)

| Table | Rows | Description |
|-------|------|-------------|
| `eos_Hazard_ID_Card` | 31,437 | Hazard identification cards (near-misses, unsafe acts) |
| `eos_Incident_Details` | 522 | Incident reports |
| `eos_Incident_Actions` | 83 | Corrective/preventive actions |
| `eos_Incident_Root_Cause` | 50 | Root cause classifications |
| `eos_MIS_Monthly_HSE_Manhours` | 443 | Monthly manhour tracking per rig |
| `eos_MIS_Monthly_HSE_Incidents` | 316 | Monthly incident statistics |
| `eos_MIS_Monthly_HSE_Activities` | 1,051 | Monthly HSE activities |
| `eos_MIS_Monthly_HSE_Meetings` | 395 | Safety meeting records |
| `eos_MIS_Monthly_HSE_Cards` | 62 | Monthly safety card counts |
| `eos_MIS_Monthly_HSE_Environment` | 2,320 | Environmental monitoring data |
| `eos_MIS_Monthly_HSE_Vehicle_Info` | 464 | Vehicle safety info |
| `eos_Leading_Indicators_Dtl` | 442 | Proactive safety metrics (training, audits, inspections) |
| `eos_Lagging_Indicators_Dtl` | 81 | Reactive safety metrics (LTI, TRIR, etc.) |
| `eos_HSE_Drill_Record_Hdr` / `_Event` / `_Observation` | 63 / 451 / 126 | Emergency drill records |
| `eos_HSE_Training_Group_Dtl` | 74 | HSE training records |

**Potential insights:**
- TRIR (Total Recordable Incident Rate) and LTIR trends
- Hazard card submission rate per rig (leading indicator)
- Incident frequency by type, cause, rig, and time period
- Manhour-normalised incident rates
- Corrective action closure rates and ageing
- Emergency drill compliance
- Environmental parameter trends

---

### 1.4 Finance & Procurement

| Table | Rows | Description |
|-------|------|-------------|
| `eos_Invoice_Dtl` / `_Hdr` | 3,291 / 1,626 | Client invoicing |
| `eos_Material_Requisition_Dtl` / `_Hdr` | 17,388 / 3,016 | Material purchase requests |
| `eos_GRN_Dtl` / `_Hdr` | 7,755 / 3,156 | Goods Received Notes |
| `eos_OPC_Material_Cost` | 16,009 | Operational material costs |
| `eos_OPC_Rig_Imprest` | 3,830 | Rig imprest (petty cash) accounts |
| `eos_OPC_HSD_Expense` | 30 | HSD (diesel) expenses |
| `eos_OPC_Manpower_Expense` | 40 | Manpower cost allocation |
| `eos_OPC_Yard_Imprest` | 31 | Yard-level imprest |
| `Exchange_Rate_Mst` | 5,028 | Historical exchange rates |
| `Mst_GL_Code` | 1,812 | General Ledger codes |
| `eos_Salary_Advise_LOP_Reversal` | 2,099 | Payroll adjustments |
| `eos_Salary_Adjustment` | 1,371 | Salary corrections |
| `eos_Salary_Status` | 654 | Monthly salary processing status |
| `Mstx_Vendor` | 3,225 | Vendor master |

**Potential insights:**
- Revenue per rig / per contract
- Material cost trends (by rig, category, time)
- Requisition-to-GRN cycle time
- Vendor spend analysis
- Imprest utilisation and overruns
- Payroll cost per rig / per crew type
- Currency exposure analysis

---

### 1.5 Equipment & Maintenance

| Table | Rows | Description |
|-------|------|-------------|
| `eos_Mst_Equipment` | 1,118 | Equipment master list |
| `eos_Mst_Equipment_Part` | 10,417 | Spare parts catalogue |
| `eos_Mst_Equipment_Model` | 3,289 | Equipment models |
| `eos_Mst_Equipment_Make` | 1,697 | Equipment manufacturers |
| `eos_Mst_Equipment_Group` | 94 | Equipment groups/categories |
| `eos_Equip_Cert_Dtl` | 26 | Equipment certification records |
| `eos_Vehicle_Log_Sheet` | 302 | Vehicle usage logs |
| `eos_Vehicle_Contracts` | 33 | Vehicle lease/rental contracts |
| `eos_Mst_Vehicle` | 27 | Vehicle master |

**Potential insights:**
- Equipment availability and certification status
- Spare parts consumption patterns
- Vehicle utilisation rates
- Maintenance cost tracking (via material requisitions cross-ref)

---

### 1.6 Access & IT

| Table | Rows | Description |
|-------|------|-------------|
| `User_Access_Dtl` | 86,571 | User access logs (who accessed what, when) |
| `User_Rights` | 14,189 | Current user permissions |
| `Wkg_IT_SW_License_Upload` | 568,068 | Software license inventory |
| `Mst_User` | 777 | System user master |
| `Wkg_AD_Users` | 21,385 | Active Directory user sync |
| `Wkg_Citrix_User_Dtl` | 2,277 | Citrix session details |

**Potential insights:**
- License utilisation vs procurement (cost saving)
- User activity patterns
- Access control audit (who has access to what)

---

## 2. Cross-Domain Insight Opportunities

The highest-value analytics come from joining across domains:

| Insight | Tables Involved |
|---------|----------------|
| **Rig P&L:** Revenue vs total cost (crew + material + imprest) per rig per month | `eos_Invoice_*` + `eos_OPC_*` + `eos_Mst_Rig` + `eos_Mst_Cost_Centre` |
| **Safety vs Workload:** Incident rate correlated with manhours and crew count | `eos_MIS_Monthly_HSE_Incidents` + `eos_MIS_Monthly_HSE_Manhours` + `eos_Crew_Grp_Dtl` |
| **Attrition Risk:** Exit patterns by rig, department, tenure, and rank | `hr_Emp_Exit_Dtl` + `Mst_Employee` + `eos_Mst_Rig` + `Mst_Rank` |
| **Crew Cost Efficiency:** Crew cost per productive drilling day | `eos_Fs_Contract_Dtl` + `eos_Drilling_Dtl_Ops` + `eos_Mst_Cost_Centre` |
| **Procurement Lead Time:** Requisition to GRN cycle by material type | `eos_Material_Requisition_*` + `eos_GRN_*` |
| **Certification Compliance:** Expiring certs by rig and rank | `eos_Fs_Certificates` + `eos_Buss_Cert_Dtl` + `eos_Mst_Fs_Employee` + `eos_Mst_Rig` |

---

## 3. Approach for Phase 2 Analytics

### Architecture: Tool-Based, No LLM-Generated SQL

The LLM does NOT generate SQL. All queries are pre-built Python functions (tools).
The LLM's only role is synthesising tool output into natural language.

```
User question
    ↓
Keyword-based intent router (deterministic, no LLM)
    ↓
Matched tool function (pre-built SQL, parameterised)
    ↓
Query result (rows/aggregates)
    ↓
LLM formats result into natural language answer
```

### Step 1: Define Analytics Tools
Each tool is a Python function with:
- A fixed SQL query (parameterised where needed — rig name, date range, etc.)
- Input validation (allowed parameter values)
- Output formatting (dict/list ready for the LLM to narrate)

**Example tool categories:**

| Category | Tool Examples |
|----------|---------------|
| Workforce | `get_headcount(rig, dept)`, `get_active_crew_by_rig()`, `get_attrition_trend(year)`, `get_crew_rotation_status(rig)` |
| Drilling | `get_drilling_hours(rig, year)`, `get_rig_utilisation(rig, month)`, `get_drilling_ops_breakdown(rig)` |
| HSE | `get_incident_count(rig, year)`, `get_hazard_card_trend(rig)`, `get_safety_kpis(rig, month)`, `get_incident_by_type()` |
| Finance | `get_invoice_summary(rig, year)`, `get_material_cost(rig, year)`, `get_vendor_spend(vendor)`, `get_imprest_summary(rig)` |
| Equipment | `get_equipment_list(rig)`, `get_cert_expiry_alerts()`, `get_parts_consumption(rig)` |
| General | `list_rigs()`, `list_departments()`, `list_companies()`, `get_employee_info(emp_id)` |

### Step 2: Build the Intent Router
Deterministic keyword/pattern matching — no LLM call:
- "how many employees" → `get_headcount`
- "incidents on DR01" → `get_incident_count(rig='DR01')`
- "drilling hours this year" → `get_drilling_hours(year=2026)`
- "material cost for EE02" → `get_material_cost(rig='EE02')`
- Fuzzy rig name matching (e.g., "wildcat" → Rig_Id 1)
- Date extraction from natural language ("last year" → 2025, "this month" → June 2026)

### Step 3: Parameter Extraction
Deterministic extraction of:
- **Rig names** — match against known rig list (29 rigs), fuzzy match short names
- **Date ranges** — regex patterns for "2024", "last quarter", "this month", "Jan to Mar"
- **Departments** — match against department master
- **Ranks** — match against rank master

### Step 4: Safety Guardrails
- Read-only database user for all analytics queries
- Query timeout (30 seconds max)
- Row limit on results (1000 rows max)
- Sensitive tables blacklisted (User_Rights, passwords, salary details if needed)
- All queries are pre-built — no dynamic SQL generation

---

## 4. Priority Order for Implementation

1. **Tool functions** — build the top 20 most useful query tools
2. **Intent router** — keyword/pattern matching to select the right tool
3. **Parameter extractor** — deterministic rig/date/dept extraction from user input
4. **Result formatter** — LLM takes tool output and narrates it (only LLM step)
5. **Expand tool library** — add more tools based on user feedback

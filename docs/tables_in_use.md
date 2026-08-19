# Tables In Use — Legacy Schema Reference


Every table `chatbot/views.py`, `chatbot/auth_backend.py`, `chatbot/audit.py`, and
`chatbot/analytics/*.py` actually query (via `FROM` / `JOIN` / `INTO` / `UPDATE`),
cross-referenced against the legacy schema catalog in [`db_table.md`](../db_table.md).

**80 of the legacy database's 518 tables are in scope.**

## ⚠️ Read this before generating model classes from this file

This file gives you **table names, primary keys, and column names only** — it does
**not** give you data types, nullability, lengths, or defaults, because the source
catalog (`db_table.md`) never captured them. Two further gaps:

1. **57 of the 80 tables are column-truncated in the source catalog** (marked
   `⚠ TRUNCATED` below) — `db_table.md` only recorded each table's first ~8 columns
   for wide tables, with the rest hidden behind `(+N more)`. The column lists below
   are **incomplete** for those tables.
2. **`eos_Mst_Root_Cause`** (joined in `chatbot/analytics/rigs.py`) **is not in
   `db_table.md` at all** — it's queried by the app but missing from the catalog
   entirely (a gap in the catalog, not a nonexistent table).

**Do not hand-write model field types from the "known columns" lists below** —
without real type info you'll be guessing (`Bank_ACTIVE`: bit, tinyint, or
char 'Y'/'N'? `Cr_Dt`: DATETIME or DATE?), and wrong guesses will bite you the
first time the new DB has to hold real migrated data.

### Recommended next step: generate accurate model stubs from the live schema

Run Django's own schema introspector against the **actual** ops DB connection
(`default` alias in `serosIS/settings.py`) — it reads real column types,
nullability, and lengths straight from `INFORMATION_SCHEMA` / `sys.columns`,
so nothing here needs to be guessed:

```bash
python manage.py inspectdb --database=default \
    Mst_user \
    Mst_Employee \
    Mst_Department \
    Mst_Rank \
    Mst_Emp_Type \
    Mst_Emp_Grade \
    Mst_Working_Designation \
    Mst_Cert \
    Mst_Fs_Category \
    eos_Mst_Fs_Employee \
    eos_Fs_Certificates \
    eos_Mst_Cert_Institute \
    eos_Mst_Competency \
    eos_Mst_Interviewer \
    eos_Reporting_Structure \
    eos_Job_Description_Hdr \
    eos_Job_Description_Dtl \
    eos_Travel_Eligibility \
    Mst_Company \
    Mst_Company_Location \
    Mst_Country \
    Mst_Currency \
    Mst_Location \
    eos_Mst_Rig \
    Mst_Rig_Type \
    Mst_Rig_Subtype \
    eos_Mst_Rig_Operation \
    eos_Rig_Site_Mapping \
    eos_Rig_To_Email_Mapping \
    eos_Mst_User_Rig_Mapping \
    eos_Crew_Grp_Dtl \
    eos_Crew_Grp_Rotation \
    eos_Mst_Crew_Grp \
    eos_Incident_Details \
    eos_Incident_Actions \
    eos_Incident_Root_Cause \
    Mstx_Incident_Type \
    Mstx_Incident_Cause \
    eos_Hazard_ID_Card \
    eos_Mst_Hazard_Type \
    eos_Mst_Root_Cause \
    eos_Mst_Parts_Of_Body \
    eos_Mst_Contact_Exposure_Type \
    eos_Mst_QHSE_Category \
    eos_HSE_Drill_Record_Hdr \
    eos_Mst_HSE_Drill \
    eos_Mst_HSE_Activity \
    eos_Mst_HSE_Consumable \
    eos_MIS_Monthly_HSE_Activities \
    eos_MIS_Monthly_HSE_Environment \
    eos_Lagging_Indicators_Dtl \
    eos_Leading_Indicators_Dtl \
    eos_Mst_Indicator_Type \
    eos_Mst_Indicator_Subtype \
    eos_Monthly_POB_Summary \
    eos_Drilling_Hdr \
    eos_Drilling_Dtl \
    eos_Drilling_Dtl_Ops \
    eos_Mst_Drilling_Operations \
    eos_Mst_Drilling_Section \
    eos_Mst_Drilling_Rate \
    eos_Prj_Drilling_Rate \
    eos_Mst_Project_Contract \
    eos_Mst_Project_Contract_dtl \
    eos_Mst_Cost_Centre \
    eos_Mst_Cost_Centre_Type \
    eos_Invoice_Hdr \
    eos_Service_Details \
    Mst_Serv_Subtype \
    eos_GRN_Hdr \
    eos_Material_Requisition_Hdr \
    eos_OPC_Material_Cost \
    eos_Mst_Contractor \
    eos_Mst_Operator \
    Mstx_Vendor \
    eos_Doc_To_Sign_Mapping \
    eos_Mst_User_Fs_Catg_Mapping \
    eos_Email_Notification_Type \
    Mail_Alert_Dtl \
    Mstx_Work_Location \
    > /tmp/legacy_models_raw.py
```


This produces one (unmanaged) Django model per table with real field types
already inferred — `managed = False`, `db_table = "..."` — which you then use as
the **starting point**: strip the ones you don't need, rename to your new-DB
convention, drop `managed = False` once it's pointed at the new database, and add
your own `Meta`/relations. Far less error-prone than hand-typing 80 model classes
from a column-name list.

If `inspectdb` isn't runnable from wherever you generate this (no DB
connectivity), the other authoritative source is the full DDL dump referenced in
`docs/sqlserver_migration_plan.md` (`database/script_mssql.sql`) — that file is
git-ignored (`*.sql`) and isn't in this checkout; if you have it locally, share it
and it can be parsed directly for exact column types instead.

---


## Auth

### `Mst_user`  _(catalog casing: `Mst_User`)_
- **PK:** `USER_ID`
- **⚠ TRUNCATED** — catalog shows only 8 of an unknown larger total (**+8 more not captured**)
- **Known columns (8, incomplete):** `USER_ID`, `USER_NAME`, `EMP_ID`, `NONEMP_ID`, `DEPT_ID`, `USER_LOGIN_ID`, `USER_ACTIVE`, `USER_TYPE_ID`


## HR / Employee

### `Mst_Employee`
- **PK:** `EMP_ID`
- **⚠ TRUNCATED** — catalog shows only 8 of an unknown larger total (**+17 more not captured**)
- **Known columns (8, incomplete):** `EMP_ID`, `COMPANY_ID`, `DEPT_ID`, `COMPANY_LOC_ID`, `Emp_Fname`, `Emp_Mname`, `Emp_Sname`, `EMP_TITLE`

### `Mst_Department`
- **PK:** `Dept_Id`
- **⚠ TRUNCATED** — catalog shows only 8 of an unknown larger total (**+2 more not captured**)
- **Known columns (8, incomplete):** `Dept_Id`, `Dept_Name`, `Dept_Dispname`, `Dept_Abrv`, `Dept_Order`, `Dept_Active`, `Cr_User_Id`, `Cr_Dt`

### `Mst_Rank`
- **PK:** `rank_id`
- **⚠ TRUNCATED** — catalog shows only 8 of an unknown larger total (**+6 more not captured**)
- **Known columns (8, incomplete):** `rank_id`, `fs_category_id`, `vessel_dept_id`, `rank_name`, `rank_abrv`, `rank_order`, `Business_System_Id_2`, `Business_System_Id_5`

### `Mst_Emp_Type`
- **PK:** `emp_type_id`
- **⚠ TRUNCATED** — catalog shows only 8 of an unknown larger total (**+5 more not captured**)
- **Known columns (8, incomplete):** `emp_type_id`, `emp_nature_id`, `emp_type_name`, `Currency_Id`, `Business_System_Id_2`, `Business_System_Id_5`, `Business_System_Id_6`, `Business_System_Id_11`

### `Mst_Emp_Grade`
- **PK:** `Emp_Grade_Id`
- **⚠ TRUNCATED** — catalog shows only 8 of an unknown larger total (**+1 more not captured**)
- **Known columns (8, incomplete):** `Emp_Grade_Id`, `Emp_Grade`, `Emp_Designation`, `Emp_Grade_Order`, `Emp_Grade_Active`, `Cr_User_Id`, `Cr_Dt`, `Mod_User_Id`

### `Mst_Working_Designation`
- **PK:** `Working_Designation_Id`
- **⚠ TRUNCATED** — catalog shows only 8 of an unknown larger total (**+1 more not captured**)
- **Known columns (8, incomplete):** `Working_Designation_Id`, `Working_Designation`, `Critical_Flag`, `Usage_Filter`, `Working_Designation_Active`, `Cr_User_Id`, `Cr_Dt`, `Mod_User_Id`

### `Mst_Cert`
- **PK:** `cert_id`
- **⚠ TRUNCATED** — catalog shows only 8 of an unknown larger total (**+4 more not captured**)
- **Known columns (8, incomplete):** `cert_id`, `cert_type_id`, `cert_name`, `cert_abrv`, `vessel_dept_id`, `Cert_Training_Type`, `Business_System_Id_2`, `Business_System_Id_6`

### `Mst_Fs_Category`
- **PK:** `fs_category_id`
- **⚠ TRUNCATED** — catalog shows only 8 of an unknown larger total (**+3 more not captured**)
- **Known columns (8, incomplete):** `fs_category_id`, `fs_category_name`, `Business_System_Id_2`, `Business_System_Id_5`, `Business_System_Id_6`, `Business_System_Id_11`, `Business_System_Id_16`, `cr_user_id`

### `eos_Mst_Fs_Employee`
- **PK:** `Fs_Emp_Id`
- **⚠ TRUNCATED** — catalog shows only 8 of an unknown larger total (**+55 more not captured**)
- **Known columns (8, incomplete):** `Fs_Emp_Id`, `Fs_Emp_Fname`, `Fs_Emp_Mname`, `Fs_Emp_Lname`, `Permanent_Addr`, `Mailing_Addr`, `Emergency_Addr`, `Fs_Emp_Tel_No`

### `eos_Fs_Certificates`
- **PK:** `Fs_Certificate_Id`
- **⚠ TRUNCATED** — catalog shows only 8 of an unknown larger total (**+8 more not captured**)
- **Known columns (8, incomplete):** `Fs_Certificate_Id`, `Fs_Emp_Id`, `Cert_Id`, `Cert_Level`, `Fs_Cert_No`, `Fs_Cert_Dt`, `Location_Id`, `Cert_Institute_Id`

### `eos_Mst_Cert_Institute`
- **PK:** `Cert_Institute_Id`
- **⚠ TRUNCATED** — catalog shows only 8 of an unknown larger total (**+2 more not captured**)
- **Known columns (8, incomplete):** `Cert_Institute_Id`, `Cert_Institute_Name`, `Cert_Institute_Shortname`, `Cert_Institute_Address`, `Location_Id`, `Tel_No`, `Cr_User_Id`, `Cr_Dt`

### `eos_Mst_Competency`
- **PK:** `Competency_Id`
- **Known columns (8):** `Competency_Id`, `Competency_Name`, `Dept_Id`, `Active`, `Cr_User_Id`, `Cr_Dt`, `Mod_User_Id`, `Mod_Dt`

### `eos_Mst_Interviewer`
- **PK:** `Interviewer_Id`
- **⚠ TRUNCATED** — catalog shows only 8 of an unknown larger total (**+1 more not captured**)
- **Known columns (8, incomplete):** `Interviewer_Id`, `User_Id`, `Dept_Id`, `Sign_Path`, `Active`, `Cr_User_Id`, `Cr_Dt`, `Mod_User_Id`

### `eos_Reporting_Structure`
- **PK:** _not recorded / composite / none_
- **Known columns (8):** `Reporting_Structure_Id`, `Fs_Category_Id`, `Rank_Id`, `Reporting_Rank_Id`, `Cr_User_Id`, `Cr_Dt`, `Mod_User_Id`, `Mod_Dt`

### `eos_Job_Description_Hdr`
- **PK:** `JD_Hdr_Id`
- **⚠ TRUNCATED** — catalog shows only 8 of an unknown larger total (**+2 more not captured**)
- **Known columns (8, incomplete):** `JD_Hdr_Id`, `Fs_Category_Id`, `Rank_Id`, `JD_Hdr_Description`, `JD_Hdr_Order`, `JD_Hdr_Active`, `Cr_User_Id`, `Cr_Dt`

### `eos_Job_Description_Dtl`
- **PK:** _not recorded / composite / none_
- **⚠ TRUNCATED** — catalog shows only 8 of an unknown larger total (**+1 more not captured**)
- **Known columns (8, incomplete):** `JD_Dtl_Id`, `JD_Hdr_Id`, `JD_Dtl_Description`, `JD_Dtl_Order`, `JD_Dtl_Active`, `Cr_User_Id`, `Cr_Dt`, `Mod_User_Id`

### `eos_Travel_Eligibility`
- **PK:** `Travel_Eligibility_Id`
- **⚠ TRUNCATED** — catalog shows only 8 of an unknown larger total (**+4 more not captured**)
- **Known columns (8, incomplete):** `Travel_Eligibility_Id`, `Fs_Category_Id`, `Rank_Id`, `Travel_Mode`, `Travel_Class`, `Travel_Preference`, `Eligible_From`, `Eligible_To`


## Org / Geography

### `Mst_Company`
- **PK:** `COMPANY_ID`
- **⚠ TRUNCATED** — catalog shows only 8 of an unknown larger total (**+15 more not captured**)
- **Known columns (8, incomplete):** `COMPANY_ID`, `Organisational_Grp_Id`, `Business_Grp_Id`, `Company_Name`, `Parent_Company_Id`, `Company_ABRV`, `Company_Code`, `Country_Id`

### `Mst_Company_Location`
- **PK:** `Company_Loc_Id`
- **⚠ TRUNCATED** — catalog shows only 8 of an unknown larger total (**+11 more not captured**)
- **Known columns (8, incomplete):** `Company_Loc_Id`, `Company_Loc_NAME`, `Company_Loc_ABRV`, `Company_Loc_Address`, `Location_Id`, `Postal_Code`, `Country_Id`, `Latitude`

### `Mst_Country`
- **PK:** `country_id`
- **⚠ TRUNCATED** — catalog shows only 8 of an unknown larger total (**+2 more not captured**)
- **Known columns (8, incomplete):** `country_id`, `country_name`, `Country_Known_Name`, `Country_ISO_Cd`, `Continent_Id`, `country_active`, `cr_user_id`, `cr_dt`

### `Mst_Currency`
- **PK:** `Currency_Id`
- **⚠ TRUNCATED** — catalog shows only 8 of an unknown larger total (**+2 more not captured**)
- **Known columns (8, incomplete):** `Currency_Id`, `Currency_Name`, `Currency_Abrv`, `Decimal_Name`, `Currency_Text`, `Currency_Active`, `CR_USER_ID`, `CR_DT`

### `Mst_Location`
- **PK:** `Location_Id`
- **⚠ TRUNCATED** — catalog shows only 8 of an unknown larger total (**+1 more not captured**)
- **Known columns (8, incomplete):** `Location_Id`, `Country_Id`, `Country_State_Id`, `Location_Name`, `location_active`, `Cr_User_Id`, `Cr_Dt`, `Mod_User_Id`


## Rig

### `eos_Mst_Rig`
- **PK:** `Rig_Id`
- **⚠ TRUNCATED** — catalog shows only 8 of an unknown larger total (**+11 more not captured**)
- **Known columns (8, incomplete):** `Rig_Id`, `Rig_Name`, `Rig_Short_Name`, `Old_Rig_Name`, `Rig_Subtype_Id`, `Rig_Type_Id`, `Rig_Built_Dt`, `Rig_Tel_No`

### `Mst_Rig_Type`
- **PK:** `Rig_Type_Id`
- **Known columns (6):** `Rig_Type_Id`, `Rig_Type_Name`, `Cr_User_Id`, `Cr_Dt`, `Mod_User_Id`, `Mod_Dt`

### `Mst_Rig_Subtype`
- **PK:** `Rig_Subtype_Id`
- **Known columns (7):** `Rig_Subtype_Id`, `Rig_Subtype_Name`, `Rig_Type_Id`, `Cr_User_Id`, `Cr_Dt`, `Mod_User_Id`, `Mod_Dt`

### `eos_Mst_Rig_Operation`
- **PK:** `Rig_Operation_Id`
- **Known columns (6):** `Rig_Operation_Id`, `Rig_Operation_Name`, `Cr_User_Id`, `Cr_Dt`, `Mod_User_Id`, `Mod_Dt`

### `eos_Rig_Site_Mapping`
- **PK:** `Rig_Site_Mapping_Id`
- **⚠ TRUNCATED** — catalog shows only 8 of an unknown larger total (**+7 more not captured**)
- **Known columns (8, incomplete):** `Rig_Site_Mapping_Id`, `Rig_Id`, `Company_Id`, `Camp_Office_Addr`, `Contact_Fs_Emp_Id_1`, `Contact_Tel_No_1`, `Contact_Fs_Emp_Id_2`, `Contact_Tel_No_2`

### `eos_Rig_To_Email_Mapping`
- **PK:** _not recorded / composite / none_
- **⚠ TRUNCATED** — catalog shows only 8 of an unknown larger total (**+4 more not captured**)
- **Known columns (8, incomplete):** `Rig_To_Email_Mapping_Id`, `Rig_Id`, `User_Id`, `Alert_Id`, `Company_Id`, `Addressee_Type`, `From_Dt`, `To_Dt`

### `eos_Mst_User_Rig_Mapping`
- **PK:** _not recorded / composite / none_
- **⚠ TRUNCATED** — catalog shows only 8 of an unknown larger total (**+1 more not captured**)
- **Known columns (8, incomplete):** `User_Rig_Mapping_Id`, `User_Id`, `Rig_Id`, `User_Rig_Mapping_From`, `User_Rig_Mapping_To`, `Cr_User_Id`, `Cr_Dt`, `Mod_User_Id`


## Crew

### `eos_Crew_Grp_Dtl`
- **PK:** _not recorded / composite / none_
- **⚠ TRUNCATED** — catalog shows only 8 of an unknown larger total (**+2 more not captured**)
- **Known columns (8, incomplete):** `Crew_Grp_Dtl_Id`, `Fs_Emp_Id`, `Rig_Id`, `Crew_Grp_Id`, `Crew_Grp_From`, `Crew_Grp_To`, `Cr_User_Id`, `Cr_Dt`

### `eos_Crew_Grp_Rotation`
- **PK:** _not recorded / composite / none_
- **⚠ TRUNCATED** — catalog shows only 8 of an unknown larger total (**+1 more not captured**)
- **Known columns (8, incomplete):** `Crew_Grp_Rotation_Id`, `Crew_Grp_Id`, `Relieving_Crew_Grp_Id`, `Crew_Grp_On_Dt`, `Crew_Grp_Off_Dt`, `Cr_User_Id`, `Cr_Dt`, `Mod_User_Id`

### `eos_Mst_Crew_Grp`
- **PK:** `Crew_Grp_Id`
- **Known columns (8):** `Crew_Grp_Id`, `Crew_Grp_Name`, `Rig_Id`, `Hitch`, `Cr_User_Id`, `Cr_Dt`, `Mod_User_Id`, `Mod_Dt`


## QHSE / Incidents / Hazards

### `eos_Incident_Details`
- **PK:** `Incident_Id`
- **⚠ TRUNCATED** — catalog shows only 8 of an unknown larger total (**+46 more not captured**)
- **Known columns (8, incomplete):** `Incident_Id`, `Work_Location_Id`, `Rig_Id`, `Unit_Name`, `Rig_Incident_No`, `Incident_No`, `Incident_Date`, `Financial_Year_Id`

### `eos_Incident_Actions`
- **PK:** _not recorded / composite / none_
- **⚠ TRUNCATED** — catalog shows only 8 of an unknown larger total (**+6 more not captured**)
- **Known columns (8, incomplete):** `Incident_Action_Id`, `Incident_Id`, `Action_Recommended`, `Action_Taken`, `Action_Party`, `Target_Date`, `Completion_Dt`, `Action_Status`

### `eos_Incident_Root_Cause`
- **PK:** _not recorded / composite / none_
- **⚠ TRUNCATED** — catalog shows only 8 of an unknown larger total (**+3 more not captured**)
- **Known columns (8, incomplete):** `Incident_Root_Cause_Id`, `Incident_Id`, `Root_Cause_Id`, `Root_Subcause_Id`, `Root_Subcause_Others`, `Marked_As_Deleted`, `Deleted_Remarks`, `Cr_User_Id`

### `Mstx_Incident_Type`
- **PK:** `Incident_Type_Id`
- **Known columns (8):** `Incident_Type_Id`, `Incident_Type`, `Incident_Abrv`, `Business_System_Id_6`, `Cr_User_Id`, `Cr_Dt`, `Mod_User_Id`, `Mod_Dt`

### `Mstx_Incident_Cause`
- **PK:** `Incident_Cause_Id`
- **Known columns (8):** `Incident_Cause_Id`, `Incident_Cause_Desc`, `Incident_Cause_Category`, `Business_System_Id_6`, `Cr_User_Id`, `Cr_Dt`, `Mod_User_Id`, `Mod_Dt`

### `eos_Hazard_ID_Card`
- **PK:** `Haz_Card_Id`
- **⚠ TRUNCATED** — catalog shows only 8 of an unknown larger total (**+17 more not captured**)
- **Known columns (8, incomplete):** `Haz_Card_Id`, `Haz_ID_Card_No`, `Prj_Contract_Id`, `Rig_Id`, `Event_Dt`, `Reported_By_Party`, `Reported_By_Fs_Emp_Id`, `Reported_By_Name`

### `eos_Mst_Hazard_Type`
- **PK:** `Haz_Type_Id`
- **Known columns (8):** `Haz_Type_Id`, `Haz_Type_Name`, `Haz_Type_Class`, `Haz_Type_Active`, `Cr_User_Id`, `Cr_Dt`, `Mod_User_Id`, `Mod_Dt`

### `eos_Mst_Root_Cause`
**⚠ NOT IN CATALOG** — referenced in code, absent from `db_table.md`. Needs `inspectdb`/live-schema lookup — no column data available here.

### `eos_Mst_Parts_Of_Body`
- **PK:** `Part_Of_Body_Id`
- **Known columns (6):** `Part_Of_Body_Id`, `Part_Of_Body_Name`, `Cr_User_Id`, `Cr_Dt`, `Mod_User_Id`, `Mod_Dt`

### `eos_Mst_Contact_Exposure_Type`
- **PK:** `Contact_Expo_Type_Id`
- **Known columns (6):** `Contact_Expo_Type_Id`, `Contact_Expo_Type_Name`, `Cr_User_Id`, `Cr_Dt`, `Mod_User_Id`, `Mod_Dt`

### `eos_Mst_QHSE_Category`
- **PK:** `QHSE_Category_Id`
- **Known columns (6):** `QHSE_Category_Id`, `QHSE_Category_Name`, `Cr_User_Id`, `Cr_Dt`, `Mod_User_Id`, `Mod_Dt`

### `eos_HSE_Drill_Record_Hdr`
- **PK:** `Drill_Record_Hdr_Id`
- **⚠ TRUNCATED** — catalog shows only 8 of an unknown larger total (**+24 more not captured**)
- **Known columns (8, incomplete):** `Drill_Record_Hdr_Id`, `Rig_Id`, `Drill_Record_Sr_No`, `Drill_Record_No`, `Drill_Dt`, `Drill_Location`, `HSE_Drill_Id_1`, `HSE_Drill_Id_2`

### `eos_Mst_HSE_Drill`
- **PK:** `HSE_Drill_Id`
- **⚠ TRUNCATED** — catalog shows only 8 of an unknown larger total (**+1 more not captured**)
- **Known columns (8, incomplete):** `HSE_Drill_Id`, `HSE_Drill_Name`, `HSE_Drill_Frequency`, `Rig_Type_Id`, `HSE_Drill_Active`, `Cr_User_Id`, `Cr_Dt`, `Mod_User_Id`

### `eos_Mst_HSE_Activity`
- **PK:** `HSE_Activity_Id`
- **Known columns (7):** `HSE_Activity_Id`, `HSE_Activity_Name`, `HSE_Activity_Type`, `Cr_User_Id`, `Cr_Dt`, `Mod_User_Id`, `Mod_Dt`

### `eos_Mst_HSE_Consumable`
- **PK:** `HSE_Consumable_Id`
- **Known columns (7):** `HSE_Consumable_Id`, `HSE_Consumable_Name`, `HSE_Consumption_Unit`, `Cr_User_Id`, `Cr_Dt`, `Mod_User_Id`, `Mod_Dt`

### `eos_MIS_Monthly_HSE_Activities`
- **PK:** _not recorded / composite / none_
- **⚠ TRUNCATED** — catalog shows only 8 of an unknown larger total (**+2 more not captured**)
- **Known columns (8, incomplete):** `Monthly_HSE_Activity_Id`, `Monthly_HSE_Returns_Hdr_Id`, `HSE_Activity_Id`, `Total_Activities`, `Eosil_Emp_Count`, `Contractor_Count`, `Cr_User_Id`, `Cr_Dt`

### `eos_MIS_Monthly_HSE_Environment`
- **PK:** _not recorded / composite / none_
- **⚠ TRUNCATED** — catalog shows only 8 of an unknown larger total (**+1 more not captured**)
- **Known columns (8, incomplete):** `Monthly_HSE_Environment_Id`, `Monthly_HSE_Returns_Hdr_Id`, `HSE_Consumable_Id`, `Total_Quantity`, `Remarks`, `Cr_User_Id`, `Cr_Dt`, `Mod_User_Id`

### `eos_Lagging_Indicators_Dtl`
- **PK:** _not recorded / composite / none_
- **⚠ TRUNCATED** — catalog shows only 8 of an unknown larger total (**+3 more not captured**)
- **Known columns (8, incomplete):** `Lagging_Indicator_Dtl_Id`, `Lagging_Indicator_Id`, `Workgroup_Id`, `Indicator_Type_Id`, `Indicator_Subtype_Id`, `Total_Count`, `Active`, `Cr_User_Id`

### `eos_Leading_Indicators_Dtl`
- **PK:** _not recorded / composite / none_
- **⚠ TRUNCATED** — catalog shows only 8 of an unknown larger total (**+6 more not captured**)
- **Known columns (8, incomplete):** `Leading_Indicator_Dtl_Id`, `Leading_Indicator_Id`, `Workgroup_Id`, `Indicator_Type_Id`, `Indicator_Subtype_Id`, `Total_Sessions`, `No_Of_Persons`, `Total_Duration`

### `eos_Mst_Indicator_Type`
- **PK:** `Indicator_Type_Id`
- **Known columns (8):** `Indicator_Type_Id`, `Indicator_Type_Name`, `Indicator_Type_Order`, `Report_Type`, `Cr_User_Id`, `Cr_Dt`, `Mod_User_Id`, `Mod_Dt`

### `eos_Mst_Indicator_Subtype`
- **PK:** `Indicator_Subtype_Id`
- **Known columns (8):** `Indicator_Subtype_Id`, `Indicator_Type_Id`, `Indicator_Subtype_Name`, `Indicator_Subtype_Order`, `Cr_User_Id`, `Cr_Dt`, `Mod_User_Id`, `Mod_Dt`

### `eos_Monthly_POB_Summary`
- **PK:** _not recorded / composite / none_
- **⚠ TRUNCATED** — catalog shows only 8 of an unknown larger total (**+1 more not captured**)
- **Known columns (8, incomplete):** `Monthly_POB_Id`, `Rig_Id`, `POB_Month`, `POB_Manhours_EOSIL`, `POB_Manhours_TP`, `Cr_User_Id`, `Cr_Dt`, `Mod_User_Id`


## Drilling / Ops

### `eos_Drilling_Hdr`
- **PK:** `Drilling_Hdr_Id`
- **⚠ TRUNCATED** — catalog shows only 8 of an unknown larger total (**+19 more not captured**)
- **Known columns (8, incomplete):** `Drilling_Hdr_Id`, `Prj_Contract_Id`, `Rig_Id`, `Latitude`, `Longitude`, `Location`, `Total_Water_Depth`, `Total_Depth`

### `eos_Drilling_Dtl`
- **PK:** `Drilling_Dtl_Id`
- **⚠ TRUNCATED** — catalog shows only 8 of an unknown larger total (**+33 more not captured**)
- **Known columns (8, incomplete):** `Drilling_Dtl_Id`, `Rig_Id`, `Drilling_Hdr_Id`, `Drilling_Dtl_Dt`, `POB_Operator`, `POB_Essar`, `POB_Essar_Serv`, `POB_Others`

### `eos_Drilling_Dtl_Ops`
- **PK:** _not recorded / composite / none_
- **⚠ TRUNCATED** — catalog shows only 8 of an unknown larger total (**+9 more not captured**)
- **Known columns (8, incomplete):** `Drilling_Dtl_Ops_Id`, `Drilling_Dtl_Id`, `Time_From`, `Time_To`, `Work_Shift`, `Duration`, `Drilling_Ops_Id`, `Drilling_Section_Id`

### `eos_Mst_Drilling_Operations`
- **PK:** `Drilling_Ops_Id`
- **Known columns (7):** `Drilling_Ops_Id`, `Drilling_Ops_Code_No`, `Drilling_Ops_Name`, `Cr_User_Id`, `Cr_Dt`, `Mod_User_Id`, `Mod_Dt`

### `eos_Mst_Drilling_Section`
- **PK:** `Drilling_Section_Id`
- **Known columns (6):** `Drilling_Section_Id`, `Drilling_Section_Name`, `Cr_User_Id`, `Cr_Dt`, `Mod_User_Id`, `Mod_Dt`

### `eos_Mst_Drilling_Rate`
- **PK:** `Drilling_Rate_Id`
- **Known columns (8):** `Drilling_Rate_Id`, `Rate_Code`, `Rate_Description`, `Rate_Active`, `Cr_User_Id`, `Cr_Dt`, `Mod_User_Id`, `Mod_Dt`

### `eos_Prj_Drilling_Rate`
- **PK:** `Prj_Drilling_Rate_Id`
- **⚠ TRUNCATED** — catalog shows only 8 of an unknown larger total (**+2 more not captured**)
- **Known columns (8, incomplete):** `Prj_Drilling_Rate_Id`, `Drilling_Rate_Id`, `Prj_Contract_Id`, `Rig_Id`, `Currency_Id`, `Rate`, `Cr_User_Id`, `Cr_Dt`


## Contracts / Finance / Materials

### `eos_Mst_Project_Contract`
- **PK:** `Prj_Contract_Id`
- **⚠ TRUNCATED** — catalog shows only 8 of an unknown larger total (**+3 more not captured**)
- **Known columns (8, incomplete):** `Prj_Contract_Id`, `Location_Id`, `Operator_Id`, `Prj_Contract_No`, `Prj_Short_Name`, `Prj_Start_Dt`, `Prj_End_Dt`, `Cr_User_Id`

### `eos_Mst_Project_Contract_dtl`  _(catalog casing: `eos_Mst_Project_Contract_Dtl`)_
- **PK:** _not recorded / composite / none_
- **⚠ TRUNCATED** — catalog shows only 8 of an unknown larger total (**+1 more not captured**)
- **Known columns (8, incomplete):** `Prj_Contract_Dtl_Id`, `Prj_Contract_Id`, `Rig_Id`, `Rig_Active_From`, `Rig_Active_To`, `Cr_User_Id`, `Cr_Dt`, `Mod_User_Id`

### `eos_Mst_Cost_Centre`
- **PK:** `Cost_Centre_Id`
- **⚠ TRUNCATED** — catalog shows only 8 of an unknown larger total (**+4 more not captured**)
- **Known columns (8, incomplete):** `Cost_Centre_Id`, `Cost_Centre_Type_Id`, `Cost_Centre_Name`, `Old_Cost_Centre_Name`, `Rig_Id`, `Fs_Emp_Id`, `Location_Id`, `Cost_Centre_Active`

### `eos_Mst_Cost_Centre_Type`
- **PK:** `Cost_Centre_Type_Id`
- **Known columns (8):** `Cost_Centre_Type_Id`, `Cost_Centre_Type_Name`, `Cost_Centre_Type_Shortname`, `Cost_Centre_Type_Active`, `Cr_User_Id`, `Cr_Dt`, `Mod_User_Id`, `Mod_Dt`

### `eos_Invoice_Hdr`
- **PK:** `Invoice_Hdr_Id`
- **⚠ TRUNCATED** — catalog shows only 8 of an unknown larger total (**+50 more not captured**)
- **Known columns (8, incomplete):** `Invoice_Hdr_Id`, `Cost_Centre_Id`, `Prj_Contract_Id`, `Invoice_Type`, `Invoice_No`, `Invoice_Dt`, `Invoice_Amt`, `Invoice_Month`

### `eos_Service_Details`
- **PK:** `Serv_Dtl_Id`
- **⚠ TRUNCATED** — catalog shows only 8 of an unknown larger total (**+7 more not captured**)
- **Known columns (8, incomplete):** `Serv_Dtl_Id`, `Fs_Emp_Id`, `Serv_Subtype_From`, `Rank_Id`, `Serv_Type_Id`, `Serv_Subtype_Id`, `Rig_Id`, `Emp_Type_Id`

### `Mst_Serv_Subtype`
- **PK:** `serv_subtype_id`
- **⚠ TRUNCATED** — catalog shows only 8 of an unknown larger total (**+1 more not captured**)
- **Known columns (8, incomplete):** `serv_subtype_id`, `serv_subtype_name`, `serv_subtype_abrv`, `Business_System_Id_2`, `Business_System_Id_6`, `cr_user_id`, `cr_dt`, `mod_user_id`

### `eos_GRN_Hdr`
- **PK:** `Grn_Hdr_Id`
- **⚠ TRUNCATED** — catalog shows only 8 of an unknown larger total (**+21 more not captured**)
- **Known columns (8, incomplete):** `Grn_Hdr_Id`, `Grn_No`, `Grn_Dt`, `Location`, `Vendor_Id`, `Receipt_Dt`, `Requisition_Type`, `MR_Hdr_Id`

### `eos_Material_Requisition_Hdr`
- **PK:** `MR_Hdr_Id`
- **⚠ TRUNCATED** — catalog shows only 8 of an unknown larger total (**+27 more not captured**)
- **Known columns (8, incomplete):** `MR_Hdr_Id`, `Prj_Contract_Id`, `Rig_id`, `MR_No`, `MR_Dt`, `Dept_Id`, `Priority`, `MR_Type`

### `eos_OPC_Material_Cost`
- **PK:** _not recorded / composite / none_
- **⚠ TRUNCATED** — catalog shows only 8 of an unknown larger total (**+20 more not captured**)
- **Known columns (8, incomplete):** `Material_Cost_Id`, `Cost_Centre_Id`, `Expense_Month`, `Dept_Id`, `OPC_Category_Id`, `GRN_Dtl_Id`, `MIN_No`, `Sr_No`


## Vendors / Contractors / Operators

### `eos_Mst_Contractor`
- **PK:** `Contractor_Id`
- **Known columns (6):** `Contractor_Id`, `Contractor_Name`, `Cr_User_Id`, `Cr_Dt`, `Mod_User_Id`, `Mod_Dt`

### `eos_Mst_Operator`
- **PK:** `Operator_Id`
- **⚠ TRUNCATED** — catalog shows only 8 of an unknown larger total (**+7 more not captured**)
- **Known columns (8, incomplete):** `Operator_Id`, `Operator_Name`, `Operator_Short_Name`, `Operator_SAP_Code`, `WBS_Client_Code`, `Location_Id`, `Country_Id`, `Contact_Person`

### `Mstx_Vendor`
- **PK:** `Vendor_Id`
- **⚠ TRUNCATED** — catalog shows only 8 of an unknown larger total (**+12 more not captured**)
- **Known columns (8, incomplete):** `Vendor_Id`, `Vendor_Name`, `Vendor_Type_Id`, `Vendor_SAP_Code`, `Vendor_Address`, `Country_id`, `Vendor_Tel_No`, `Vendor_Email`


## Docs / Mapping / Notifications

### `eos_Doc_To_Sign_Mapping`
- **PK:** _not recorded / composite / none_
- **⚠ TRUNCATED** — catalog shows only 8 of an unknown larger total (**+2 more not captured**)
- **Known columns (8, incomplete):** `Doc_To_Sign_Id`, `Doc_Name`, `Emp_Id`, `Sign_Path`, `Sign_From`, `Sign_To`, `Cr_User_Id`, `Cr_Dt`

### `eos_Mst_User_Fs_Catg_Mapping`
- **PK:** _not recorded / composite / none_
- **⚠ TRUNCATED** — catalog shows only 8 of an unknown larger total (**+1 more not captured**)
- **Known columns (8, incomplete):** `User_Fs_Catg_Mapping_Id`, `User_Id`, `Fs_Category_Id`, `User_Fs_Catg_Mapping_From`, `User_Fs_Catg_Mapping_To`, `Cr_User_Id`, `Cr_Dt`, `Mod_User_Id`

### `eos_Email_Notification_Type`
- **PK:** `EN_Type_Id`
- **⚠ TRUNCATED** — catalog shows only 8 of an unknown larger total (**+1 more not captured**)
- **Known columns (8, incomplete):** `EN_Type_Id`, `EN_Type_Name`, `EN_Type_Subject`, `EN_Description`, `EN_Type_Active`, `Cr_User_Id`, `Cr_Dt`, `Mod_User_Id`

### `Mail_Alert_Dtl`
- **PK:** `Alert_Id`
- **⚠ TRUNCATED** — catalog shows only 8 of an unknown larger total (**+11 more not captured**)
- **Known columns (8, incomplete):** `Alert_Id`, `Business_System_Id`, `Alert_Type`, `Alert_Category`, `Alert_Name`, `Alert_Window`, `Alert_Freq`, `Menu_Id`


## Work Location

### `Mstx_Work_Location`
- **PK:** `Work_Location_Id`
- **Known columns (7):** `Work_Location_Id`, `Work_Location`, `Business_System_Id_6`, `Cr_User_Id`, `Cr_Dt`, `Mod_User_Id`, `Mod_Dt`


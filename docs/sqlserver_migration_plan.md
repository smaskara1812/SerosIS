# SQL Server Migration Plan

**Status:** planning · **Owner:** _TBD_ · **Last updated:** 2026-08-14

> MySQL is the temporary development database. **Production runs on SQL Server.**
> Authoritative table/schema names live in [`database/script_mssql.sql`](../database/script_mssql.sql).
> This document is the plan to make the Django app run cleanly on SQL Server with
> minimal ongoing strain.

---

## 1. Goal

Every raw SQL statement the app runs must work on **both** MySQL (dev) and SQL Server
(prod) with **no per-query rewriting** and no behaviour change on MySQL today.

The mechanism already exists — `chatbot/db/sql.py :: maybe_translate(sql, params)` —
it is just not applied everywhere yet. The plan is to make it the single choke point
for all raw SQL, complete its rules, and add guard rails so the problem can't regress.

---

## 2. Current state (findings)

### 2.1 What the app's raw SQL touches
The app only references **two** of the SQL Server schemas:

| In code (MySQL flat name) | In production (SQL Server) | Schema |
|---|---|---|
| `eos_Mst_Rig`, `eos_Travel_Eligibility`, `eos_MIS_Monthly_HSE_*`, … | `eos.Mst_Rig`, `eos.Travel_Eligibility`, … | `eos` |
| `Mst_user`, `Mst_Department`, `Mst_Rank`, `Mstx_Incident_Type`, … | `dbo.Mst_user`, `dbo.Mst_Department`, … | `dbo` |

The DB also has `hr`, `ser`, `shp`, `ebtsl` schemas — **the app does not use them** (other modules).
So this is a **two-schema** problem, not six.

### 2.2 The translator (`chatbot/db/sql.py`)
`maybe_translate(sql, params)` converts MySQL-flavoured SQL → SQL Server when
`USE_MSSQL=true`, and is a **pass-through on MySQL**. It already handles:

- `eos_TableName → eos.TableName` (rule: `\beos_(?=[A-Z])`)
- `CURDATE()/NOW() → CAST(GETDATE() AS DATE)/GETDATE()`
- `DATE(x)`, `DATE_FORMAT(...)`, `DATE_SUB/ADD → DATEADD`, `DATEDIFF` arg flip
- `IF() → IIF()`, `col IS [NOT] NULL → CASE …`, `CAST(x AS CHAR) → VARCHAR(50)`
- reserved-word aliases `AS open/type/key → AS [open]/…`
- `LIMIT n` / `LIMIT %s [OFFSET %s]` → `OFFSET … ROWS FETCH NEXT … ROWS ONLY`

### 2.3 The gap (the actual landmine)
Only the **analytics layer** routes through the translator
(`chatbot/analytics/tools.py`, 1 call site).
Everything else runs **raw** and bypasses it:

| Module | raw `.execute(` calls | routed through translator? |
|---|---|---|
| `chatbot/views.py` | **183** | ❌ no |
| `chatbot/auth_backend.py` | 1 | ❌ no |
| `chatbot/health.py` | 1 | ❌ no |
| `chatbot/analytics/tools.py` | 1 | ✅ yes |

On SQL Server these 185 statements would run MySQL SQL unchanged → `eos_X` names
never become `eos.X`, `NOW()`/`LIMIT` never adapt, etc.

### 2.4 What is already migration-ready
- **Audit trail** (`chatbot/audit.py`): its only raw SQL (`snap()`) already routes
  through `maybe_translate`; every table it references is `eos_`-prefixed; writes go
  through Django's ORM (backend-correct automatically). No further work needed.
- **Django ORM models** (`cb_*` tables, auth/sessions): the ORM emits correct SQL per
  backend automatically.
- **Config**: `USE_MSSQL` flag + ODBC config in `chatbot/db/config.py`;
  `tests/test_mssql_connections.py` exists.

---

## 3. Strategy

**One choke point.** Introduce a thin helper and funnel *all* raw SQL through it:

```python
# chatbot/db/sql.py (or chatbot/db/__init__.py)
def dbq(cursor, sql, params=()):
    """Execute raw SQL through the dialect translator.
    No-op on MySQL; adapts to SQL Server when USE_MSSQL=true."""
    sql, params = maybe_translate(sql, tuple(params or ()))
    return cursor.execute(sql, params)
```

Then replace `cursor.execute(sql, params)` → `dbq(cursor, sql, params)` app-wide.
- **Today (MySQL):** identical behaviour (pure pass-through).
- **Production (SQL Server):** everything adapts in one place.

Chosen over the alternatives because:
- **vs. per-query rewrites:** unmaintainable across 185 call sites.
- **vs. a symbolic table-name registry:** a large rewrite; the translator already
  keeps code readable (MySQL-flavoured) with one place to fix dialect quirks.
- **vs. an auto-translating cursor/back-end wrapper:** more "magic", harder to test and
  reason about; an explicit `dbq()` is greppable and lint-able.

---

## 4. Phased plan

Each phase is independently shippable and verified on MySQL (no behaviour change) before moving on.

### Phase 0 — Prep & baseline (½ day)
- [ ] Stand up a SQL Server instance (staging) from `database/script_mssql.sql`.
- [ ] Confirm the app login's **default schema is `dbo`** (so bare `Mst_*`/`Mstx_*`
      resolve). If not, note it for Phase 2.
- [ ] Get `tests/test_mssql_connections.py` green against staging.
- [ ] Snapshot current behaviour: capture a few masters/listings API responses on
      MySQL to diff against later.

### Phase 1 — Introduce the choke point (1 day)
- [ ] Add `dbq(cursor, sql, params)` to `chatbot/db/sql.py`.
- [ ] Mechanically convert `chatbot/views.py` (183 sites), `auth_backend.py` (1),
      `health.py` (1) from `*.execute(` → `dbq(*, …)`. Scriptable (function-scoped
      string transform + `ast.parse` validation), the same technique used to wire the
      audit trail.
- [ ] **Verify on MySQL:** full smoke test of masters + listings + login + health +
      audit. Zero behaviour change expected.

### Phase 2 — Complete the translator rules (½ day)
- [ ] If the login default schema is **not** `dbo`: add a rule so `Mst_`/`Mstx_`
      (and any other bare legacy prefixes the app uses) → `dbo.Mst_`/`dbo.Mstx_`.
- [ ] Audit `script_mssql.sql` for every table the app references (see §2.1) and
      confirm each is reachable under the translator's rules.
- [ ] Add unit tests in `tests/` for `maybe_translate` covering each app table name
      and each dialect feature actually used (grep shows ~64 uses of
      `LIMIT/NOW/CURDATE/DATE_FORMAT/DATEDIFF/COALESCE` in views alone).

### Phase 3 — Run the app on SQL Server (1–2 days)
- [ ] Point `USE_MSSQL=true` at staging; run the masters CRUD, listings, exports,
      login, permissions, and audit end-to-end.
- [ ] Fix edge cases surfaced (identifier quoting, implicit CASTs, `TOP` vs `FETCH`,
      empty-result handling, `cursor.lastrowid` on auto-increment tables — note SQL
      Server needs `SCOPE_IDENTITY()`/`OUTPUT`; masters that use `MAX(id)+1` are fine,
      but `travel_eligibility`/`reporting_structure` use `lastrowid`).
- [ ] Re-run the Phase 0 response diffs — MySQL vs SQL Server outputs should match.

### Phase 4 — Guard rails (½ day)
- [ ] Add a test that **fails if any app module outside `chatbot/db/` contains a raw
      `\.execute\(` not going through `dbq`** (regex scan). Prevents drift.
- [ ] Document the rule in `CLAUDE.md` / contributing notes: "all raw SQL goes through
      `dbq()`; new masters keep using the audit helpers (already translator-aware)."

### Phase 5 — Cutover
- [ ] Production `.env`: `USE_MYSQL=false`, `USE_MSSQL=true`, ODBC driver + creds.
- [ ] Run Django migrations against the SQL Server **chathistory** DB (the `cb_*`
      tables incl. `cb_audit_log`) — `manage.py migrate --database=chathistory`.
- [ ] Smoke test + monitor the audit trail (it captures login/permission/master
      activity, a good post-cutover health signal).

---

## 5. Known edge cases / watch list

- **Auto-increment inserts:** `travel_eligibility` & `reporting_structure` read
  `cursor.lastrowid`. On SQL Server use `SELECT SCOPE_IDENTITY()` or an `OUTPUT` clause.
  All other masters use `COALESCE(MAX(id),0)+1` (portable).
- **`NOW()` in INSERTs** (competency, travel, reporting, job descriptions): handled by
  the translator once routed through it — another reason Phase 1 matters.
- **Default schema assumption:** the whole `dbo.Mst_*` story hinges on the login's
  default schema. Verify in Phase 0.
- **Reserved words / bracket-quoting:** translator handles known aliases; watch for new
  ones as queries are added.
- **UTF-8 / collation:** validate non-ASCII (e.g. the `·` used in `cb_menu.menu_group`)
  round-trips under the SQL Server collation.

---

## 6. Effort estimate

| Phase | Est. |
|---|---|
| 0 Prep & baseline | ½ day |
| 1 Choke point + convert call sites | 1 day |
| 2 Complete translator rules + tests | ½ day |
| 3 Run on SQL Server, fix edge cases | 1–2 days |
| 4 Guard rails | ½ day |
| 5 Cutover | ½ day |
| **Total** | **~4–5 days** |

The bulk of value lands in **Phase 1** (the choke point), which is a safe no-op on MySQL.

---

## 7. Bottom line

The strain is **not** the table names — it's that raw SQL bypasses the translator that
already exists. Funnel everything through `maybe_translate` via `dbq()`, confirm the
`dbo` default schema, and add a regression test. Everything else is edge-case cleanup.

The audit trail is already ahead of this curve and needs nothing further.

# SQL Server Migration Plan

**Status:** Phase 1 & 4 done, Phase 2 mostly done · **Owner:** _TBD_ · **Last updated:** 2026-08-14

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
- `Mst_TableName / Mstx_TableName → dbo.Mst_TableName / dbo.Mstx_TableName`
  (explicit table list — **added 2026-08-14**, see Phase 2)
- `CURDATE()/NOW() → CAST(GETDATE() AS DATE)/GETDATE()`
- `DATE(x)`, `DATE_FORMAT(...)`, `DATE_SUB/ADD → DATEADD`, `DATEDIFF` arg flip
- `IF() → IIF()`, `col IS [NOT] NULL → CASE …`, `CAST(x AS CHAR) → VARCHAR(50)`
- reserved-word aliases `AS open/type/key → AS [open]/…`
- `LIMIT n` / `LIMIT %s [OFFSET %s]` → `OFFSET … ROWS FETCH NEXT … ROWS ONLY`

### 2.3 The gap (the actual landmine) — ✅ closed 2026-08-14
Previously only the **analytics layer** routed through the translator; everything
else ran raw SQL that bypassed it. **Fixed in Phase 1** — every raw query now goes
through `dbq()` (which calls `maybe_translate` internally):

| Module | raw `.execute(` calls | routed through translator? |
|---|---|---|
| `chatbot/views.py` | 183 | ✅ yes (via `dbq()`) |
| `chatbot/auth_backend.py` | 1 | ✅ yes (via `dbq()`) |
| `chatbot/audit.py` | 1 | ✅ yes (via `dbq()`) |
| `chatbot/analytics/tools.py` | 1 | ✅ yes (via its own `_query()`, pre-existing) |
| `chatbot/health.py` / `chatbot/db/connection.py` | 2 | N/A — SQLAlchemy `text()` pings, not dialect-sensitive |

`tests/test_no_raw_sql.py` now enforces this stays true (see Phase 4).

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

**One choke point.** Introduce a thin helper and funnel *all* raw SQL through it —
**implemented** in `chatbot/db/sql.py`:

```python
def dbq(cursor, sql, params=None):
    if params is None:                    # preserve execute(sql)'s no-params path —
        sql, _ = maybe_translate(sql, ())  # avoids %-substitution on literal '%'
        return cursor.execute(sql)         # (e.g. DATE_FORMAT format strings)
    sql, params = maybe_translate(sql, tuple(params))
    return cursor.execute(sql, params)
```

(The `params is None` branch matters: 37 of the 184 call sites pass no params at
all, and some raw SQL contains literal `%` that isn't a bind placeholder — routing
those through `cursor.execute(sql, ())` instead of `cursor.execute(sql)` risks
Python's %-formatting choking on them.)

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
- [x] Confirmed which schema the app's `Mst_*`/`Mstx_*` tables live in
      (`dbo`, verified against `script_mssql.sql`) — handled explicitly in Phase 2,
      so the app no longer *depends on* the login's default schema at all.
- [ ] Get `tests/test_mssql_connections.py` green against staging.
- [ ] Snapshot current behaviour: capture a few masters/listings API responses on
      MySQL to diff against later.

### Phase 1 — Introduce the choke point (1 day) ✅ done 2026-08-14
- [x] Added `dbq(cursor, sql, params=None)` to `chatbot/db/sql.py`.
- [x] Converted `chatbot/views.py` (183 sites: 160 `cursor.execute(` + 23
      `cur.execute(`) and `chatbot/auth_backend.py` (1 site) from raw `.execute(` →
      `dbq(...)`. `chatbot/health.py`'s `conn.execute(text(...))` and
      `chatbot/db/connection.py`'s equivalent are **out of scope** — they're
      SQLAlchemy connectivity pings (`SELECT 1`), a different API shape with no
      dialect-sensitive SQL, not DB-API cursors.
- [x] `chatbot/audit.py :: snap()` also switched to `dbq()` (was calling
      `maybe_translate` + `cursor.execute()` manually — same effect, now consistent
      with the rest of the app).
- [x] **Verified on MySQL:** logged in (exercises the converted `auth_backend.py`
      path), full create→edit→delete round-trips on multiple masters, listings
      list APIs, a listings export, and the audit trail's own `snap()` — all
      produced identical results to before. Zero behaviour change, as expected.

### Phase 2 — Complete the translator rules (½ day) — mostly done 2026-08-14
- [x] Added an **explicit `Mst_`/`Mstx_` → `dbo.Mst_`/`dbo.Mstx_` rule**
      (`_DBO_TABLES` in `chatbot/db/sql.py`), rather than relying on / verifying the
      login's default schema. Deliberately **not** a casing-based pattern like the
      `eos_` rule — `Mst_user` is lowercase after the prefix (unlike the PascalCase
      `eos_` tables), so a pattern rule would have silently missed exactly the
      most-used table. Instead the 14 exact `Mst_*`/`Mstx_*` table names the app
      references are listed explicitly and matched as whole tokens.
      **If a new bare `Mst_*`/`Mstx_*` table gets queried later, add it to
      `_DBO_TABLES` — it will NOT auto-translate otherwise.**
- [x] Confirmed all 14 against `database/script_mssql.sql` — every one is `[dbo]`.
- [x] Verified translation output directly (no SQL Server connection needed —
      `translate_mssql()` is pure and testable standalone): `Mst_user →
      dbo.Mst_user`, `eos_Mst_Rig → eos.Mst_Rig`, `Mst_Rig_Subtype →
      dbo.Mst_Rig_Subtype` (confirmed no collision with the `eos_Mst_Rig` rule),
      and a mixed query (JOIN across both schemas + LIMIT/OFFSET) — all correct.
- [ ] Add unit tests in `tests/` for `maybe_translate` covering each app table name
      and each dialect feature actually used (grep shows ~64 uses of
      `LIMIT/NOW/CURDATE/DATE_FORMAT/DATEDIFF/COALESCE` in views alone). The ad-hoc
      verification above should become a real test file.

### Phase 3 — Run the app on SQL Server (1–2 days)
- [ ] Point `USE_MSSQL=true` at staging; run the masters CRUD, listings, exports,
      login, permissions, and audit end-to-end.
- [ ] Fix edge cases surfaced (identifier quoting, implicit CASTs, `TOP` vs `FETCH`,
      empty-result handling, `cursor.lastrowid` on auto-increment tables — note SQL
      Server needs `SCOPE_IDENTITY()`/`OUTPUT`; masters that use `MAX(id)+1` are fine,
      but `travel_eligibility`/`reporting_structure` use `lastrowid`).
- [ ] Re-run the Phase 0 response diffs — MySQL vs SQL Server outputs should match.

### Phase 4 — Guard rails (½ day) ✅ done 2026-08-14
- [x] `tests/test_no_raw_sql.py` — AST-based scan that **fails if any app module
      outside the translator's own choke points contains a raw `<name>.execute(...)`
      DB-API call**. Run: `python tests/test_no_raw_sql.py`. Correctly allows
      `chatbot/db/sql.py::dbq()` and `chatbot/analytics/tools.py::_query()` (the two
      legitimate choke points), and SQLAlchemy's `conn.execute(text(...))` pings
      (structurally different API, no dialect-sensitive SQL). Currently passes clean.
- [ ] Wire this into CI once one exists.
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

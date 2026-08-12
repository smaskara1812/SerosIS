# SerosIS — Internal Web Application

SerosIS is a Django-based internal web application built for Seros, an oil rig service company. It provides an RBAC-controlled admin portal with master data forms and listing pages that read from the live Seros operational database.

---

## Technology Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Language | Python | 3.11.15 |
| Web Framework | Django | 5.2.15 |
| Database (Ops) | MySQL / MS SQL Server | — |
| Database (App) | MySQL (`serosis`) | — |
| ORM | Django ORM (multi-database) | — |
| Frontend | Plain HTML / CSS / JS (no framework) | — |
| Dev DB Driver | PyMySQL | latest |
| Prod DB Driver | pyodbc + mssql-django | latest |

---

## Project Structure

```
serosIS/
├── chatbot/                    # Main Django app
│   ├── auth_backend.py         # Custom authentication backend
│   ├── context_processors.py   # Nav items + permission injection
│   ├── db/                     # DB connection config helpers
│   ├── migrations/             # Django migrations (chathistory DB only)
│   ├── models.py               # App models (cb_* tables)
│   ├── permissions.py          # RBAC: get_user_access, require_permission
│   ├── urls.py                 # All URL routes
│   ├── views.py                # All view functions and API handlers
│   └── templates/chatbot/
│       ├── base.html           # Shared layout + sidebar nav
│       ├── login.html
│       ├── admin/
│       │   └── user_rights.html       # Admin: user permission grid
│       ├── listings/
│       │   ├── index.html             # Listings index cards
│       │   ├── incidents.html
│       │   ├── hazard_cards.html
│       │   ├── employees.html
│       │   ├── staff.html
│       │   ├── crew_rotations.html
│       │   ├── invoices.html
│       │   ├── certificates.html
│       │   └── users.html             # Mst_user listing
│       └── masters/
│           ├── index.html             # Masters index cards
│           ├── rigs.html
│           ├── operator.html
│           ├── contractor.html
│           ├── cost_centre.html
│           ├── cost_centre_type.html
│           ├── email_notification_type.html
│           └── cert_institute.html
├── serosIS/                    # Django project config
│   ├── settings.py
│   ├── urls.py
│   └── db_router.py            # Multi-database routing logic
├── manage.py
├── requirements.txt
└── .env                        # Environment variables (not committed)
```

---

## Database Architecture

SerosIS uses **two separate databases** via Django's multi-database support.

### `default` — Seros Operational Database (`seros_data`)
- The live 518-table Seros EOS database
- **Read-only** in the current phase — all listing and master form data is read from here
- Master form saves (INSERT / UPDATE) write back to this database
- No Django migrations run against this DB
- Tables accessed include: `Mst_user`, `eos_Mst_Rig`, `eos_Mst_Operator`, `eos_Mst_Contractor`, `eos_Mst_Cost_Centre`, `eos_Mst_Cost_Centre_Type`, `eos_Email_Notification_Type`, `eos_Mst_Cert_Institute`, `Mst_Department`, `Mst_Location`, `Mst_Country`, and all listing-related tables

### `chathistory` — Application Database (`serosis`)
- Stores all application-managed data: Django auth users, sessions, RBAC permissions, and nav menu definitions
- All Django migrations run here
- Routed via `ChatHistoryRouter` in `serosIS/db_router.py`

| Table | Purpose |
|-------|---------|
| `auth_user` | Django user accounts |
| `cb_user_profile` | App admin flag per user |
| `cb_user_permissions` | Per-user, per-menu-key permission flags |
| `cb_menu` | Menu/permission registry (replaces hardcoded dict) |
| `cb_conversations` | (Reserved) |
| `cb_messages` | (Reserved) |

### Database Router Rules

```
auth / contenttypes / sessions / chatbot app  →  chathistory
everything else                               →  default (ops DB)
```

Migrations only run on `chathistory`. The ops DB is never migrated.

---

## Authentication

Authentication is handled by a custom backend in `chatbot/auth_backend.py`.

**Login flow:**
1. Look up the login ID in `seros_data.Mst_user` (all rows for that login ID)
2. If an **active** row is found (`USER_ACTIVE = 'Y'`) → validate password → allow login
3. If only an **inactive** row is found → return Django user with `is_active=False` → login page shows "This account is inactive"
4. If not found in `Mst_user` → fall through to Django's `ModelBackend` (handles superusers)

**Password:** Currently a single shared default password (`seros2026`). Designed as an AD swap-point — replacing `_fetch_mst_users` + password check with an Active Directory call requires no other changes.

**Session caching:** User permissions are cached in the Django session on first load and invalidated on logout.

---

## RBAC (Role-Based Access Control)

Permissions are defined per menu item and stored in the `cb_menu` and `cb_user_permissions` tables.

### Menu Registry (`cb_menu`)

Each page/feature is registered as a row with a `menu_key` (e.g. `listings.incidents`, `masters.rigs`). Flags control which actions are available for that page:

| Flag | Meaning |
|------|---------|
| `view_available` | Page can be shown in nav |
| `add_available` | Add action available |
| `edit_available` | Edit action available |
| `delete_available` | Delete action available |
| `export_available` | Export action available |
| `upload_available` | Upload action available |

### User Permissions (`cb_user_permissions`)

One row per `(user_login_id, menu_key)` pair. Columns: `can_view`, `can_add`, `can_edit`, `can_delete`, `can_export`.

### App Admin

Users with `cb_user_profile.is_app_admin = True` bypass all permission checks and see everything.

### Enforcing Permissions in Views

```python
@require_permission("listings.incidents", "view")
def incidents_page(request):
    ...
```

`require_permission` returns a 403 page if the user lacks the specified action. The nav sidebar automatically hides items the user cannot view.

---

## Adding a New Page — Checklist

Every new page follows these 5 steps:

| Step | File | What to do |
|------|------|------------|
| 1 | MySQL (`serosis.cb_menu`) | INSERT one row with the `menu_key`, group, order, and available action flags |
| 2 | `chatbot/context_processors.py` → `_NAV_ITEMS` | Add one dict entry; `id` must match `menu_key` exactly |
| 3 | `chatbot/urls.py` | Add `path()` entries for the page and its API endpoint(s) |
| 4 | `chatbot/views.py` | Add page view (with `@require_permission`) and API view(s) |
| 5 | `chatbot/templates/chatbot/` | Create HTML template extending `chatbot/base.html` |

**cb_menu INSERT template:**
```sql
INSERT INTO serosis.cb_menu
  (menu_key, menu_label, menu_group, group_order, menu_order,
   view_available, add_available, edit_available, delete_available,
   export_available, upload_available, is_active, cr_dt, mod_dt)
VALUES
  ('listings.my_page', 'My Page', 'Listings', 2, <next_order>,
   1, 0, 0, 0, 0, 0, 1, NOW(), NOW());
```

Group orders: 1 = Overview, 2 = Listings, 3 = Masters, 4 = Tools

---

## Environment Variables

Stored in `.env` at the project root (not committed to version control).

| Variable | Purpose |
|----------|---------|
| `DJANGO_SECRET_KEY` | Django secret key |
| `DEBUG` | `True` for development, `False` for production |
| `DB_HOST` / `DB_PORT` / `DB_NAME` / `DB_USER` / `DB_PASSWORD` | Ops DB connection |
| `CHAT_DB_HOST` / `CHAT_DB_PORT` / `CHAT_DB_NAME` / `CHAT_DB_USER` / `CHAT_DB_PASSWORD` | App DB connection |

---

## Running Locally

**Requirements:** Python 3.11, MySQL (or MS SQL Server in production)

```bash
# 1. Create and activate virtual environment
python3.11 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up environment variables
cp .env.example .env
# edit .env with your DB credentials

# 4. Run migrations (chathistory DB only)
python manage.py migrate --database chathistory

# 5. Start development server
python manage.py runserver
```

---

## Current Pages

### Listings (read-only data views)

| Page | URL | Table(s) |
|------|-----|---------|
| Incidents | `/listings/incidents/` | `eos_Incident` |
| Hazard Cards | `/listings/hazard-cards/` | `eos_Hazard_Card` |
| Employees | `/listings/employees/` | `Mst_Employee` |
| Staff | `/listings/staff/` | `Mst_Staff` |
| Crew Rotations | `/listings/crew-rotations/` | `eos_Crew_Rotation` |
| Invoices | `/listings/invoices/` | `eos_Invoice` |
| Certificates | `/listings/certificates/` | `eos_Emp_Certificate` |
| System Users | `/listings/users/` | `Mst_user` |

### Masters (full CRUD forms)

| Page | URL | Table | Actions |
|------|-----|-------|---------|
| Rigs | `/masters/rigs/` | `eos_Mst_Rig` | Search / Add / Edit |
| Operators | `/masters/operator/` | `eos_Mst_Operator` | Add / Edit / Deactivate |
| Contractors | `/masters/contractor/` | `eos_Mst_Contractor` | Add / Edit / Delete |
| Cost Centres | `/masters/cost-centre/` | `eos_Mst_Cost_Centre` | Add / Edit / Deactivate |
| Cost Centre Types | `/masters/cost-centre-type/` | `eos_Mst_Cost_Centre_Type` | Add / Edit / Deactivate |
| Email Notification Types | `/masters/email-notification-types/` | `eos_Email_Notification_Type` | Add / Edit / Deactivate |
| Cert Institutes | `/masters/cert-institutes/` | `eos_Mst_Cert_Institute` | Add / Edit / Delete |

### Admin

| Page | URL | Purpose |
|------|-----|---------|
| User Rights | `/admin/user-rights/` | Assign per-user permissions across all menu items |

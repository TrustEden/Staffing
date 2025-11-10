# Healthcare Staffing Bridge App

Monolithic-but-modular project that unifies internal staffing and agency coordination. The backend ships with FastAPI + SQLAlchemy, Postgres schema, tiered shift visibility, conflict detection, and a seed React frontend scaffolded with Vite.

## Stack
- **Backend:** FastAPI, SQLAlchemy 2.0, Alembic-ready migrations, Postgres
- **Auth:** JWT access/refresh tokens (Passlib + python-jose)
- **Notifications:** In-app stored notifications with read state
- **Imports:** Pandas-based Excel/CSV parser with tiered release defaults
- **Frontend:** React 18 + Vite with routing + Axios client stub

## Directory Layout
```
backend/
  app/
    models.py              # SQLAlchemy ORM models
    schemas.py             # Pydantic v2 models
    routes/                # Auth, facilities, agencies, shifts, uploads, notifications, admin
    services/              # Auth, conflict checking, notifications, Excel parser, scheduler
    utils/constants.py     # Shared enums / settings
  config.py                # Settings via pydantic-settings
  main.py                  # FastAPI entrypoint
frontend/
  src/                     # React scaffold with dashboard placeholders
  package.json             # Vite project config
migrations/                # Reserved for Alembic
.database/
  init_db.sql              # Postgres DDL
  seeds.sql                # Sample seed data (uses pgcrypto)
docs/
  feature-map.md           # MVP and phase roadmap
  api-spec.md              # Endpoint overview
  schema-diagram.png       # Placeholder � generate via dbdiagram or similar
start.sh                   # Helper script to boot backend (Unix)
```

## Getting Started
1. **Backend**

   Setup:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   uvicorn main:app --reload
   ```
   Environment variables live in `.env`. Default database URL targets a local Postgres instance named `healthcare_staffing`.

2. **Database**
   ```bash
   createdb healthcare_staffing
   psql healthcare_staffing -f database/init_db.sql
   psql healthcare_staffing -f database/seeds.sql
   ```
   The seed data creates a platform admin (`superadmin@example.com` / `ChangeMe123!`) plus sample facility & agency admins. The password hashing uses Postgres `crypt()`.

3. **Frontend**

   Setup:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
   Vite proxy forwards `/api` requests to `http://localhost:8000`. Frontend runs on `http://localhost:5173`.

## Key Backend Use Cases
- **Facilities** create & manage shifts, upload schedules, add internal staff
- **Agencies** view partnered facilities and claims
- **Shift Lifecycle** supports tiered visibility, conflict detection, claim approvals, & notifications
- **Notifications** keep facility and agency admins informed; endpoints expose read/unread state
- **Excel/CSV Import** normalizes dates/times and auto-builds tiered release timestamps

## Testing & Next Steps
- Add Alembic migrations under `migrations/`
- Wire React views to backend when API stabilizes
- Integrate SMS/Email sending (Twilio/SendGrid) once credentials available
- Extend scheduler to a background worker (RQ/Celery) for automated tier releases

## Recent Updates

### SuperAdmin Dashboard Features (2025-10-26)
- **Company Creation Flow**: Added confirmation dialog before creating companies/agencies
  - Two-step process: form submission → review & confirm → create
  - Shows complete summary of company details and admin account

- **Relationship Management**: Enhanced with confirmation dialogs
  - All actions (approve, deny, unlink) now require confirmation
  - Contextual messaging for each action type
  - Unlink functionality added to "View Company Links" section

- **Company Statistics**: Fixed agency stats loading issue
  - Resolved SQLAlchemy join ambiguity error
  - Company info modal now displays correctly for both facilities and agencies
  - Shows employee count, total shifts, fill rate, and lock status

### Bug Fixes
- **Admin Routes (backend)**: Fixed `AmbiguousForeignKeysError` in `get_company_stats()` function
  - Explicit join conditions for queries involving `Claim` → `User` relationships
  - Affects agency statistics calculations (lines 181-195)
## Notes
- The backend auto-creates tables in dev mode (`APP_ENV=development`). Use Alembic for production migrations.
- `docs/schema-diagram.png` is a placeholder. Export an ERD from dbdiagram.io or Draw.io when finalizing the schema.
- Notifications currently persist to DB only; hook in websockets or 3rd-party push later.

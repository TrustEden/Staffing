# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Healthcare Staffing Bridge is a monolithic-but-modular FastAPI + React application that unifies internal healthcare staffing and agency coordination. Facilities manage shifts with tiered visibility, agencies claim shifts, and the system handles conflict detection, notifications, and approval workflows.

**Stack:**
- Backend: FastAPI, SQLAlchemy 2.0, Postgres, JWT auth (Passlib + python-jose)
- Frontend: React 18 + Vite, Axios client
- Background: RQ + Redis for async tasks, scheduled tier releases
- Testing: pytest with 108 tests, in-memory SQLite

## Windows Development Environment

This project is developed on Windows. Always use Windows commands (not Unix) when running shell commands.

## Common Commands

### Backend

**Setup:**
```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

**Run Development Server:**
```bash
cd backend
venv\Scripts\activate
set PYTHONPATH=.
uvicorn main:app --reload
```
Server runs on `http://localhost:8000`. API docs at `/docs`.

**Run Background Worker (for tiered release & scheduled tasks):**
```bash
cd backend
venv\Scripts\activate
set PYTHONPATH=D:\Connected-main
python -m backend.worker
```
Requires Redis running on `redis://localhost:6379`.

**Environment Variables:**
Backend reads `.env` from `backend/` directory. Key settings in `config.py`:
- `DATABASE_URL`: Postgres connection (default: `postgresql+psycopg2://postgres:postgres@localhost:5432/healthcare_staffing`)
- `JWT_SECRET`: Token signing secret
- `REDIS_URL`: Redis connection for RQ
- `APP_ENV`: `development`/`staging`/`production` (auto-creates tables in dev)

### Frontend

**Setup:**
```bash
cd frontend
npm install
```

**Run Development Server:**
```bash
cd frontend
npm run dev
```
Frontend runs on `http://localhost:5173`. Vite proxy forwards `/api` to backend.

**Build:**
```bash
cd frontend
npm run build
```

### Database

**Initialize Database:**
```bash
createdb healthcare_staffing
psql healthcare_staffing -f database\init_db.sql
psql healthcare_staffing -f database\seeds.sql
```

Seed data creates:
- Platform admin: username=`superadmin`, email=`superadmin@example.com`, password=`ChangeMe123!`
- Sample facility & agency admins (created via `create_superadmin.py` script)

**Create Superadmin:**
```bash
cd backend
venv\Scripts\activate
set PYTHONPATH=D:\Connected-main
python create_superadmin.py
```

### Testing

**Run All Tests:**
```bash
cd backend
venv\Scripts\activate
set PYTHONPATH=D:\Connected-main
python -m pytest tests\ -v
```

**Run Specific Test File:**
```bash
python -m pytest tests\test_auth.py -v
```

**Run Specific Test Class:**
```bash
python -m pytest tests\test_auth.py::TestAuthToken -v
```

**Run with Coverage:**
```bash
python -m pytest tests\ --cov=backend\app --cov-report=term-missing --cov-report=html
```

**Test Suite Overview:**
- 108 tests across 5 modules (auth, shifts, claims, notifications, admin)
- Uses pytest-asyncio for async endpoints
- In-memory SQLite for speed
- Fixtures in `tests/conftest.py` provide test users, companies, tokens
- See `backend/TESTING.md` for detailed test documentation

## Architecture

### Backend Structure

**Entry Point:** `backend/main.py` imports `create_app()` from `backend/app/__init__.py`.

**Core Modules:**
- `app/models.py`: SQLAlchemy ORM (Company, User, Shift, Claim, Notification, etc.)
- `app/schemas.py`: Pydantic v2 request/response models
- `app/database.py`: SQLAlchemy engine, session management
- `app/dependencies.py`: FastAPI dependencies (auth, DB session)
- `config.py`: Pydantic-settings configuration

**Routes (in `app/routes/`):**
- `auth_routes.py`: Register, login, refresh, /me
- `facility_routes.py`: Facility CRUD, staff management
- `agency_routes.py`: Agency CRUD, relationships
- `shift_routes.py`: Shift CRUD, cancel, list with visibility filtering
- `claim_routes.py`: Claim shifts, approve/deny, list claims
- `notification_routes.py`: List, mark read/unread
- `admin_routes.py`: Relationship management, company stats, pending claims
- `upload_routes.py`: Excel/CSV shift import with pandas

**Services (in `app/services/`):**
- `auth_service.py`: JWT token creation/validation, password hashing
- `notification_service.py`: Create & deliver in-app notifications
- `excel_parser.py`: Pandas-based Excel/CSV parser with tiered release defaults
- `shift_conflict_checker.py`: Detect overlapping shifts for same user
- `scheduler.py`: RQ-based scheduled tasks (tier releases, reminders)

**Background Tasks:**
- `app/tasks/shift_tasks.py`: RQ job definitions (process tier releases, send reminders)
- `worker.py`: RQ worker entrypoint (run with `python -m backend.worker`)

**Utilities:**
- `app/utils/constants.py`: Enums (UserRole, ShiftStatus, ShiftVisibility, etc.)
- `app/utils/id_generator.py`: Display ID generation for companies

### Key Domain Concepts

**Shift Visibility & Tiered Release:**
- `ShiftVisibility`: `internal` (facility only), `agency` (partnered agencies), `tiered` (auto-release to agencies at scheduled time)
- Tiered shifts have `tier_release_at` datetime; scheduler job makes them visible when time arrives
- Facilities create shifts; agencies claim; facility admins approve/deny

**Company Types & Roles:**
- `CompanyType`: `facility` or `agency`
- `UserRole`: `admin` (platform admin, no company), `staff` (facility staff), `agency_admin`, `agency_staff`
- Platform admins (role=`admin`) manage relationships, facility admins (role=`admin` with facility company) manage shifts, agencies claim shifts

**Claim Lifecycle:**
- Agency user claims shift → Claim status `pending` → Facility admin approves (status `approved`, auto-denies other claims) or denies (status `denied`)
- Each state change triggers notifications to relevant users

**Conflict Detection:**
- `shift_conflict_checker.py` validates no overlapping shifts for same user before creating shift or approving claim
- Checks date + time range overlap

**Notifications:**
- In-app only (stored in `notifications` table)
- Created on shift claim, approval, denial, cancellation
- Endpoints: list (with unread filter), mark read/unread, mark all read
- Future: hook in SMS/Email via Twilio/SendGrid (credentials in config)

### Frontend Structure

- React 18 + Vite scaffold with routing
- Dashboard placeholders for facility/agency/platform admin roles
- Axios client stubs for API calls
- Production frontend: wire to backend when API stabilizes

### Database Schema

**Core Tables:**
- `companies`: Facilities & agencies with `display_id`, `type`, `is_locked`
- `users`: Staff & admins with `role`, `company_id` (null for platform admin)
- `shifts`: Created by facilities, have `visibility`, `status`, `tier_release_at`
- `claims`: Agency users claim shifts, have `status` (pending/approved/denied)
- `notifications`: In-app messages with `is_read` flag
- `facility_agency_relationships`: Links facilities to agencies with `status` (pending/active/denied/revoked)
- `invitations`: (Future) Invitation-based onboarding

**Constraints & Indexes:**
- Unique constraints on `companies.display_id`, `users.username`
- Foreign keys with cascade deletes
- Check constraints on time ranges, status enums

### Authentication & Authorization

**JWT Flow:**
- `POST /api/auth/token` (OAuth2 password flow) returns access + refresh tokens
- Access token: 30min, Refresh token: 24hr (configurable in `config.py`)
- `Authorization: Bearer <access_token>` header required for protected endpoints
- `POST /api/auth/refresh` exchanges refresh token for new access token

**Role-Based Access Control:**
- Routes use `get_current_user()` dependency (from `dependencies.py`)
- Additional role checks in route handlers (e.g., `require_role(UserRole.ADMIN)`)
- Platform admins (role=`admin`, company_id=null): manage relationships, view all companies
- Facility admins (role=`admin`, company_id=facility): manage shifts, approve claims for their facility
- Agency admins (role=`agency_admin`): view partnered facilities, manage agency staff
- Staff (role=`staff` or `agency_staff`): claim shifts, view own claims

### Testing Architecture

**Fixtures (in `tests/conftest.py`):**
- `test_db()`: In-memory SQLite session (function scope)
- `client()`: FastAPI TestClient with DB override
- Token fixtures: `superadmin_token`, `facility_admin_token`, `agency_admin_token`, `agency_staff_token`
- Data fixtures: `sample_facility`, `sample_agency`, `sample_shift`, `active_relationship`, `sample_claim`

**Test Modules:**
- `test_auth.py` (19 tests): Login, refresh, registration, password hashing
- `test_shifts.py` (25 tests): CRUD, visibility, conflict detection, cancellation
- `test_claims.py` (22 tests): Claim lifecycle, duplicate prevention, auto-denial
- `test_notifications.py` (22 tests): List, mark read, event triggers
- `test_admin.py` (31 tests): Relationships, company stats, pending claims

**Running Tests:**
- Always set `PYTHONPATH=D:\Connected-main` before running pytest
- Use `-v` for verbose output, `--tb=long` for detailed tracebacks
- Use `--cov=backend\app` for coverage reports

## Development Workflow

1. **Tables Auto-Created in Dev:** When `APP_ENV=development`, `create_app()` runs `Base.metadata.create_all()` on startup. Use Alembic migrations for production.

2. **Seeding Data:** Use `database/seeds.sql` or `create_superadmin.py` for initial data.

3. **Background Worker:** Start Redis, then run `python -m backend.worker` to process scheduled tasks (tier releases, reminders). Without worker, tiered shifts won't auto-release.

4. **Excel Import:** `POST /api/uploads/shifts?facility_id=<uuid>` accepts Excel/CSV with columns: `Date`, `Start Time`, `End Time`, `Role`. Parser normalizes dates/times and sets `tier_release_at` based on `default_tiered_release_hours` (24h default).

5. **API Documentation:** FastAPI auto-generates OpenAPI docs at `/docs` and `/redoc`.

6. **Windows Paths:** Use backslashes (`\`) in paths, set environment variables with `set VAR=value` (not `export`).

## Known Issues & Future Work

- **Alembic Migrations:** Not yet configured. Add under `migrations/` for production schema management.
- **SMS/Email:** Twilio/SendGrid integration stubbed but not active (need credentials in `.env`).
- **WebSockets:** In-app notifications stored in DB only; consider WebSockets for real-time push.
- **Frontend Wiring:** React views are placeholders; wire to backend when API stabilizes.
- **Windows Batch Scripts:** README mentions `D:\Schedule\start_backend.bat` and `start_frontend.bat` but these are not in repo (user-specific).

## Recent Updates

**2025-10-26: SuperAdmin Dashboard Improvements**
- Added confirmation dialogs for company creation & relationship management
- Fixed `AmbiguousForeignKeysError` in `get_company_stats()` (lines 181-195 in `admin_routes.py`) with explicit join conditions for `Claim` → `User` relationships
- Company stats modal now correctly displays for both facilities and agencies

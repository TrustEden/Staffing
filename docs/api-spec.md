# API Specification (MVP)

Base URL: `/api`

## Auth
- `POST /auth/register` – create a user (platform admin only in production)
- `POST /auth/token` – obtain access/refresh tokens (OAuth2 password flow)
- `POST /auth/refresh` – refresh tokens using refresh token
- `GET /auth/me` – return current user profile

## Facilities
- `GET /facilities/` – list facilities visible to requester
- `POST /facilities/` – create facility (platform admin only)
- `GET /facilities/{facility_id}` – retrieve facility details
- `PATCH /facilities/{facility_id}` – update facility metadata
- `GET /facilities/{facility_id}/staff` – list staff for facility
- `POST /facilities/{facility_id}/staff` – add staff/admin to facility

## Agencies
- `GET /agencies/` – list agencies visible to requester
- `POST /agencies/` – create agency (platform admin only)
- `GET /agencies/{agency_id}` – retrieve agency details
- `PATCH /agencies/{agency_id}` – update agency metadata
- `GET /agencies/{agency_id}/staff` – list agency members
- `POST /agencies/{agency_id}/staff` – add agency admin/staff
- `GET /agencies/{agency_id}/relationships` – facilities with active relationship

## Shifts
- `POST /shifts/` – create shift (facility admin)
- `GET /shifts/` – list shifts filtered by visibility & role
- `GET /shifts/{shift_id}` – get shift detail
- `PATCH /shifts/{shift_id}` – update shift
- `POST /shifts/{shift_id}/cancel` – cancel shift & notify claimants
- `POST /shifts/{shift_id}/claims` – claim a shift (facility/agency staff)
- `GET /shifts/{shift_id}/claims` – list claims (facility admin)
- `POST /shifts/{shift_id}/claims/{claim_id}/approve` – approve claim (facility admin)
- `POST /shifts/{shift_id}/claims/{claim_id}/deny` – deny claim (facility admin)

## Uploads
- `POST /uploads/shifts?facility_id=UUID` – import shifts from Excel/CSV

## Notifications
- `GET /notifications/` – list notifications for current user
- `POST /notifications/{notification_id}/read` – mark single notification read/unread
- `POST /notifications/mark-all-read` – mark all notifications read

## Admin
- `GET /admin/relationships` – list facility/agency relationships
- `POST /admin/relationships` – create new relationship
- `PATCH /admin/relationships/{relationship_id}` – update relationship status
- `DELETE /admin/relationships/{relationship_id}` – remove relationship
- `GET /admin/claims/pending` – list pending claims (platform admin or facility admin scoped)

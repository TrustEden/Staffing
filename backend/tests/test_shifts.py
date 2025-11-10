"""Tests for shift management endpoints."""

from datetime import date, datetime, time, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app import models
from backend.app.utils.constants import ShiftStatus, ShiftVisibility


class TestCreateShift:
    """Tests for POST /api/shifts/ (create shift)."""

    def test_create_shift_success(
        self,
        client: TestClient,
        facility_admin_token: str,
        sample_facility: models.Company,
    ):
        """Test successful shift creation by facility admin."""
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        response = client.post(
            "/api/shifts/",
            headers={"Authorization": f"Bearer {facility_admin_token}"},
            json={
                "facility_id": str(sample_facility.id),
                "date": tomorrow,
                "start_time": "07:00:00",
                "end_time": "19:00:00",
                "role_required": "RN",
                "visibility": "agency",
                "notes": "Day shift, ICU",
                "is_premium": False,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["role_required"] == "RN"
        assert data["status"] == "open"
        assert data["visibility"] == "agency"
        assert "id" in data

    def test_create_shift_unauthorized_user(
        self,
        client: TestClient,
        agency_admin_token: str,
        sample_facility: models.Company,
    ):
        """Test that agency admin cannot create shift for facility."""
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        response = client.post(
            "/api/shifts/",
            headers={"Authorization": f"Bearer {agency_admin_token}"},
            json={
                "facility_id": str(sample_facility.id),
                "date": tomorrow,
                "start_time": "07:00:00",
                "end_time": "19:00:00",
                "role_required": "RN",
                "visibility": "agency",
            },
        )
        assert response.status_code == 403

    def test_create_shift_tiered_with_auto_release(
        self,
        client: TestClient,
        facility_admin_token: str,
        sample_facility: models.Company,
    ):
        """Test tiered shift creation with automatic release_at calculation."""
        tomorrow = (date.today() + timedelta(days=2)).isoformat()
        response = client.post(
            "/api/shifts/",
            headers={"Authorization": f"Bearer {facility_admin_token}"},
            json={
                "facility_id": str(sample_facility.id),
                "date": tomorrow,
                "start_time": "07:00:00",
                "end_time": "19:00:00",
                "role_required": "RN",
                "visibility": "tiered",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["visibility"] == "tiered"
        assert data["release_at"] is not None  # Should be auto-calculated

    def test_create_shift_no_auth(self, client: TestClient, sample_facility: models.Company):
        """Test that creating shift without auth token fails."""
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        response = client.post(
            "/api/shifts/",
            json={
                "facility_id": str(sample_facility.id),
                "date": tomorrow,
                "start_time": "07:00:00",
                "end_time": "19:00:00",
                "role_required": "RN",
                "visibility": "agency",
            },
        )
        assert response.status_code == 401

    def test_create_premium_shift(
        self,
        client: TestClient,
        facility_admin_token: str,
        sample_facility: models.Company,
    ):
        """Test creating a premium shift with premium notes."""
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        response = client.post(
            "/api/shifts/",
            headers={"Authorization": f"Bearer {facility_admin_token}"},
            json={
                "facility_id": str(sample_facility.id),
                "date": tomorrow,
                "start_time": "19:00:00",
                "end_time": "07:00:00",
                "role_required": "RN",
                "visibility": "agency",
                "is_premium": True,
                "premium_notes": "Night shift differential - $10/hr extra",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["is_premium"] is True
        assert "extra" in data["premium_notes"]


class TestListShifts:
    """Tests for GET /api/shifts/ (list shifts)."""

    def test_list_shifts_as_facility_admin(
        self,
        client: TestClient,
        facility_admin_token: str,
        sample_shift: models.Shift,
    ):
        """Test facility admin can see their facility's shifts."""
        response = client.get(
            "/api/shifts/",
            headers={"Authorization": f"Bearer {facility_admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        shift_ids = [s["id"] for s in data]
        assert str(sample_shift.id) in shift_ids

    def test_list_shifts_visibility_filtering(
        self,
        client: TestClient,
        test_db: Session,
        facility_admin_token: str,
        agency_staff_token: str,
        sample_facility: models.Company,
        facility_admin_user: models.User,
        sample_agency: models.Company,
        active_relationship: models.Relationship,
    ):
        """Test that visibility rules are enforced when listing shifts."""
        # Create internal shift
        internal_shift = models.Shift(
            facility_id=sample_facility.id,
            date=date.today() + timedelta(days=1),
            start_time=time(7, 0),
            end_time=time(19, 0),
            role_required="RN",
            visibility=ShiftVisibility.INTERNAL,
            posted_by_id=facility_admin_user.id,
            posted_at=datetime.now(timezone.utc),
        )
        test_db.add(internal_shift)

        # Create agency-visible shift
        agency_shift = models.Shift(
            facility_id=sample_facility.id,
            date=date.today() + timedelta(days=2),
            start_time=time(7, 0),
            end_time=time(19, 0),
            role_required="LPN",
            visibility=ShiftVisibility.AGENCY,
            posted_by_id=facility_admin_user.id,
            posted_at=datetime.now(timezone.utc),
        )
        test_db.add(agency_shift)
        test_db.commit()

        # Facility admin should see both
        response = client.get(
            "/api/shifts/",
            headers={"Authorization": f"Bearer {facility_admin_token}"},
        )
        assert response.status_code == 200
        facility_data = response.json()
        facility_shift_ids = [s["id"] for s in facility_data]
        assert str(internal_shift.id) in facility_shift_ids
        assert str(agency_shift.id) in facility_shift_ids

        # Agency staff should only see agency-visible shift
        response = client.get(
            "/api/shifts/",
            headers={"Authorization": f"Bearer {agency_staff_token}"},
        )
        assert response.status_code == 200
        agency_data = response.json()
        agency_shift_ids = [s["id"] for s in agency_data]
        assert str(internal_shift.id) not in agency_shift_ids
        assert str(agency_shift.id) in agency_shift_ids

    def test_list_shifts_filter_by_date(
        self,
        client: TestClient,
        test_db: Session,
        facility_admin_token: str,
        sample_facility: models.Company,
        facility_admin_user: models.User,
    ):
        """Test filtering shifts by date range."""
        # Create shifts on different dates
        today = date.today()
        shift1 = models.Shift(
            facility_id=sample_facility.id,
            date=today + timedelta(days=1),
            start_time=time(7, 0),
            end_time=time(19, 0),
            role_required="RN",
            visibility=ShiftVisibility.AGENCY,
            posted_by_id=facility_admin_user.id,
            posted_at=datetime.now(timezone.utc),
        )
        shift2 = models.Shift(
            facility_id=sample_facility.id,
            date=today + timedelta(days=5),
            start_time=time(7, 0),
            end_time=time(19, 0),
            role_required="RN",
            visibility=ShiftVisibility.AGENCY,
            posted_by_id=facility_admin_user.id,
            posted_at=datetime.now(timezone.utc),
        )
        test_db.add_all([shift1, shift2])
        test_db.commit()

        # Filter to only get shift1
        start = (today + timedelta(days=1)).isoformat()
        end = (today + timedelta(days=3)).isoformat()
        response = client.get(
            f"/api/shifts/?start_date={start}&end_date={end}",
            headers={"Authorization": f"Bearer {facility_admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        shift_ids = [s["id"] for s in data]
        assert str(shift1.id) in shift_ids
        assert str(shift2.id) not in shift_ids

    def test_list_shifts_filter_by_status(
        self,
        client: TestClient,
        facility_admin_token: str,
        sample_shift: models.Shift,
        test_db: Session,
    ):
        """Test filtering shifts by status."""
        # Change sample shift to approved
        sample_shift.status = ShiftStatus.APPROVED
        test_db.commit()

        # Filter for open shifts
        response = client.get(
            "/api/shifts/?status=open",
            headers={"Authorization": f"Bearer {facility_admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        shift_ids = [s["id"] for s in data]
        assert str(sample_shift.id) not in shift_ids

        # Filter for approved shifts
        response = client.get(
            "/api/shifts/?status=approved",
            headers={"Authorization": f"Bearer {facility_admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        shift_ids = [s["id"] for s in data]
        assert str(sample_shift.id) in shift_ids


class TestGetShift:
    """Tests for GET /api/shifts/{shift_id}."""

    def test_get_shift_success(
        self,
        client: TestClient,
        facility_admin_token: str,
        sample_shift: models.Shift,
    ):
        """Test getting a specific shift."""
        response = client.get(
            f"/api/shifts/{sample_shift.id}",
            headers={"Authorization": f"Bearer {facility_admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(sample_shift.id)
        assert data["role_required"] == sample_shift.role_required

    def test_get_shift_not_found(
        self, client: TestClient, facility_admin_token: str
    ):
        """Test getting non-existent shift returns 404."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.get(
            f"/api/shifts/{fake_id}",
            headers={"Authorization": f"Bearer {facility_admin_token}"},
        )
        assert response.status_code == 404

    def test_get_shift_forbidden_visibility(
        self,
        client: TestClient,
        test_db: Session,
        agency_staff_token: str,
        sample_facility: models.Company,
        facility_admin_user: models.User,
    ):
        """Test that agency cannot see internal shift."""
        # Create internal-only shift
        internal_shift = models.Shift(
            facility_id=sample_facility.id,
            date=date.today() + timedelta(days=1),
            start_time=time(7, 0),
            end_time=time(19, 0),
            role_required="RN",
            visibility=ShiftVisibility.INTERNAL,
            posted_by_id=facility_admin_user.id,
            posted_at=datetime.now(timezone.utc),
        )
        test_db.add(internal_shift)
        test_db.commit()

        response = client.get(
            f"/api/shifts/{internal_shift.id}",
            headers={"Authorization": f"Bearer {agency_staff_token}"},
        )
        assert response.status_code == 403


class TestUpdateShift:
    """Tests for PATCH /api/shifts/{shift_id}."""

    def test_update_shift_success(
        self,
        client: TestClient,
        facility_admin_token: str,
        sample_shift: models.Shift,
    ):
        """Test successful shift update."""
        response = client.patch(
            f"/api/shifts/{sample_shift.id}",
            headers={"Authorization": f"Bearer {facility_admin_token}"},
            json={"role_required": "LPN", "notes": "Updated notes"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["role_required"] == "LPN"
        assert data["notes"] == "Updated notes"

    def test_update_shift_unauthorized(
        self,
        client: TestClient,
        agency_admin_token: str,
        sample_shift: models.Shift,
    ):
        """Test that agency admin cannot update facility shift."""
        response = client.patch(
            f"/api/shifts/{sample_shift.id}",
            headers={"Authorization": f"Bearer {agency_admin_token}"},
            json={"role_required": "LPN"},
        )
        assert response.status_code == 403


class TestCancelShift:
    """Tests for POST /api/shifts/{shift_id}/cancel."""

    def test_cancel_shift_success(
        self,
        client: TestClient,
        facility_admin_token: str,
        sample_shift: models.Shift,
        test_db: Session,
    ):
        """Test successful shift cancellation."""
        response = client.post(
            f"/api/shifts/{sample_shift.id}/cancel",
            headers={"Authorization": f"Bearer {facility_admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"

    def test_cancel_shift_with_pending_claims(
        self,
        client: TestClient,
        facility_admin_token: str,
        sample_shift: models.Shift,
        sample_claim: models.Claim,
        test_db: Session,
    ):
        """Test cancelling shift denies all pending claims."""
        response = client.post(
            f"/api/shifts/{sample_shift.id}/cancel",
            headers={"Authorization": f"Bearer {facility_admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"

        # Verify claim was denied
        test_db.refresh(sample_claim)
        assert sample_claim.status.value == "denied"
        assert "cancelled" in sample_claim.denial_reason.lower()


class TestShiftConflictDetection:
    """Tests for shift conflict detection during claims."""

    def test_no_conflict_different_dates(
        self,
        client: TestClient,
        test_db: Session,
        agency_staff_token: str,
        agency_staff_user: models.User,
        sample_facility: models.Company,
        facility_admin_user: models.User,
        active_relationship: models.Relationship,
    ):
        """Test no conflict when shifts are on different dates."""
        # Create first shift and claim it
        shift1 = models.Shift(
            facility_id=sample_facility.id,
            date=date.today() + timedelta(days=1),
            start_time=time(7, 0),
            end_time=time(19, 0),
            role_required="RN",
            visibility=ShiftVisibility.AGENCY,
            posted_by_id=facility_admin_user.id,
            posted_at=datetime.now(timezone.utc),
        )
        test_db.add(shift1)
        test_db.commit()

        # Claim first shift
        response = client.post(
            f"/api/shifts/{shift1.id}/claims",
            headers={"Authorization": f"Bearer {agency_staff_token}"},
        )
        assert response.status_code == 201

        # Create second shift on different date
        shift2 = models.Shift(
            facility_id=sample_facility.id,
            date=date.today() + timedelta(days=2),  # Different date
            start_time=time(7, 0),
            end_time=time(19, 0),
            role_required="RN",
            visibility=ShiftVisibility.AGENCY,
            posted_by_id=facility_admin_user.id,
            posted_at=datetime.now(timezone.utc),
        )
        test_db.add(shift2)
        test_db.commit()

        # Should be able to claim second shift (different date)
        response = client.post(
            f"/api/shifts/{shift2.id}/claims",
            headers={"Authorization": f"Bearer {agency_staff_token}"},
        )
        assert response.status_code == 201

    def test_conflict_overlapping_times(
        self,
        client: TestClient,
        test_db: Session,
        agency_staff_token: str,
        agency_staff_user: models.User,
        sample_facility: models.Company,
        facility_admin_user: models.User,
        active_relationship: models.Relationship,
    ):
        """Test conflict detection for overlapping shifts on same date."""
        same_date = date.today() + timedelta(days=1)

        # Create and claim first shift (7am - 7pm)
        shift1 = models.Shift(
            facility_id=sample_facility.id,
            date=same_date,
            start_time=time(7, 0),
            end_time=time(19, 0),
            role_required="RN",
            visibility=ShiftVisibility.AGENCY,
            posted_by_id=facility_admin_user.id,
            posted_at=datetime.now(timezone.utc),
        )
        test_db.add(shift1)
        test_db.commit()

        # Claim first shift and approve it
        from backend.app.utils.constants import ClaimStatus
        claim1 = models.Claim(
            shift_id=shift1.id,
            user_id=agency_staff_user.id,
            status=ClaimStatus.APPROVED,
            claimed_at=datetime.now(timezone.utc),
            approved_by_id=facility_admin_user.id,
        )
        test_db.add(claim1)
        shift1.status = ShiftStatus.APPROVED
        test_db.commit()

        # Create overlapping shift (12pm - 8pm) on same date
        shift2 = models.Shift(
            facility_id=sample_facility.id,
            date=same_date,
            start_time=time(12, 0),
            end_time=time(20, 0),
            role_required="RN",
            visibility=ShiftVisibility.AGENCY,
            posted_by_id=facility_admin_user.id,
            posted_at=datetime.now(timezone.utc),
        )
        test_db.add(shift2)
        test_db.commit()

        # Attempt to claim overlapping shift should fail
        response = client.post(
            f"/api/shifts/{shift2.id}/claims",
            headers={"Authorization": f"Bearer {agency_staff_token}"},
        )
        assert response.status_code == 409  # Conflict
        assert "conflict" in response.json()["detail"].lower()

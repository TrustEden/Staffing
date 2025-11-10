"""Tests for claim management endpoints."""

from datetime import date, datetime, time, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app import models
from backend.app.utils.constants import ClaimStatus, ShiftStatus, ShiftVisibility


class TestClaimShift:
    """Tests for POST /api/shifts/{shift_id}/claims (claim shift)."""

    def test_claim_shift_success(
        self,
        client: TestClient,
        agency_staff_token: str,
        sample_shift: models.Shift,
        active_relationship: models.Relationship,
    ):
        """Test successful shift claim by agency staff."""
        response = client.post(
            f"/api/shifts/{sample_shift.id}/claims",
            headers={"Authorization": f"Bearer {agency_staff_token}"},
        )
        assert response.status_code == 201
        data = response.json()
        assert "claim" in data
        claim = data["claim"]
        assert claim["shift_id"] == str(sample_shift.id)
        assert claim["status"] == "pending"

    def test_claim_shift_duplicate_prevention(
        self,
        client: TestClient,
        agency_staff_token: str,
        sample_shift: models.Shift,
        sample_claim: models.Claim,
    ):
        """Test that user cannot claim same shift twice."""
        # sample_claim already has the agency staff claiming the shift
        response = client.post(
            f"/api/shifts/{sample_shift.id}/claims",
            headers={"Authorization": f"Bearer {agency_staff_token}"},
        )
        assert response.status_code == 409
        assert "already claimed" in response.json()["detail"].lower()

    def test_claim_shift_not_visible(
        self,
        client: TestClient,
        test_db: Session,
        agency_staff_token: str,
        sample_facility: models.Company,
        facility_admin_user: models.User,
    ):
        """Test that agency staff cannot claim internal-only shift."""
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
        test_db.commit()

        response = client.post(
            f"/api/shifts/{internal_shift.id}/claims",
            headers={"Authorization": f"Bearer {agency_staff_token}"},
        )
        assert response.status_code == 403

    def test_claim_cancelled_shift(
        self,
        client: TestClient,
        test_db: Session,
        agency_staff_token: str,
        sample_shift: models.Shift,
    ):
        """Test that user cannot claim cancelled shift."""
        sample_shift.status = ShiftStatus.CANCELLED
        test_db.commit()

        response = client.post(
            f"/api/shifts/{sample_shift.id}/claims",
            headers={"Authorization": f"Bearer {agency_staff_token}"},
        )
        assert response.status_code == 409
        assert "not available" in response.json()["detail"].lower()

    def test_claim_approved_shift(
        self,
        client: TestClient,
        test_db: Session,
        agency_staff_token: str,
        sample_shift: models.Shift,
    ):
        """Test that user cannot claim already approved shift."""
        sample_shift.status = ShiftStatus.APPROVED
        test_db.commit()

        response = client.post(
            f"/api/shifts/{sample_shift.id}/claims",
            headers={"Authorization": f"Bearer {agency_staff_token}"},
        )
        assert response.status_code == 409
        assert "not available" in response.json()["detail"].lower()

    def test_claim_shift_updates_shift_status(
        self,
        client: TestClient,
        test_db: Session,
        agency_staff_token: str,
        sample_shift: models.Shift,
        active_relationship: models.Relationship,
    ):
        """Test that claiming a shift changes its status to pending."""
        # Reset shift to open
        sample_shift.status = ShiftStatus.OPEN
        test_db.commit()

        response = client.post(
            f"/api/shifts/{sample_shift.id}/claims",
            headers={"Authorization": f"Bearer {agency_staff_token}"},
        )
        assert response.status_code == 201

        test_db.refresh(sample_shift)
        assert sample_shift.status == ShiftStatus.PENDING


class TestListShiftClaims:
    """Tests for GET /api/shifts/{shift_id}/claims."""

    def test_list_shift_claims_as_facility_admin(
        self,
        client: TestClient,
        facility_admin_token: str,
        sample_shift: models.Shift,
        sample_claim: models.Claim,
    ):
        """Test facility admin can view claims for their shifts."""
        response = client.get(
            f"/api/shifts/{sample_shift.id}/claims",
            headers={"Authorization": f"Bearer {facility_admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        claim_ids = [c["id"] for c in data]
        assert str(sample_claim.id) in claim_ids

    def test_list_shift_claims_unauthorized(
        self,
        client: TestClient,
        agency_admin_token: str,
        sample_shift: models.Shift,
        sample_claim: models.Claim,
    ):
        """Test that agency admin from different agency cannot view claims."""
        # Create another agency
        # Agency admin from different agency shouldn't see claims
        response = client.get(
            f"/api/shifts/{sample_shift.id}/claims",
            headers={"Authorization": f"Bearer {agency_admin_token}"},
        )
        assert response.status_code == 403

    def test_list_shift_claims_includes_user_name(
        self,
        client: TestClient,
        facility_admin_token: str,
        sample_shift: models.Shift,
        sample_claim: models.Claim,
        agency_staff_user: models.User,
    ):
        """Test that claim list includes user names."""
        response = client.get(
            f"/api/shifts/{sample_shift.id}/claims",
            headers={"Authorization": f"Bearer {facility_admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        claim = next(c for c in data if c["id"] == str(sample_claim.id))
        assert claim["user_name"] == agency_staff_user.name


class TestApproveClaim:
    """Tests for POST /api/shifts/{shift_id}/claims/{claim_id}/approve."""

    def test_approve_claim_success(
        self,
        client: TestClient,
        facility_admin_token: str,
        sample_shift: models.Shift,
        sample_claim: models.Claim,
        test_db: Session,
    ):
        """Test successful claim approval."""
        response = client.post(
            f"/api/shifts/{sample_shift.id}/claims/{sample_claim.id}/approve",
            headers={"Authorization": f"Bearer {facility_admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "approved"
        assert data["approved_by_id"] is not None

        # Verify shift status changed to approved
        test_db.refresh(sample_shift)
        assert sample_shift.status == ShiftStatus.APPROVED

    def test_approve_claim_denies_others(
        self,
        client: TestClient,
        test_db: Session,
        facility_admin_token: str,
        sample_shift: models.Shift,
        sample_claim: models.Claim,
        auth_service,
        sample_agency: models.Company,
    ):
        """Test that approving one claim denies other pending claims."""
        # Create another agency staff user
        other_user = models.User(
            username="otherstaff",
            email="other@example.com",
            hashed_password=auth_service.hash_password("password123"),
            name="Other Staff",
            role="agency_staff",
            company_id=sample_agency.id,
            is_active=True,
        )
        test_db.add(other_user)
        test_db.commit()

        # Create another claim from different user
        other_claim = models.Claim(
            shift_id=sample_shift.id,
            user_id=other_user.id,
            status=ClaimStatus.PENDING,
            claimed_at=datetime.now(timezone.utc),
        )
        test_db.add(other_claim)
        test_db.commit()

        # Approve first claim
        response = client.post(
            f"/api/shifts/{sample_shift.id}/claims/{sample_claim.id}/approve",
            headers={"Authorization": f"Bearer {facility_admin_token}"},
        )
        assert response.status_code == 200

        # Verify other claim was denied
        test_db.refresh(other_claim)
        assert other_claim.status == ClaimStatus.DENIED
        assert "another claim" in other_claim.denial_reason.lower()

    def test_approve_claim_unauthorized(
        self,
        client: TestClient,
        agency_admin_token: str,
        sample_shift: models.Shift,
        sample_claim: models.Claim,
    ):
        """Test that agency admin cannot approve claims."""
        response = client.post(
            f"/api/shifts/{sample_shift.id}/claims/{sample_claim.id}/approve",
            headers={"Authorization": f"Bearer {agency_admin_token}"},
        )
        assert response.status_code == 403

    def test_approve_claim_not_found(
        self,
        client: TestClient,
        facility_admin_token: str,
        sample_shift: models.Shift,
    ):
        """Test approving non-existent claim returns 404."""
        fake_claim_id = "00000000-0000-0000-0000-000000000000"
        response = client.post(
            f"/api/shifts/{sample_shift.id}/claims/{fake_claim_id}/approve",
            headers={"Authorization": f"Bearer {facility_admin_token}"},
        )
        assert response.status_code == 404


class TestDenyClaim:
    """Tests for POST /api/shifts/{shift_id}/claims/{claim_id}/deny."""

    def test_deny_claim_success(
        self,
        client: TestClient,
        facility_admin_token: str,
        sample_shift: models.Shift,
        sample_claim: models.Claim,
        test_db: Session,
    ):
        """Test successful claim denial."""
        response = client.post(
            f"/api/shifts/{sample_shift.id}/claims/{sample_claim.id}/deny",
            headers={"Authorization": f"Bearer {facility_admin_token}"},
            json={"reason": "Insufficient experience"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "denied"
        assert data["denial_reason"] == "Insufficient experience"

    def test_deny_claim_shifts_back_to_open(
        self,
        client: TestClient,
        test_db: Session,
        facility_admin_token: str,
        sample_shift: models.Shift,
        sample_claim: models.Claim,
    ):
        """Test that denying all claims changes shift status back to open."""
        # Ensure it's the only claim
        response = client.post(
            f"/api/shifts/{sample_shift.id}/claims/{sample_claim.id}/deny",
            headers={"Authorization": f"Bearer {facility_admin_token}"},
            json={"reason": "Not available"},
        )
        assert response.status_code == 200

        # Verify shift status changed back to open
        test_db.refresh(sample_shift)
        assert sample_shift.status == ShiftStatus.OPEN

    def test_deny_claim_with_other_pending(
        self,
        client: TestClient,
        test_db: Session,
        facility_admin_token: str,
        sample_shift: models.Shift,
        sample_claim: models.Claim,
        auth_service,
        sample_agency: models.Company,
    ):
        """Test that shift stays pending when other claims remain."""
        # Create another agency staff user
        other_user = models.User(
            username="otherstaff2",
            email="other2@example.com",
            hashed_password=auth_service.hash_password("password123"),
            name="Other Staff 2",
            role="agency_staff",
            company_id=sample_agency.id,
            is_active=True,
        )
        test_db.add(other_user)
        test_db.commit()

        # Create another pending claim
        other_claim = models.Claim(
            shift_id=sample_shift.id,
            user_id=other_user.id,
            status=ClaimStatus.PENDING,
            claimed_at=datetime.now(timezone.utc),
        )
        test_db.add(other_claim)
        test_db.commit()

        # Deny first claim
        response = client.post(
            f"/api/shifts/{sample_shift.id}/claims/{sample_claim.id}/deny",
            headers={"Authorization": f"Bearer {facility_admin_token}"},
            json={"reason": "Not needed"},
        )
        assert response.status_code == 200

        # Verify shift stays pending (other claim still pending)
        test_db.refresh(sample_shift)
        assert sample_shift.status == ShiftStatus.PENDING

    def test_deny_claim_unauthorized(
        self,
        client: TestClient,
        agency_admin_token: str,
        sample_shift: models.Shift,
        sample_claim: models.Claim,
    ):
        """Test that agency admin cannot deny claims."""
        response = client.post(
            f"/api/shifts/{sample_shift.id}/claims/{sample_claim.id}/deny",
            headers={"Authorization": f"Bearer {agency_admin_token}"},
            json={"reason": "Not authorized"},
        )
        assert response.status_code == 403

    def test_deny_claim_without_reason(
        self,
        client: TestClient,
        facility_admin_token: str,
        sample_shift: models.Shift,
        sample_claim: models.Claim,
    ):
        """Test denying claim without reason (reason is optional)."""
        response = client.post(
            f"/api/shifts/{sample_shift.id}/claims/{sample_claim.id}/deny",
            headers={"Authorization": f"Bearer {facility_admin_token}"},
            json={},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "denied"


class TestListMyClaims:
    """Tests for GET /api/claims/me."""

    def test_list_my_claims_success(
        self,
        client: TestClient,
        agency_staff_token: str,
        sample_claim: models.Claim,
    ):
        """Test user can view their own claims."""
        response = client.get(
            "/api/claims/me",
            headers={"Authorization": f"Bearer {agency_staff_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        claim_ids = [c["id"] for c in data]
        assert str(sample_claim.id) in claim_ids

    def test_list_my_claims_includes_shift_details(
        self,
        client: TestClient,
        agency_staff_token: str,
        sample_claim: models.Claim,
        sample_shift: models.Shift,
    ):
        """Test that my claims includes shift details."""
        response = client.get(
            "/api/claims/me",
            headers={"Authorization": f"Bearer {agency_staff_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        claim = next(c for c in data if c["id"] == str(sample_claim.id))
        assert "shift" in claim
        assert claim["shift"]["id"] == str(sample_shift.id)
        assert claim["shift"]["role_required"] == sample_shift.role_required

    def test_list_my_claims_empty_for_new_user(
        self,
        client: TestClient,
        test_db: Session,
        auth_service,
        sample_agency: models.Company,
    ):
        """Test empty list for user with no claims."""
        # Create new user with no claims
        new_user = models.User(
            username="newstaff",
            email="new@example.com",
            hashed_password=auth_service.hash_password("password123"),
            name="New Staff",
            role="agency_staff",
            company_id=sample_agency.id,
            is_active=True,
        )
        test_db.add(new_user)
        test_db.commit()

        token, _ = auth_service.create_access_token(
            new_user.id, new_user.role, new_user.company_id
        )

        response = client.get(
            "/api/claims/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0

    def test_list_my_claims_only_shows_own_claims(
        self,
        client: TestClient,
        test_db: Session,
        agency_staff_token: str,
        sample_claim: models.Claim,
        auth_service,
        sample_agency: models.Company,
        sample_shift: models.Shift,
    ):
        """Test user only sees their own claims, not others'."""
        # Create another user with a claim
        other_user = models.User(
            username="otherstaff3",
            email="other3@example.com",
            hashed_password=auth_service.hash_password("password123"),
            name="Other Staff 3",
            role="agency_staff",
            company_id=sample_agency.id,
            is_active=True,
        )
        test_db.add(other_user)
        test_db.commit()

        # Create another shift for the other user to claim
        other_shift = models.Shift(
            facility_id=sample_shift.facility_id,
            date=date.today() + timedelta(days=3),
            start_time=time(7, 0),
            end_time=time(19, 0),
            role_required="LPN",
            visibility=ShiftVisibility.AGENCY,
            posted_by_id=sample_shift.posted_by_id,
            posted_at=datetime.now(timezone.utc),
        )
        test_db.add(other_shift)
        test_db.commit()

        other_claim = models.Claim(
            shift_id=other_shift.id,
            user_id=other_user.id,
            status=ClaimStatus.PENDING,
            claimed_at=datetime.now(timezone.utc),
        )
        test_db.add(other_claim)
        test_db.commit()

        # Original user should only see their own claim
        response = client.get(
            "/api/claims/me",
            headers={"Authorization": f"Bearer {agency_staff_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        claim_ids = [c["id"] for c in data]
        assert str(sample_claim.id) in claim_ids
        assert str(other_claim.id) not in claim_ids

"""Tests for admin endpoints."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app import models
from backend.app.utils.constants import ClaimStatus, CompanyType, RelationshipStatus


class TestListRelationships:
    """Tests for GET /api/admin/relationships."""

    def test_list_relationships_as_superadmin(
        self,
        client: TestClient,
        superadmin_token: str,
        active_relationship: models.Relationship,
    ):
        """Test platform admin can list all relationships."""
        response = client.get(
            "/api/admin/relationships",
            headers={"Authorization": f"Bearer {superadmin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        relationship_ids = [r["id"] for r in data]
        assert str(active_relationship.id) in relationship_ids

    def test_list_relationships_forbidden_for_facility_admin(
        self, client: TestClient, facility_admin_token: str
    ):
        """Test facility admin cannot list relationships."""
        response = client.get(
            "/api/admin/relationships",
            headers={"Authorization": f"Bearer {facility_admin_token}"},
        )
        assert response.status_code == 403

    def test_list_relationships_forbidden_for_agency_admin(
        self, client: TestClient, agency_admin_token: str
    ):
        """Test agency admin cannot list relationships."""
        response = client.get(
            "/api/admin/relationships",
            headers={"Authorization": f"Bearer {agency_admin_token}"},
        )
        assert response.status_code == 403

    def test_list_relationships_no_auth(self, client: TestClient):
        """Test listing relationships requires authentication."""
        response = client.get("/api/admin/relationships")
        assert response.status_code == 401


class TestCreateRelationship:
    """Tests for POST /api/admin/relationships."""

    def test_create_relationship_success(
        self,
        client: TestClient,
        test_db: Session,
        superadmin_token: str,
        sample_facility: models.Company,
    ):
        """Test creating a new relationship as platform admin."""
        # Create a new agency for this test
        new_agency = models.Company(
            display_id="AGN002",
            name="New Agency",
            type=CompanyType.AGENCY,
            address="789 New Street",
            contact_email="new@agency.com",
        )
        test_db.add(new_agency)
        test_db.commit()

        response = client.post(
            "/api/admin/relationships",
            headers={"Authorization": f"Bearer {superadmin_token}"},
            json={
                "facility_id": str(sample_facility.id),
                "agency_id": str(new_agency.id),
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["facility_id"] == str(sample_facility.id)
        assert data["agency_id"] == str(new_agency.id)
        assert data["status"] == "invited"

    def test_create_relationship_duplicate(
        self,
        client: TestClient,
        superadmin_token: str,
        active_relationship: models.Relationship,
    ):
        """Test that creating duplicate relationship fails."""
        response = client.post(
            "/api/admin/relationships",
            headers={"Authorization": f"Bearer {superadmin_token}"},
            json={
                "facility_id": str(active_relationship.facility_id),
                "agency_id": str(active_relationship.agency_id),
            },
        )
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"].lower()

    def test_create_relationship_invalid_facility(
        self,
        client: TestClient,
        superadmin_token: str,
        sample_agency: models.Company,
    ):
        """Test creating relationship with invalid facility ID."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.post(
            "/api/admin/relationships",
            headers={"Authorization": f"Bearer {superadmin_token}"},
            json={"facility_id": fake_id, "agency_id": str(sample_agency.id)},
        )
        assert response.status_code == 404

    def test_create_relationship_forbidden_for_facility_admin(
        self,
        client: TestClient,
        facility_admin_token: str,
        sample_facility: models.Company,
        sample_agency: models.Company,
    ):
        """Test facility admin cannot create relationships."""
        response = client.post(
            "/api/admin/relationships",
            headers={"Authorization": f"Bearer {facility_admin_token}"},
            json={
                "facility_id": str(sample_facility.id),
                "agency_id": str(sample_agency.id),
            },
        )
        assert response.status_code == 403


class TestUpdateRelationship:
    """Tests for PATCH /api/admin/relationships/{relationship_id}."""

    def test_update_relationship_status(
        self,
        client: TestClient,
        test_db: Session,
        superadmin_token: str,
        sample_facility: models.Company,
        sample_agency: models.Company,
        superadmin_user: models.User,
    ):
        """Test updating relationship status."""
        # Create invited relationship
        relationship = models.Relationship(
            facility_id=sample_facility.id,
            agency_id=sample_agency.id,
            status=RelationshipStatus.INVITED,
            invited_by_id=superadmin_user.id,
        )
        test_db.add(relationship)
        test_db.commit()

        # Update to active
        response = client.patch(
            f"/api/admin/relationships/{relationship.id}",
            headers={"Authorization": f"Bearer {superadmin_token}"},
            json={"status": "active"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "active"
        assert data["invite_accepted_at"] is not None

    def test_update_relationship_to_revoked(
        self,
        client: TestClient,
        superadmin_token: str,
        active_relationship: models.Relationship,
    ):
        """Test revoking an active relationship."""
        response = client.patch(
            f"/api/admin/relationships/{active_relationship.id}",
            headers={"Authorization": f"Bearer {superadmin_token}"},
            json={"status": "revoked"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "revoked"

    def test_update_relationship_not_found(
        self, client: TestClient, superadmin_token: str
    ):
        """Test updating non-existent relationship."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.patch(
            f"/api/admin/relationships/{fake_id}",
            headers={"Authorization": f"Bearer {superadmin_token}"},
            json={"status": "active"},
        )
        assert response.status_code == 404

    def test_update_relationship_forbidden_for_facility_admin(
        self,
        client: TestClient,
        facility_admin_token: str,
        active_relationship: models.Relationship,
    ):
        """Test facility admin cannot update relationships."""
        response = client.patch(
            f"/api/admin/relationships/{active_relationship.id}",
            headers={"Authorization": f"Bearer {facility_admin_token}"},
            json={"status": "revoked"},
        )
        assert response.status_code == 403


class TestDeleteRelationship:
    """Tests for DELETE /api/admin/relationships/{relationship_id}."""

    def test_delete_relationship_success(
        self,
        client: TestClient,
        test_db: Session,
        superadmin_token: str,
        sample_facility: models.Company,
        sample_agency: models.Company,
        superadmin_user: models.User,
    ):
        """Test deleting a relationship."""
        # Create relationship to delete
        relationship = models.Relationship(
            facility_id=sample_facility.id,
            agency_id=sample_agency.id,
            status=RelationshipStatus.INVITED,
            invited_by_id=superadmin_user.id,
        )
        test_db.add(relationship)
        test_db.commit()
        relationship_id = relationship.id

        response = client.delete(
            f"/api/admin/relationships/{relationship_id}",
            headers={"Authorization": f"Bearer {superadmin_token}"},
        )
        assert response.status_code == 204

        # Verify it was deleted
        deleted_rel = test_db.get(models.Relationship, relationship_id)
        assert deleted_rel is None

    def test_delete_relationship_not_found(
        self, client: TestClient, superadmin_token: str
    ):
        """Test deleting non-existent relationship."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.delete(
            f"/api/admin/relationships/{fake_id}",
            headers={"Authorization": f"Bearer {superadmin_token}"},
        )
        assert response.status_code == 404

    def test_delete_relationship_forbidden_for_facility_admin(
        self,
        client: TestClient,
        facility_admin_token: str,
        active_relationship: models.Relationship,
    ):
        """Test facility admin cannot delete relationships."""
        response = client.delete(
            f"/api/admin/relationships/{active_relationship.id}",
            headers={"Authorization": f"Bearer {facility_admin_token}"},
        )
        assert response.status_code == 403


class TestListPendingClaims:
    """Tests for GET /api/admin/claims/pending."""

    def test_list_pending_claims_as_superadmin(
        self,
        client: TestClient,
        superadmin_token: str,
        sample_claim: models.Claim,
    ):
        """Test platform admin can see all pending claims."""
        response = client.get(
            "/api/admin/claims/pending",
            headers={"Authorization": f"Bearer {superadmin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        claim_ids = [c["id"] for c in data]
        assert str(sample_claim.id) in claim_ids

    def test_list_pending_claims_as_facility_admin(
        self,
        client: TestClient,
        facility_admin_token: str,
        sample_claim: models.Claim,
    ):
        """Test facility admin can see pending claims for their facility."""
        response = client.get(
            "/api/admin/claims/pending",
            headers={"Authorization": f"Bearer {facility_admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        claim_ids = [c["id"] for c in data]
        assert str(sample_claim.id) in claim_ids

    def test_list_pending_claims_only_pending_status(
        self,
        client: TestClient,
        test_db: Session,
        superadmin_token: str,
        sample_shift: models.Shift,
        agency_staff_user: models.User,
    ):
        """Test that only pending claims are returned, not approved/denied."""
        # Create approved claim
        from datetime import date, datetime, time, timedelta, timezone

        approved_shift = models.Shift(
            facility_id=sample_shift.facility_id,
            date=date.today() + timedelta(days=5),
            start_time=time(7, 0),
            end_time=time(19, 0),
            role_required="RN",
            posted_by_id=sample_shift.posted_by_id,
            posted_at=datetime.now(timezone.utc),
        )
        test_db.add(approved_shift)
        test_db.commit()

        approved_claim = models.Claim(
            shift_id=approved_shift.id,
            user_id=agency_staff_user.id,
            status=ClaimStatus.APPROVED,
            claimed_at=datetime.now(timezone.utc),
        )
        test_db.add(approved_claim)
        test_db.commit()

        response = client.get(
            "/api/admin/claims/pending",
            headers={"Authorization": f"Bearer {superadmin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        claim_ids = [c["id"] for c in data]
        # Approved claim should not be in the list
        assert str(approved_claim.id) not in claim_ids

    def test_list_pending_claims_forbidden_for_agency_admin(
        self, client: TestClient, agency_admin_token: str
    ):
        """Test agency admin cannot list pending claims."""
        response = client.get(
            "/api/admin/claims/pending",
            headers={"Authorization": f"Bearer {agency_admin_token}"},
        )
        assert response.status_code == 403


class TestGetCompanyStats:
    """Tests for GET /api/admin/companies/{company_id}/stats."""

    def test_get_company_stats_facility(
        self,
        client: TestClient,
        test_db: Session,
        superadmin_token: str,
        sample_facility: models.Company,
        sample_shift: models.Shift,
        sample_claim: models.Claim,
        facility_admin_user: models.User,
    ):
        """Test getting statistics for a facility."""
        # Approve the claim to have filled shift
        sample_claim.status = ClaimStatus.APPROVED
        test_db.commit()

        response = client.get(
            f"/api/admin/companies/{sample_facility.id}/stats",
            headers={"Authorization": f"Bearer {superadmin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["company_id"] == str(sample_facility.id)
        assert data["name"] == sample_facility.name
        assert data["type"] == "facility"
        assert data["employee_count"] >= 1  # At least facility_admin_user
        assert data["total_shifts"] >= 1
        assert data["filled_shifts"] >= 1
        assert data["fill_rate"] > 0

    def test_get_company_stats_agency(
        self,
        client: TestClient,
        test_db: Session,
        superadmin_token: str,
        sample_agency: models.Company,
        sample_claim: models.Claim,
        agency_staff_user: models.User,
        agency_admin_user: models.User,
    ):
        """Test getting statistics for an agency."""
        # Approve the claim
        sample_claim.status = ClaimStatus.APPROVED
        test_db.commit()

        response = client.get(
            f"/api/admin/companies/{sample_agency.id}/stats",
            headers={"Authorization": f"Bearer {superadmin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["company_id"] == str(sample_agency.id)
        assert data["name"] == sample_agency.name
        assert data["type"] == "agency"
        assert data["employee_count"] >= 2  # agency_admin + agency_staff
        assert data["total_shifts"] >= 1  # Claims made by agency staff
        assert data["filled_shifts"] >= 1  # Approved claims

    def test_get_company_stats_not_found(
        self, client: TestClient, superadmin_token: str
    ):
        """Test getting stats for non-existent company."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.get(
            f"/api/admin/companies/{fake_id}/stats",
            headers={"Authorization": f"Bearer {superadmin_token}"},
        )
        assert response.status_code == 404

    def test_get_company_stats_forbidden_for_facility_admin(
        self,
        client: TestClient,
        facility_admin_token: str,
        sample_facility: models.Company,
    ):
        """Test facility admin cannot get company stats."""
        response = client.get(
            f"/api/admin/companies/{sample_facility.id}/stats",
            headers={"Authorization": f"Bearer {facility_admin_token}"},
        )
        assert response.status_code == 403


class TestLockCompany:
    """Tests for PATCH /api/admin/companies/{company_id}/lock."""

    def test_lock_company_success(
        self,
        client: TestClient,
        test_db: Session,
        superadmin_token: str,
        sample_facility: models.Company,
        facility_admin_user: models.User,
    ):
        """Test locking a company account."""
        response = client.patch(
            f"/api/admin/companies/{sample_facility.id}/lock",
            headers={"Authorization": f"Bearer {superadmin_token}"},
            json={"is_locked": True},
        )
        assert response.status_code == 200
        data = response.json()
        assert "locked" in data["message"].lower()

        # Verify company is locked
        test_db.refresh(sample_facility)
        assert sample_facility.is_locked is True

        # Verify users are deactivated
        test_db.refresh(facility_admin_user)
        assert facility_admin_user.is_active is False

    def test_unlock_company_success(
        self,
        client: TestClient,
        test_db: Session,
        superadmin_token: str,
        sample_facility: models.Company,
        facility_admin_user: models.User,
    ):
        """Test unlocking a company account."""
        # Lock first
        sample_facility.is_locked = True
        facility_admin_user.is_active = False
        test_db.commit()

        # Unlock
        response = client.patch(
            f"/api/admin/companies/{sample_facility.id}/lock",
            headers={"Authorization": f"Bearer {superadmin_token}"},
            json={"is_locked": False},
        )
        assert response.status_code == 200
        data = response.json()
        assert "unlocked" in data["message"].lower()

        # Verify company is unlocked
        test_db.refresh(sample_facility)
        assert sample_facility.is_locked is False

        # Verify users are activated
        test_db.refresh(facility_admin_user)
        assert facility_admin_user.is_active is True

    def test_lock_company_not_found(self, client: TestClient, superadmin_token: str):
        """Test locking non-existent company."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.patch(
            f"/api/admin/companies/{fake_id}/lock",
            headers={"Authorization": f"Bearer {superadmin_token}"},
            json={"is_locked": True},
        )
        assert response.status_code == 404

    def test_lock_company_forbidden_for_facility_admin(
        self,
        client: TestClient,
        facility_admin_token: str,
        sample_facility: models.Company,
    ):
        """Test facility admin cannot lock companies."""
        response = client.patch(
            f"/api/admin/companies/{sample_facility.id}/lock",
            headers={"Authorization": f"Bearer {facility_admin_token}"},
            json={"is_locked": True},
        )
        assert response.status_code == 403


class TestResetAdminPassword:
    """Tests for POST /api/admin/companies/{company_id}/reset-admin-password."""

    def test_reset_admin_password_success(
        self,
        client: TestClient,
        test_db: Session,
        superadmin_token: str,
        sample_facility: models.Company,
        facility_admin_user: models.User,
        auth_service,
    ):
        """Test resetting admin password."""
        new_password = "newSecurePassword123"
        response = client.post(
            f"/api/admin/companies/{sample_facility.id}/reset-admin-password",
            headers={"Authorization": f"Bearer {superadmin_token}"},
            json={"new_password": new_password},
        )
        assert response.status_code == 200
        data = response.json()
        assert "reset successfully" in data["message"].lower()
        assert data["admin_username"] == facility_admin_user.username

        # Verify password was changed
        test_db.refresh(facility_admin_user)
        assert auth_service.verify_password(new_password, facility_admin_user.hashed_password)

    def test_reset_admin_password_agency(
        self,
        client: TestClient,
        test_db: Session,
        superadmin_token: str,
        sample_agency: models.Company,
        agency_admin_user: models.User,
        auth_service,
    ):
        """Test resetting agency admin password."""
        new_password = "newAgencyPassword123"
        response = client.post(
            f"/api/admin/companies/{sample_agency.id}/reset-admin-password",
            headers={"Authorization": f"Bearer {superadmin_token}"},
            json={"new_password": new_password},
        )
        assert response.status_code == 200
        data = response.json()
        assert "reset successfully" in data["message"].lower()

        # Verify password was changed
        test_db.refresh(agency_admin_user)
        assert auth_service.verify_password(new_password, agency_admin_user.hashed_password)

    def test_reset_admin_password_company_not_found(
        self, client: TestClient, superadmin_token: str
    ):
        """Test resetting password for non-existent company."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.post(
            f"/api/admin/companies/{fake_id}/reset-admin-password",
            headers={"Authorization": f"Bearer {superadmin_token}"},
            json={"new_password": "newPassword123"},
        )
        assert response.status_code == 404

    def test_reset_admin_password_forbidden_for_facility_admin(
        self,
        client: TestClient,
        facility_admin_token: str,
        sample_facility: models.Company,
    ):
        """Test facility admin cannot reset passwords."""
        response = client.post(
            f"/api/admin/companies/{sample_facility.id}/reset-admin-password",
            headers={"Authorization": f"Bearer {facility_admin_token}"},
            json={"new_password": "newPassword123"},
        )
        assert response.status_code == 403

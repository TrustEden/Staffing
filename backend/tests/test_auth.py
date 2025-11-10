"""Tests for authentication endpoints."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app import models
from backend.app.schemas import UserCreate
from backend.app.services.auth_service import AuthService
from backend.app.utils.constants import UserRole


class TestAuthToken:
    """Tests for POST /api/auth/token (login)."""

    def test_login_success(
        self, client: TestClient, facility_admin_user: models.User
    ):
        """Test successful login with valid credentials."""
        response = client.post(
            "/api/auth/token",
            data={"username": "facilityadmin", "password": "password123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
        assert "refresh_expires_in" in data

    def test_login_invalid_username(self, client: TestClient):
        """Test login with non-existent username."""
        response = client.post(
            "/api/auth/token",
            data={"username": "nonexistent", "password": "password123"},
        )
        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]

    def test_login_invalid_password(
        self, client: TestClient, facility_admin_user: models.User
    ):
        """Test login with incorrect password."""
        response = client.post(
            "/api/auth/token",
            data={"username": "facilityadmin", "password": "wrongpassword"},
        )
        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]

    def test_login_inactive_user(
        self, client: TestClient, test_db: Session, facility_admin_user: models.User
    ):
        """Test login with inactive user account."""
        facility_admin_user.is_active = False
        test_db.commit()

        response = client.post(
            "/api/auth/token",
            data={"username": "facilityadmin", "password": "password123"},
        )
        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]

    def test_login_case_insensitive_username(
        self, client: TestClient, facility_admin_user: models.User
    ):
        """Test that login username is case-insensitive."""
        response = client.post(
            "/api/auth/token",
            data={"username": "FACILITYADMIN", "password": "password123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data


class TestAuthRefresh:
    """Tests for POST /api/auth/refresh."""

    def test_refresh_tokens_success(
        self,
        client: TestClient,
        auth_service: AuthService,
        facility_admin_user: models.User,
    ):
        """Test successful token refresh."""
        _, refresh_token_str = auth_service.create_refresh_token(
            facility_admin_user.id, facility_admin_user.role
        )
        # Get the actual JWT token (first element of tuple)
        refresh_token = auth_service.create_refresh_token(
            facility_admin_user.id, facility_admin_user.role
        )[0]

        response = client.post(
            "/api/auth/refresh", json={"refresh_token": refresh_token}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_refresh_with_access_token_fails(
        self,
        client: TestClient,
        auth_service: AuthService,
        facility_admin_user: models.User,
    ):
        """Test that using access token for refresh fails."""
        access_token, _ = auth_service.create_access_token(
            facility_admin_user.id,
            facility_admin_user.role,
            facility_admin_user.company_id,
        )

        response = client.post(
            "/api/auth/refresh", json={"refresh_token": access_token}
        )
        assert response.status_code == 401

    def test_refresh_with_invalid_token(self, client: TestClient):
        """Test refresh with invalid token."""
        response = client.post(
            "/api/auth/refresh", json={"refresh_token": "invalid_token"}
        )
        assert response.status_code == 401

    def test_refresh_inactive_user(
        self,
        client: TestClient,
        test_db: Session,
        auth_service: AuthService,
        facility_admin_user: models.User,
    ):
        """Test refresh fails for inactive user."""
        refresh_token, _ = auth_service.create_refresh_token(
            facility_admin_user.id, facility_admin_user.role
        )

        # Deactivate user
        facility_admin_user.is_active = False
        test_db.commit()

        response = client.post(
            "/api/auth/refresh", json={"refresh_token": refresh_token}
        )
        assert response.status_code == 403
        assert "deactivated" in response.json()["detail"].lower()


class TestAuthMe:
    """Tests for GET /api/auth/me."""

    def test_get_current_user_success(
        self, client: TestClient, facility_admin_token: str, facility_admin_user: models.User
    ):
        """Test getting current user info with valid token."""
        response = client.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {facility_admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(facility_admin_user.id)
        assert data["username"] == facility_admin_user.username
        assert data["name"] == facility_admin_user.name
        assert data["role"] == facility_admin_user.role.value
        assert data["is_active"] is True

    def test_get_current_user_no_token(self, client: TestClient):
        """Test that accessing /me without token fails."""
        response = client.get("/api/auth/me")
        assert response.status_code == 401

    def test_get_current_user_invalid_token(self, client: TestClient):
        """Test that accessing /me with invalid token fails."""
        response = client.get(
            "/api/auth/me", headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401

    def test_get_current_user_different_roles(
        self,
        client: TestClient,
        superadmin_token: str,
        facility_admin_token: str,
        agency_admin_token: str,
        agency_staff_token: str,
    ):
        """Test /me endpoint works for all user roles."""
        tokens = [
            (superadmin_token, "ADMIN"),
            (facility_admin_token, "ADMIN"),
            (agency_admin_token, "AGENCY_ADMIN"),
            (agency_staff_token, "AGENCY_STAFF"),
        ]

        for token, expected_role in tokens:
            response = client.get(
                "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["role"] == expected_role


class TestUserRegistration:
    """Tests for POST /api/auth/register."""

    def test_register_user_success(
        self, client: TestClient, test_db: Session, sample_facility: models.Company
    ):
        """Test successful user registration."""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "newuser",
                "password": "password123",
                "email": "newuser@example.com",
                "name": "New User",
                "role": "staff",
                "company_id": str(sample_facility.id),
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "newuser@example.com"
        assert data["name"] == "New User"
        assert data["role"] == "staff"
        assert "id" in data

    def test_register_user_duplicate_username(
        self,
        client: TestClient,
        test_db: Session,
        sample_facility: models.Company,
        facility_admin_user: models.User,
    ):
        """Test registration with duplicate username fails."""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "facilityadmin",  # Already exists
                "password": "password123",
                "email": "another@example.com",
                "name": "Another User",
                "role": "staff",
                "company_id": str(sample_facility.id),
            },
        )
        assert response.status_code == 409
        assert "already taken" in response.json()["detail"].lower()

    def test_register_user_short_password(
        self, client: TestClient, sample_facility: models.Company
    ):
        """Test registration with password shorter than 8 characters fails."""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "newuser",
                "password": "short",  # Less than 8 characters
                "email": "newuser@example.com",
                "name": "New User",
                "role": "staff",
                "company_id": str(sample_facility.id),
            },
        )
        assert response.status_code == 422  # Validation error

    def test_register_user_without_company(self, client: TestClient):
        """Test registration without company (platform admin scenario)."""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "platformuser",
                "password": "password123",
                "email": "platform@example.com",
                "name": "Platform User",
                "role": "admin",
                "company_id": None,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "platformuser"
        assert data["company_id"] is None


class TestPasswordHashing:
    """Tests for password hashing functionality."""

    def test_password_hash_verification(self, auth_service: AuthService):
        """Test that password hashing and verification work correctly."""
        plain_password = "mySecurePassword123"
        hashed = auth_service.hash_password(plain_password)

        assert hashed != plain_password
        assert auth_service.verify_password(plain_password, hashed) is True
        assert auth_service.verify_password("wrongPassword", hashed) is False

    def test_different_passwords_have_different_hashes(
        self, auth_service: AuthService
    ):
        """Test that same password produces different hashes (salt)."""
        password = "samePassword"
        hash1 = auth_service.hash_password(password)
        hash2 = auth_service.hash_password(password)

        assert hash1 != hash2  # Different due to salt
        assert auth_service.verify_password(password, hash1) is True
        assert auth_service.verify_password(password, hash2) is True

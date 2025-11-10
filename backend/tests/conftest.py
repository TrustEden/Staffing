"""Test fixtures and configuration for pytest."""

from __future__ import annotations

import uuid
from datetime import date, datetime, time, timedelta, timezone
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app import models
from backend.app.database import Base, get_db
from backend.app.services.auth_service import AuthService
from backend.app.utils.constants import (
    CompanyType,
    RelationshipStatus,
    ShiftStatus,
    ShiftVisibility,
    UserRole,
)
from backend.main import app


@pytest.fixture(scope="function")
def test_db() -> Generator[Session, None, None]:
    """Create an in-memory SQLite test database for each test."""
    # Use SQLite in-memory database for fast tests
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Create all tables
    Base.metadata.create_all(bind=engine)

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(test_db: Session) -> Generator[TestClient, None, None]:
    """Create a FastAPI TestClient with test database."""
    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def auth_service(test_db: Session) -> AuthService:
    """Create an AuthService instance for testing."""
    return AuthService(test_db)


@pytest.fixture(scope="function")
def superadmin_user(test_db: Session, auth_service: AuthService) -> models.User:
    """Create a platform superadmin user (no company affiliation)."""
    user = models.User(
        id=uuid.uuid4(),
        username="superadmin",
        email="superadmin@example.com",
        hashed_password=auth_service.hash_password("password123"),
        name="Super Admin",
        role=UserRole.ADMIN,
        company_id=None,  # Platform admin has no company
        is_active=True,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture(scope="function")
def superadmin_token(auth_service: AuthService, superadmin_user: models.User) -> str:
    """Generate auth token for platform superadmin."""
    token, _ = auth_service.create_access_token(
        superadmin_user.id, superadmin_user.role, superadmin_user.company_id
    )
    return token


@pytest.fixture(scope="function")
def sample_facility(test_db: Session) -> models.Company:
    """Create a sample facility company."""
    facility = models.Company(
        id=uuid.uuid4(),
        display_id="FAC001",
        name="Memorial Hospital",
        type=CompanyType.FACILITY,
        address="123 Hospital Way",
        contact_email="contact@memorial.com",
        phone="555-0100",
        timezone="America/New_York",
        is_locked=False,
    )
    test_db.add(facility)
    test_db.commit()
    test_db.refresh(facility)
    return facility


@pytest.fixture(scope="function")
def facility_admin_user(
    test_db: Session, auth_service: AuthService, sample_facility: models.Company
) -> models.User:
    """Create a facility admin user."""
    user = models.User(
        id=uuid.uuid4(),
        username="facilityadmin",
        email="admin@memorial.com",
        hashed_password=auth_service.hash_password("password123"),
        name="Facility Admin",
        role=UserRole.ADMIN,
        company_id=sample_facility.id,
        is_active=True,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture(scope="function")
def facility_admin_token(
    auth_service: AuthService, facility_admin_user: models.User
) -> str:
    """Generate auth token for facility admin."""
    token, _ = auth_service.create_access_token(
        facility_admin_user.id, facility_admin_user.role, facility_admin_user.company_id
    )
    return token


@pytest.fixture(scope="function")
def sample_agency(test_db: Session) -> models.Company:
    """Create a sample agency company."""
    agency = models.Company(
        id=uuid.uuid4(),
        display_id="AGN001",
        name="Healthcare Staffing Plus",
        type=CompanyType.AGENCY,
        address="456 Agency Blvd",
        contact_email="contact@staffingplus.com",
        phone="555-0200",
        timezone="America/New_York",
        is_locked=False,
    )
    test_db.add(agency)
    test_db.commit()
    test_db.refresh(agency)
    return agency


@pytest.fixture(scope="function")
def agency_admin_user(
    test_db: Session, auth_service: AuthService, sample_agency: models.Company
) -> models.User:
    """Create an agency admin user."""
    user = models.User(
        id=uuid.uuid4(),
        username="agencyadmin",
        email="admin@staffingplus.com",
        hashed_password=auth_service.hash_password("password123"),
        name="Agency Admin",
        role=UserRole.AGENCY_ADMIN,
        company_id=sample_agency.id,
        is_active=True,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture(scope="function")
def agency_admin_token(auth_service: AuthService, agency_admin_user: models.User) -> str:
    """Generate auth token for agency admin."""
    token, _ = auth_service.create_access_token(
        agency_admin_user.id, agency_admin_user.role, agency_admin_user.company_id
    )
    return token


@pytest.fixture(scope="function")
def agency_staff_user(
    test_db: Session, auth_service: AuthService, sample_agency: models.Company
) -> models.User:
    """Create an agency staff user."""
    user = models.User(
        id=uuid.uuid4(),
        username="agencystaff",
        email="staff@staffingplus.com",
        hashed_password=auth_service.hash_password("password123"),
        name="Agency Staff",
        license_number="RN123456",
        role=UserRole.AGENCY_STAFF,
        company_id=sample_agency.id,
        is_active=True,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture(scope="function")
def agency_staff_token(auth_service: AuthService, agency_staff_user: models.User) -> str:
    """Generate auth token for agency staff."""
    token, _ = auth_service.create_access_token(
        agency_staff_user.id, agency_staff_user.role, agency_staff_user.company_id
    )
    return token


@pytest.fixture(scope="function")
def sample_shift(
    test_db: Session, sample_facility: models.Company, facility_admin_user: models.User
) -> models.Shift:
    """Create a sample shift."""
    tomorrow = date.today() + timedelta(days=1)
    shift = models.Shift(
        id=uuid.uuid4(),
        facility_id=sample_facility.id,
        date=tomorrow,
        start_time=time(7, 0),
        end_time=time(19, 0),
        role_required="RN",
        status=ShiftStatus.OPEN,
        visibility=ShiftVisibility.AGENCY,
        posted_by_id=facility_admin_user.id,
        posted_at=datetime.now(timezone.utc),
        notes="Need experienced RN for day shift",
        is_premium=False,
    )
    test_db.add(shift)
    test_db.commit()
    test_db.refresh(shift)
    return shift


@pytest.fixture(scope="function")
def active_relationship(
    test_db: Session,
    sample_facility: models.Company,
    sample_agency: models.Company,
    facility_admin_user: models.User,
) -> models.Relationship:
    """Create an active relationship between facility and agency."""
    relationship = models.Relationship(
        id=uuid.uuid4(),
        facility_id=sample_facility.id,
        agency_id=sample_agency.id,
        status=RelationshipStatus.ACTIVE,
        invited_by_id=facility_admin_user.id,
        invite_accepted_at=datetime.now(timezone.utc),
    )
    test_db.add(relationship)
    test_db.commit()
    test_db.refresh(relationship)
    return relationship


@pytest.fixture(scope="function")
def sample_claim(
    test_db: Session, sample_shift: models.Shift, agency_staff_user: models.User
) -> models.Claim:
    """Create a sample claim."""
    from backend.app.utils.constants import ClaimStatus

    claim = models.Claim(
        id=uuid.uuid4(),
        shift_id=sample_shift.id,
        user_id=agency_staff_user.id,
        status=ClaimStatus.PENDING,
        claimed_at=datetime.now(timezone.utc),
    )
    test_db.add(claim)
    sample_shift.status = ShiftStatus.PENDING
    test_db.commit()
    test_db.refresh(claim)
    return claim

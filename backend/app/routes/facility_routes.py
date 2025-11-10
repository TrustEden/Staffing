from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app import models
from backend.app.database import get_db
from backend.app.dependencies import get_auth_service, get_current_user, require_roles
from backend.app.schemas import CompanyCreate, CompanyCreateWithAdmin, CompanyOut, CompanyUpdate, RelationshipOut, UserCreate, UserOut
from backend.app.services.auth_service import AuthService
from backend.app.utils.constants import CompanyType, RelationshipStatus, UserRole
from backend.app.utils.id_generator import generate_company_display_id
from pydantic import BaseModel

router = APIRouter(tags=["facilities"])


class LinkRequestByDisplayId(BaseModel):
    agency_display_id: str


@router.get("/", response_model=list[CompanyOut])
def list_facilities(
    db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
) -> list[CompanyOut]:
    """List all facilities. Agency admins can see all facilities to request links."""
    query = db.query(models.Company).filter(models.Company.type == CompanyType.FACILITY)

    # Only filter for facility users - they should only see their own facility
    if current_user.role in {UserRole.ADMIN, UserRole.STAFF} and current_user.company_id:
        query = query.filter(models.Company.id == current_user.company_id)
    # Agency admins can see ALL facilities (to request links)
    # Platform admins can see all facilities

    facilities = query.order_by(models.Company.name).all()
    return [CompanyOut.model_validate(facility) for facility in facilities]


@router.post("/", response_model=CompanyOut, status_code=status.HTTP_201_CREATED)
def create_facility(
    payload: CompanyCreateWithAdmin,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles(UserRole.ADMIN)),
    auth_service: AuthService = Depends(get_auth_service),
) -> CompanyOut:
    if payload.type != CompanyType.FACILITY:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Company type must be facility")
    if current_user.company_id is not None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only platform admins can create facilities")

    # Generate unique display ID
    display_id = generate_company_display_id(db, CompanyType.FACILITY)

    # Create facility
    facility = models.Company(
        name=payload.name,
        type=CompanyType.FACILITY,
        display_id=display_id,
        address=payload.address,
        contact_email=str(payload.contact_email) if payload.contact_email else None,
        phone=payload.phone,
        timezone=payload.timezone,
    )
    db.add(facility)
    db.commit()
    db.refresh(facility)

    # Create admin user for the facility
    admin_user_data = UserCreate(
        username=payload.admin_username,
        email=payload.admin_email,
        password=payload.admin_password,
        name=payload.admin_name,
        phone=payload.admin_phone,
        role=UserRole.ADMIN,
        company_id=facility.id,
    )
    auth_service.create_user(admin_user_data)

    return CompanyOut.model_validate(facility)


@router.get("/{facility_id}", response_model=CompanyOut)
def get_facility(
    facility_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> CompanyOut:
    facility = _get_facility_or_404(db, facility_id)
    if current_user.role in {UserRole.ADMIN, UserRole.STAFF} and current_user.company_id not in {facility.id, None}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    if current_user.role == UserRole.AGENCY_ADMIN:
        relationship = (
            db.query(models.Relationship)
            .filter(
                models.Relationship.facility_id == facility.id,
                models.Relationship.agency_id == current_user.company_id,
                models.Relationship.status == RelationshipStatus.ACTIVE,
            )
            .one_or_none()
        )
        if not relationship:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No facility relationship")
    return CompanyOut.model_validate(facility)


@router.patch("/{facility_id}", response_model=CompanyOut)
def update_facility(
    facility_id: UUID,
    payload: CompanyUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> CompanyOut:
    facility = _get_facility_or_404(db, facility_id)
    if current_user.company_id not in {facility.id, None}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot modify this facility")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(facility, field, value)
    db.commit()
    db.refresh(facility)
    return CompanyOut.model_validate(facility)


@router.get("/{facility_id}/staff", response_model=list[UserOut])
def list_staff(
    facility_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> list[UserOut]:
    facility = _get_facility_or_404(db, facility_id)
    if current_user.company_id not in {facility.id, None}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    staff = (
        db.query(models.User)
        .filter(
            models.User.company_id == facility.id,
            models.User.role.in_([UserRole.STAFF, UserRole.ADMIN]),
        )
        .order_by(models.User.name)
        .all()
    )
    return [UserOut.model_validate(member) for member in staff]


@router.post("/{facility_id}/staff", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def add_staff_member(
    facility_id: UUID,
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> UserOut:
    facility = _get_facility_or_404(db, facility_id)
    if current_user.company_id != facility.id or current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only facility admins can add staff")

    if payload.role not in {UserRole.STAFF, UserRole.ADMIN}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role for facility staff")

    staff_payload = payload.model_copy(update={"company_id": facility.id})
    staff_member = auth_service.create_user(staff_payload)
    return UserOut.model_validate(staff_member)


def _get_facility_or_404(db: Session, facility_id: UUID) -> models.Company:
    facility = db.get(models.Company, facility_id)
    if not facility or facility.type != CompanyType.FACILITY:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Facility not found")
    return facility


@router.post("/{facility_id}/request-link")
def request_agency_link(
    facility_id: UUID,
    payload: LinkRequestByDisplayId,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> dict:
    """Request a connection with an agency by entering their display ID."""
    facility = _get_facility_or_404(db, facility_id)

    if current_user.company_id != facility.id or current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only facility admins can request links")

    # Find agency by display_id
    agency = (
        db.query(models.Company)
        .filter(
            models.Company.display_id == payload.agency_display_id,
            models.Company.type == CompanyType.AGENCY
        )
        .first()
    )

    if not agency:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agency with ID '{payload.agency_display_id}' not found"
        )

    # Check if relationship already exists
    existing = (
        db.query(models.Relationship)
        .filter(
            models.Relationship.facility_id == facility.id,
            models.Relationship.agency_id == agency.id
        )
        .first()
    )

    if existing:
        if existing.status == RelationshipStatus.ACTIVE:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already linked with this agency")
        elif existing.status == RelationshipStatus.INVITED:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Link request already pending")
        else:  # REVOKED
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Previous link was revoked. Contact platform admin.")

    # Create pending relationship request
    relationship = models.Relationship(
        facility_id=facility.id,
        agency_id=agency.id,
        status=RelationshipStatus.INVITED,
        invited_by_id=current_user.id
    )
    db.add(relationship)
    db.commit()
    db.refresh(relationship)

    return {
        "message": f"Link request sent to platform admin for approval",
        "facility": facility.name,
        "agency": agency.name,
        "status": "pending_approval"
    }


@router.get("/{facility_id}/all-relationships", response_model=list[RelationshipOut])
def list_facility_relationships(
    facility_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> list[RelationshipOut]:
    """Get all relationships (invited, active, revoked) for a facility."""
    facility = _get_facility_or_404(db, facility_id)

    if current_user.company_id != facility.id or current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only facility admins can view relationships")

    relationships = (
        db.query(models.Relationship)
        .filter(models.Relationship.facility_id == facility.id)
        .order_by(models.Relationship.created_at.desc())
        .all()
    )
    return [RelationshipOut.model_validate(rel) for rel in relationships]

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

router = APIRouter(tags=["agencies"])


class LinkRequestByDisplayId(BaseModel):
    facility_display_id: str


@router.get("/", response_model=list[CompanyOut])
def list_agencies(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> list[CompanyOut]:
    """List all agencies. Facility admins can see all agencies to request links."""
    query = db.query(models.Company).filter(models.Company.type == CompanyType.AGENCY)

    # Only filter for agency users - they should only see their own agency
    if current_user.role in {UserRole.AGENCY_ADMIN, UserRole.AGENCY_STAFF} and current_user.company_id:
        query = query.filter(models.Company.id == current_user.company_id)
    # Facility admins and staff can see ALL agencies (to request links)
    # Platform admins can see all agencies

    agencies = query.order_by(models.Company.name).all()
    return [CompanyOut.model_validate(agency) for agency in agencies]


@router.post("/", response_model=CompanyOut, status_code=status.HTTP_201_CREATED)
def create_agency(
    payload: CompanyCreateWithAdmin,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles(UserRole.ADMIN)),
    auth_service: AuthService = Depends(get_auth_service),
) -> CompanyOut:
    if payload.type != CompanyType.AGENCY:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Company type must be agency")
    if current_user.company_id is not None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only platform admins can create agencies")

    # Generate unique display ID
    display_id = generate_company_display_id(db, CompanyType.AGENCY)

    # Create agency
    agency = models.Company(
        name=payload.name,
        type=CompanyType.AGENCY,
        display_id=display_id,
        address=payload.address,
        contact_email=str(payload.contact_email) if payload.contact_email else None,
        phone=payload.phone,
        timezone=payload.timezone,
    )
    db.add(agency)
    db.commit()
    db.refresh(agency)

    # Create admin user for the agency
    admin_user_data = UserCreate(
        username=payload.admin_username,
        email=payload.admin_email,
        password=payload.admin_password,
        name=payload.admin_name,
        phone=payload.admin_phone,
        role=UserRole.AGENCY_ADMIN,
        company_id=agency.id,
    )
    auth_service.create_user(admin_user_data)

    return CompanyOut.model_validate(agency)


@router.get("/{agency_id}", response_model=CompanyOut)
def get_agency(
    agency_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> CompanyOut:
    agency = _get_agency_or_404(db, agency_id)
    if current_user.role in {UserRole.AGENCY_ADMIN, UserRole.AGENCY_STAFF} and current_user.company_id not in {agency.id, None}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    if current_user.role in {UserRole.ADMIN, UserRole.STAFF} and current_user.company_id:
        relationship = (
            db.query(models.Relationship)
            .filter(
                models.Relationship.facility_id == current_user.company_id,
                models.Relationship.agency_id == agency.id,
                models.Relationship.status == RelationshipStatus.ACTIVE,
            )
            .one_or_none()
        )
        if not relationship:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No agency relationship")
    return CompanyOut.model_validate(agency)


@router.patch("/{agency_id}", response_model=CompanyOut)
def update_agency(
    agency_id: UUID,
    payload: CompanyUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> CompanyOut:
    agency = _get_agency_or_404(db, agency_id)
    if current_user.company_id not in {agency.id, None}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot modify this agency")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(agency, field, value)
    db.commit()
    db.refresh(agency)
    return CompanyOut.model_validate(agency)


@router.get("/{agency_id}/staff", response_model=list[UserOut])
def list_agency_staff(
    agency_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> list[UserOut]:
    agency = _get_agency_or_404(db, agency_id)
    if current_user.company_id not in {agency.id, None}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    staff = (
        db.query(models.User)
        .filter(
            models.User.company_id == agency.id,
            models.User.role.in_([UserRole.AGENCY_ADMIN, UserRole.AGENCY_STAFF]),
        )
        .order_by(models.User.name)
        .all()
    )
    return [UserOut.model_validate(member) for member in staff]


@router.post("/{agency_id}/staff", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def add_agency_staff(
    agency_id: UUID,
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> UserOut:
    agency = _get_agency_or_404(db, agency_id)
    if current_user.company_id != agency.id or current_user.role != UserRole.AGENCY_ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only agency admins can add staff")

    if payload.role not in {UserRole.AGENCY_ADMIN, UserRole.AGENCY_STAFF}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role for agency staff")

    staff_payload = payload.model_copy(update={"company_id": agency.id})
    staff_member = auth_service.create_user(staff_payload)
    return UserOut.model_validate(staff_member)


@router.get("/{agency_id}/relationships", response_model=list[CompanyOut])
def list_agency_facilities(
    agency_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> list[CompanyOut]:
    agency = _get_agency_or_404(db, agency_id)
    if current_user.company_id not in {agency.id, None}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    facilities = (
        db.query(models.Company)
        .join(models.Relationship, models.Relationship.facility_id == models.Company.id)
        .filter(
            models.Relationship.agency_id == agency.id,
            models.Relationship.status == RelationshipStatus.ACTIVE,
            models.Company.type == CompanyType.FACILITY,
        )
        .order_by(models.Company.name)
        .all()
    )
    return [CompanyOut.model_validate(facility) for facility in facilities]


def _get_agency_or_404(db: Session, agency_id: UUID) -> models.Company:
    agency = db.get(models.Company, agency_id)
    if not agency or agency.type != CompanyType.AGENCY:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agency not found")
    return agency


@router.post("/{agency_id}/request-link")
def request_facility_link(
    agency_id: UUID,
    payload: LinkRequestByDisplayId,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> dict:
    """Request a connection with a facility by entering their display ID."""
    agency = _get_agency_or_404(db, agency_id)

    if current_user.company_id != agency.id or current_user.role != UserRole.AGENCY_ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only agency admins can request links")

    # Find facility by display_id
    facility = (
        db.query(models.Company)
        .filter(
            models.Company.display_id == payload.facility_display_id,
            models.Company.type == CompanyType.FACILITY
        )
        .first()
    )

    if not facility:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Facility with ID '{payload.facility_display_id}' not found"
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
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already linked with this facility")
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


@router.get("/{agency_id}/all-relationships", response_model=list[RelationshipOut])
def list_agency_relationships(
    agency_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> list[RelationshipOut]:
    """Get all relationships (invited, active, revoked) for an agency."""
    agency = _get_agency_or_404(db, agency_id)

    if current_user.company_id != agency.id or current_user.role != UserRole.AGENCY_ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only agency admins can view relationships")

    relationships = (
        db.query(models.Relationship)
        .filter(models.Relationship.agency_id == agency.id)
        .order_by(models.Relationship.created_at.desc())
        .all()
    )
    return [RelationshipOut.model_validate(rel) for rel in relationships]

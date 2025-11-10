from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app import models
from backend.app.database import get_db
from backend.app.dependencies import get_auth_service, get_current_user
from backend.app.schemas import ClaimOut, RelationshipCreate, RelationshipOut, RelationshipUpdate
from backend.app.services.auth_service import AuthService
from backend.app.utils.constants import ClaimStatus, CompanyType, RelationshipStatus, ShiftStatus, UserRole
from pydantic import BaseModel

router = APIRouter(tags=["admin"])


class CompanyStatsOut(BaseModel):
    company_id: UUID
    display_id: str
    name: str
    type: CompanyType
    employee_count: int
    total_shifts: int
    filled_shifts: int
    fill_rate: float
    is_locked: bool


class PasswordResetRequest(BaseModel):
    new_password: str


class LockStatusUpdate(BaseModel):
    is_locked: bool


@router.get("/relationships", response_model=list[RelationshipOut])
def list_relationships(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> list[RelationshipOut]:
    _ensure_platform_admin(current_user)
    relationships = db.query(models.Relationship).order_by(models.Relationship.created_at.desc()).all()
    return [RelationshipOut.model_validate(rel) for rel in relationships]


@router.post("/relationships", response_model=RelationshipOut, status_code=status.HTTP_201_CREATED)
def create_relationship(
    payload: RelationshipCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> RelationshipOut:
    _ensure_platform_admin(current_user)
    facility = db.get(models.Company, payload.facility_id)
    agency = db.get(models.Company, payload.agency_id)
    if not facility or facility.type != CompanyType.FACILITY:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Facility not found")
    if not agency or agency.type != CompanyType.AGENCY:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agency not found")

    existing = (
        db.query(models.Relationship)
        .filter(
            models.Relationship.facility_id == payload.facility_id,
            models.Relationship.agency_id == payload.agency_id,
        )
        .one_or_none()
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Relationship already exists")

    relationship = models.Relationship(
        facility_id=payload.facility_id,
        agency_id=payload.agency_id,
        status=RelationshipStatus.INVITED,
        invited_by_id=current_user.id,
    )
    db.add(relationship)
    db.commit()
    db.refresh(relationship)
    return RelationshipOut.model_validate(relationship)


@router.patch("/relationships/{relationship_id}", response_model=RelationshipOut)
def update_relationship(
    relationship_id: UUID,
    payload: RelationshipUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> RelationshipOut:
    _ensure_platform_admin(current_user)
    relationship = db.get(models.Relationship, relationship_id)
    if not relationship:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Relationship not found")

    relationship.status = payload.status
    if payload.status == RelationshipStatus.ACTIVE:
        relationship.invite_accepted_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(relationship)
    return RelationshipOut.model_validate(relationship)


@router.delete("/relationships/{relationship_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_relationship(
    relationship_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> None:
    _ensure_platform_admin(current_user)
    relationship = db.get(models.Relationship, relationship_id)
    if not relationship:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Relationship not found")
    db.delete(relationship)
    db.commit()


@router.get("/claims/pending", response_model=list[ClaimOut])
def list_pending_claims(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> list[ClaimOut]:
    if current_user.company_id is None:
        claims = db.query(models.Claim).filter(models.Claim.status == ClaimStatus.PENDING).all()
    else:
        if current_user.role != UserRole.ADMIN:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only facility admins can view pending claims")
        claims = (
            db.query(models.Claim)
            .join(models.Shift)
            .filter(
                models.Shift.facility_id == current_user.company_id,
                models.Claim.status == ClaimStatus.PENDING,
            )
            .all()
        )
    return [ClaimOut.model_validate(claim) for claim in claims]


def _ensure_platform_admin(user: models.User) -> None:
    if user.company_id is not None or user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Platform admin required")


@router.get("/companies/{company_id}/stats", response_model=CompanyStatsOut)
def get_company_stats(
    company_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> CompanyStatsOut:
    """Get statistics for a specific company."""
    _ensure_platform_admin(current_user)

    company = db.get(models.Company, company_id)
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    # Count employees
    employee_count = db.query(models.User).filter(models.User.company_id == company_id).count()

    # Count shifts (for facilities) or count staff shifts (for agencies)
    if company.type == CompanyType.FACILITY:
        total_shifts = db.query(models.Shift).filter(models.Shift.facility_id == company_id).count()
        # Filled shifts = shifts with approved claims
        filled_shifts = (
            db.query(models.Shift)
            .join(models.Claim)
            .filter(
                models.Shift.facility_id == company_id,
                models.Claim.status == ClaimStatus.APPROVED
            )
            .distinct()
            .count()
        )
    else:
        # For agencies, count shifts claimed by their staff
        total_shifts = (
            db.query(models.Claim)
            .join(models.User, models.Claim.user_id == models.User.id)
            .filter(models.User.company_id == company_id)
            .count()
        )
        filled_shifts = (
            db.query(models.Claim)
            .join(models.User, models.Claim.user_id == models.User.id)
            .filter(
                models.User.company_id == company_id,
                models.Claim.status == ClaimStatus.APPROVED
            )
            .count()
        )

    fill_rate = (filled_shifts / total_shifts * 100) if total_shifts > 0 else 0.0

    return CompanyStatsOut(
        company_id=company.id,
        display_id=company.display_id,
        name=company.name,
        type=company.type,
        employee_count=employee_count,
        total_shifts=total_shifts,
        filled_shifts=filled_shifts,
        fill_rate=round(fill_rate, 2),
        is_locked=company.is_locked,
    )


@router.patch("/companies/{company_id}/lock", response_model=dict)
def update_lock_status(
    company_id: UUID,
    payload: LockStatusUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> dict:
    """Lock or unlock a company account."""
    _ensure_platform_admin(current_user)

    company = db.get(models.Company, company_id)
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    company.is_locked = payload.is_locked
    db.commit()

    # Also lock/unlock all users in that company
    db.query(models.User).filter(models.User.company_id == company_id).update(
        {"is_active": not payload.is_locked}
    )
    db.commit()

    action = "locked" if payload.is_locked else "unlocked"
    return {"message": f"Company {company.name} ({company.display_id}) has been {action}"}


@router.post("/companies/{company_id}/reset-admin-password")
def reset_company_admin_password(
    company_id: UUID,
    payload: PasswordResetRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> dict:
    """Reset the password for a company's admin user."""
    _ensure_platform_admin(current_user)

    company = db.get(models.Company, company_id)
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    # Find the admin user for this company
    admin_role = UserRole.AGENCY_ADMIN if company.type == CompanyType.AGENCY else UserRole.ADMIN
    admin_user = (
        db.query(models.User)
        .filter(
            models.User.company_id == company_id,
            models.User.role == admin_role
        )
        .first()
    )

    if not admin_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin user not found for this company")

    # Reset the password
    admin_user.hashed_password = auth_service.hash_password(payload.new_password)
    db.commit()

    return {
        "message": f"Password reset successfully for {company.name} admin ({admin_user.username})",
        "admin_username": admin_user.username
    }

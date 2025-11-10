from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app import models
from backend.app.database import get_db
from backend.app.dependencies import get_current_user
from backend.app.schemas import (
    ClaimActionResponse,
    ClaimCreate,
    ClaimDecisionRequest,
    ClaimOut,
    ShiftCreate,
    ShiftOut,
    ShiftUpdate,
)
from backend.app.services.notification_service import NotificationService
from backend.app.services.scheduler import ShiftScheduler
from backend.app.services.shift_conflict_checker import ShiftConflictChecker
from backend.app.utils.constants import (
    ClaimStatus,
    CompanyType,
    NotificationType,
    RelationshipStatus,
    ShiftStatus,
    ShiftVisibility,
    UserRole,
)

router = APIRouter(tags=["shifts"])
scheduler = ShiftScheduler()


def get_notification_service(db: Session = Depends(get_db)) -> NotificationService:
    return NotificationService(db)


@router.post("/", response_model=ShiftOut, status_code=status.HTTP_201_CREATED)
def create_shift(
    payload: ShiftCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> ShiftOut:
    _ensure_facility_admin(current_user, payload.facility_id)
    facility = db.get(models.Company, payload.facility_id)
    if not facility or facility.type != CompanyType.FACILITY:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Facility not found")

    release_at = payload.release_at
    tier_1_release = None
    tier_2_release = None

    # Calculate tier release times for tiered visibility shifts
    if payload.visibility == ShiftVisibility.TIERED:
        base = datetime.combine(payload.date, payload.start_time, tzinfo=timezone.utc)
        if not release_at:
            release_at = base - timedelta(hours=scheduler.settings.default_tiered_release_hours)

        # Set tier_1_release to release_at, tier_2_release to 12 hours later
        tier_1_release = release_at
        tier_2_release = release_at + timedelta(hours=12)

        # Start with internal visibility for tiered releases
        visibility = ShiftVisibility.INTERNAL
    else:
        visibility = payload.visibility

    shift = models.Shift(
        facility_id=payload.facility_id,
        date=payload.date,
        start_time=payload.start_time,
        end_time=payload.end_time,
        role_required=payload.role_required,
        visibility=visibility,
        notes=payload.notes,
        is_premium=payload.is_premium,
        premium_notes=payload.premium_notes,
        posted_by_id=current_user.id,
        release_at=release_at,
        tier_1_release=tier_1_release,
        tier_2_release=tier_2_release,
    )
    db.add(shift)
    db.commit()
    db.refresh(shift)

    # Schedule tier releases if tier times are in the future
    if tier_1_release and tier_1_release > datetime.now(timezone.utc):
        scheduler.schedule_shift_release(shift.id, tier_1_release, tier_2_release)

    return ShiftOut.model_validate(shift)


@router.get("/", response_model=list[ShiftOut])
def list_shifts(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    facility_id: Optional[UUID] = None,
    status_filter: Optional[ShiftStatus] = Query(None, alias="status"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    role_required: Optional[str] = None,
) -> list[ShiftOut]:
    query = db.query(models.Shift)

    if facility_id:
        query = query.filter(models.Shift.facility_id == facility_id)
    if status_filter:
        query = query.filter(models.Shift.status == status_filter)
    if start_date:
        query = query.filter(models.Shift.date >= start_date)
    if end_date:
        query = query.filter(models.Shift.date <= end_date)
    if role_required:
        query = query.filter(models.Shift.role_required.ilike(f"%{role_required}%"))

    shifts = query.order_by(models.Shift.date, models.Shift.start_time).all()
    visible_shifts = [shift for shift in shifts if _can_view_shift(db, current_user, shift)]

    # Add facility name to each shift
    shift_outs = []
    for shift in visible_shifts:
        shift_dict = ShiftOut.model_validate(shift).model_dump()
        shift_dict['facility_name'] = shift.facility.name if shift.facility else None
        shift_outs.append(ShiftOut(**shift_dict))

    return shift_outs


@router.get("/{shift_id}", response_model=ShiftOut)
def get_shift(
    shift_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> ShiftOut:
    shift = _get_shift_or_404(db, shift_id)
    if not _can_view_shift(db, current_user, shift):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not permitted to view this shift")
    return ShiftOut.model_validate(shift)


@router.patch("/{shift_id}", response_model=ShiftOut)
def update_shift(
    shift_id: UUID,
    payload: ShiftUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> ShiftOut:
    shift = _get_shift_or_404(db, shift_id)
    _ensure_facility_admin(current_user, shift.facility_id)

    update_data = payload.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(shift, field, value)

    if shift.visibility == ShiftVisibility.TIERED and shift.release_at is None:
        shift.release_at = scheduler.compute_release_at(shift)
    db.commit()
    db.refresh(shift)
    return ShiftOut.model_validate(shift)


@router.post("/{shift_id}/cancel", response_model=ShiftOut)
def cancel_shift(
    shift_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service),
) -> ShiftOut:
    shift = _get_shift_or_404(db, shift_id)
    _ensure_facility_admin(current_user, shift.facility_id)

    shift.status = ShiftStatus.CANCELLED
    for claim in shift.claims:
        if claim.status in {ClaimStatus.PENDING, ClaimStatus.APPROVED}:
            claim.status = ClaimStatus.DENIED
            claim.denial_reason = "Shift cancelled by facility"
            notification_service.create_notification(
                claim.user_id,
                NotificationType.SHIFT_CANCELLED.value,
                f"Shift on {shift.date} was cancelled.",
            )
    db.commit()
    db.refresh(shift)
    return ShiftOut.model_validate(shift)


@router.post("/{shift_id}/claims", response_model=ClaimActionResponse, status_code=status.HTTP_201_CREATED)
def claim_shift(
    shift_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> ClaimActionResponse:
    shift = _get_shift_or_404(db, shift_id)
    if not _can_view_shift(db, current_user, shift):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot claim this shift")
    if shift.status in {ShiftStatus.APPROVED, ShiftStatus.CANCELLED}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Shift is not available")

    existing_claim = (
        db.query(models.Claim)
        .filter(models.Claim.shift_id == shift.id, models.Claim.user_id == current_user.id)
        .one_or_none()
    )
    if existing_claim:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You already claimed this shift")

    conflict_checker = ShiftConflictChecker(db)
    conflicts = conflict_checker.check_for_user(current_user.id, shift)
    if conflicts.hard_conflicts:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=conflicts.hard_conflicts[0])

    claim = models.Claim(
        shift_id=shift.id,
        user_id=current_user.id,
        status=ClaimStatus.PENDING,
    )
    db.add(claim)
    shift.status = ShiftStatus.PENDING
    db.commit()
    db.refresh(claim)

    _notify_shift_claim(db, shift, claim)
    return ClaimActionResponse(claim=ClaimOut.model_validate(claim), warnings=conflicts.warnings)


@router.get("/{shift_id}/claims", response_model=list[ClaimOut])
def list_shift_claims(
    shift_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> list[ClaimOut]:
    shift = _get_shift_or_404(db, shift_id)
    if not _can_manage_shift(current_user, shift):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not permitted")

    # Add user name to each claim
    claim_outs = []
    for claim in shift.claims:
        claim_dict = ClaimOut.model_validate(claim).model_dump()
        claim_dict['user_name'] = claim.user.name if claim.user else "Unknown"
        claim_outs.append(ClaimOut(**claim_dict))

    return claim_outs


@router.post("/{shift_id}/claims/{claim_id}/approve", response_model=ClaimOut)
def approve_claim(
    shift_id: UUID,
    claim_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service),
) -> ClaimOut:
    shift = _get_shift_or_404(db, shift_id)
    if not _can_manage_shift(current_user, shift):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not permitted")

    claim = db.get(models.Claim, claim_id)
    if not claim or claim.shift_id != shift.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")

    claim.status = ClaimStatus.APPROVED
    claim.approved_by_id = current_user.id
    claim.denial_reason = None
    shift.status = ShiftStatus.APPROVED

    other_claims = (
        db.query(models.Claim)
        .filter(
            models.Claim.shift_id == shift.id,
            models.Claim.id != claim.id,
            models.Claim.status == ClaimStatus.PENDING,
        )
        .all()
    )
    for other in other_claims:
        other.status = ClaimStatus.DENIED
        other.denial_reason = "Another claim was approved"
        notification_service.create_notification(
            other.user_id,
            NotificationType.SHIFT_DENIED.value,
            f"Shift on {shift.date} was assigned to another clinician.",
        )

    db.commit()
    db.refresh(claim)

    notification_service.create_notification(
        claim.user_id,
        NotificationType.SHIFT_APPROVED.value,
        f"Your claim for the shift on {shift.date} has been approved.",
    )
    return ClaimOut.model_validate(claim)


@router.post("/{shift_id}/claims/{claim_id}/deny", response_model=ClaimOut)
def deny_claim(
    shift_id: UUID,
    claim_id: UUID,
    payload: ClaimDecisionRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service),
) -> ClaimOut:
    shift = _get_shift_or_404(db, shift_id)
    if not _can_manage_shift(current_user, shift):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not permitted")

    claim = db.get(models.Claim, claim_id)
    if not claim or claim.shift_id != shift.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")

    claim.status = ClaimStatus.DENIED
    claim.denial_reason = payload.reason
    claim.approved_by_id = current_user.id

    remaining_pending = (
        db.query(models.Claim)
        .filter(models.Claim.shift_id == shift.id, models.Claim.status == ClaimStatus.PENDING)
        .count()
    )
    if remaining_pending == 0:
        shift.status = ShiftStatus.OPEN
    db.commit()
    db.refresh(claim)

    notification_service.create_notification(
        claim.user_id,
        NotificationType.SHIFT_DENIED.value,
        payload.reason or f"Your claim for the shift on {shift.date} was denied.",
    )
    return ClaimOut.model_validate(claim)


def _get_shift_or_404(db: Session, shift_id: UUID) -> models.Shift:
    shift = db.get(models.Shift, shift_id)
    if not shift:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shift not found")
    return shift


def _ensure_facility_admin(user: models.User, facility_id: UUID) -> None:
    if user.company_id is None:
        return
    if user.company_id != facility_id or user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Facility admin required")


def _can_manage_shift(user: models.User, shift: models.Shift) -> bool:
    if user.company_id is None:
        return True
    return user.role == UserRole.ADMIN and user.company_id == shift.facility_id


def _can_view_shift(db: Session, user: models.User, shift: models.Shift) -> bool:
    if user.company_id is None:
        return True
    if user.role in {UserRole.ADMIN, UserRole.STAFF}:
        return user.company_id == shift.facility_id
    if user.role in {UserRole.AGENCY_ADMIN, UserRole.AGENCY_STAFF}:
        relationship = (
            db.query(models.Relationship)
            .filter(
                models.Relationship.facility_id == shift.facility_id,
                models.Relationship.agency_id == user.company_id,
                models.Relationship.status == RelationshipStatus.ACTIVE,
            )
            .one_or_none()
        )
        if not relationship:
            return False
        if shift.visibility == ShiftVisibility.INTERNAL:
            return False
        if shift.visibility == ShiftVisibility.TIERED and not scheduler.should_release_to_agencies(shift):
            return False
        return True
    return False


def _notify_shift_claim(db: Session, shift: models.Shift, claim: models.Claim) -> None:
    notification_service = NotificationService(db)
    facility_admins = (
        db.query(models.User)
        .filter(
            models.User.company_id == shift.facility_id,
            models.User.role == UserRole.ADMIN,
        )
        .all()
    )
    for admin_user in facility_admins:
        notification_service.create_notification(
            admin_user.id,
            NotificationType.SHIFT_CLAIMED.value,
            f"Shift on {shift.date} was claimed by {claim.user.name}.",
        )
    if claim.user.company_id and claim.user.company_id != shift.facility_id:
        agency_admins = (
            db.query(models.User)
            .filter(
                models.User.company_id == claim.user.company_id,
                models.User.role == UserRole.AGENCY_ADMIN,
            )
            .all()
        )
        for admin_user in agency_admins:
            notification_service.create_notification(
                admin_user.id,
                NotificationType.SHIFT_CLAIMED.value,
                f"Your staff member {claim.user.name} claimed a shift on {shift.date}.",
            )

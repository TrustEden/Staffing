"""Analytics routes for Healthcare Staffing Bridge application."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app import models
from backend.app.database import get_db
from backend.app.dependencies import get_current_user
from backend.app.schemas import (
    AgencyPerformanceResponse,
    FillRateResponse,
    ShiftStatsResponse,
    TimeToFillResponse,
)
from backend.app.services import analytics
from backend.app.utils.constants import CompanyType, UserRole

router = APIRouter(tags=["analytics"])


@router.get("/facility/{facility_id}/fill-rate", response_model=FillRateResponse)
def get_facility_fill_rate(
    facility_id: UUID,
    start_date: date = Query(..., description="Start date for analysis period (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date for analysis period (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> FillRateResponse:
    """
    Get fill rate statistics for a facility.

    Calculates the percentage of shifts filled (approved) vs total shifts.

    **Authorization:**
    - Platform admins can view any facility
    - Facility admins/staff can only view their own facility
    - Agency users cannot access this endpoint
    """
    # Verify facility exists
    facility = _get_facility_or_404(db, facility_id)

    # Authorization check
    _ensure_facility_access(current_user, facility)

    # Validate date range
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be before or equal to end_date"
        )

    # Calculate fill rate
    result = analytics.calculate_fill_rate(db, facility_id, start_date, end_date)
    return FillRateResponse(**result)


@router.get("/facility/{facility_id}/time-to-fill", response_model=TimeToFillResponse)
def get_facility_time_to_fill(
    facility_id: UUID,
    start_date: date = Query(..., description="Start date for analysis period (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date for analysis period (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> TimeToFillResponse:
    """
    Get time-to-fill metrics for a facility.

    Calculates average time from shift creation to claim approval.

    **Authorization:**
    - Platform admins can view any facility
    - Facility admins/staff can only view their own facility
    - Agency users cannot access this endpoint
    """
    # Verify facility exists
    facility = _get_facility_or_404(db, facility_id)

    # Authorization check
    _ensure_facility_access(current_user, facility)

    # Validate date range
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be before or equal to end_date"
        )

    # Calculate time to fill
    result = analytics.get_time_to_fill_metrics(db, facility_id, start_date, end_date)
    return TimeToFillResponse(**result)


@router.get("/facility/{facility_id}/shift-stats", response_model=ShiftStatsResponse)
def get_facility_shift_stats(
    facility_id: UUID,
    start_date: date = Query(..., description="Start date for analysis period (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date for analysis period (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> ShiftStatsResponse:
    """
    Get comprehensive shift statistics for a facility.

    Returns counts by status, visibility tier, and premium shifts.

    **Authorization:**
    - Platform admins can view any facility
    - Facility admins/staff can only view their own facility
    - Agency users cannot access this endpoint
    """
    # Verify facility exists
    facility = _get_facility_or_404(db, facility_id)

    # Authorization check
    _ensure_facility_access(current_user, facility)

    # Validate date range
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be before or equal to end_date"
        )

    # Get shift statistics
    result = analytics.get_shift_statistics(db, facility_id, start_date, end_date)
    return ShiftStatsResponse(**result)


@router.get("/agency/{agency_id}/performance", response_model=AgencyPerformanceResponse)
def get_agency_performance(
    agency_id: UUID,
    start_date: date = Query(..., description="Start date for analysis period (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date for analysis period (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> AgencyPerformanceResponse:
    """
    Get performance metrics for an agency.

    Returns claim statistics, approval rate, and average response time.

    **Authorization:**
    - Platform admins can view any agency
    - Agency admins can only view their own agency
    - Facility users cannot access this endpoint
    """
    # Verify agency exists
    agency = _get_agency_or_404(db, agency_id)

    # Authorization check
    _ensure_agency_access(current_user, agency)

    # Validate date range
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be before or equal to end_date"
        )

    # Get agency performance
    result = analytics.get_agency_performance(db, agency_id, start_date, end_date)
    return AgencyPerformanceResponse(**result)


# Helper functions
def _get_facility_or_404(db: Session, facility_id: UUID) -> models.Company:
    """Get facility by ID or raise 404."""
    facility = db.get(models.Company, facility_id)
    if not facility or facility.type != CompanyType.FACILITY:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Facility not found"
        )
    return facility


def _get_agency_or_404(db: Session, agency_id: UUID) -> models.Company:
    """Get agency by ID or raise 404."""
    agency = db.get(models.Company, agency_id)
    if not agency or agency.type != CompanyType.AGENCY:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agency not found"
        )
    return agency


def _ensure_facility_access(user: models.User, facility: models.Company) -> None:
    """
    Ensure user has access to facility analytics.

    - Platform admins (no company_id) can access any facility
    - Facility admins/staff can only access their own facility
    - Agency users are denied
    """
    # Platform admin (no company association) can access any facility
    if user.company_id is None:
        return

    # Agency users cannot access facility analytics
    if user.role in {UserRole.AGENCY_ADMIN, UserRole.AGENCY_STAFF}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Agency users cannot access facility analytics"
        )

    # Facility users can only access their own facility
    if user.role in {UserRole.ADMIN, UserRole.STAFF}:
        if user.company_id != facility.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only access analytics for your own facility"
            )
        return

    # Default deny
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied"
    )


def _ensure_agency_access(user: models.User, agency: models.Company) -> None:
    """
    Ensure user has access to agency analytics.

    - Platform admins (no company_id) can access any agency
    - Agency admins can only access their own agency
    - Facility users are denied
    """
    # Platform admin (no company association) can access any agency
    if user.company_id is None:
        return

    # Facility users cannot access agency analytics
    if user.role in {UserRole.ADMIN, UserRole.STAFF}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Facility users cannot access agency analytics"
        )

    # Agency users can only access their own agency
    if user.role in {UserRole.AGENCY_ADMIN, UserRole.AGENCY_STAFF}:
        if user.company_id != agency.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only access analytics for your own agency"
            )
        return

    # Default deny
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied"
    )

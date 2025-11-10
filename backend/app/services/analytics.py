"""Analytics service for Healthcare Staffing Bridge application."""

from __future__ import annotations

from datetime import date
from typing import Optional
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app import models
from backend.app.utils.constants import ClaimStatus, ShiftStatus, ShiftVisibility


def calculate_fill_rate(
    db: Session, facility_id: UUID, start_date: date, end_date: date
) -> dict:
    """
    Calculate the percentage of shifts filled (status='approved') vs total shifts.

    Args:
        db: Database session
        facility_id: UUID of the facility
        start_date: Start date for the analysis period
        end_date: End date for the analysis period

    Returns:
        Dictionary with fill_rate statistics
    """
    # Query total shifts for the facility within the date range
    total_shifts = (
        db.query(func.count(models.Shift.id))
        .filter(
            models.Shift.facility_id == facility_id,
            models.Shift.date >= start_date,
            models.Shift.date <= end_date,
        )
        .scalar()
    ) or 0

    # Query approved shifts
    approved_shifts = (
        db.query(func.count(models.Shift.id))
        .filter(
            models.Shift.facility_id == facility_id,
            models.Shift.date >= start_date,
            models.Shift.date <= end_date,
            models.Shift.status == ShiftStatus.APPROVED,
        )
        .scalar()
    ) or 0

    # Calculate fill rate percentage
    fill_rate = (approved_shifts / total_shifts * 100) if total_shifts > 0 else 0.0

    return {
        "facility_id": str(facility_id),
        "start_date": start_date,
        "end_date": end_date,
        "total_shifts": total_shifts,
        "filled_shifts": approved_shifts,
        "fill_rate_percentage": round(fill_rate, 2),
    }


def get_time_to_fill_metrics(
    db: Session, facility_id: UUID, start_date: date, end_date: date
) -> dict:
    """
    Calculate average time from shift creation to claim approval.

    Args:
        db: Database session
        facility_id: UUID of the facility
        start_date: Start date for the analysis period
        end_date: End date for the analysis period

    Returns:
        Dictionary with time-to-fill metrics
    """
    # Query approved claims for shifts in the date range
    # Join Shift and Claim tables to get time differences
    results = (
        db.query(
            models.Shift.id.label("shift_id"),
            models.Shift.created_at.label("shift_created_at"),
            models.Claim.updated_at.label("claim_approved_at"),
        )
        .join(models.Claim, models.Shift.id == models.Claim.shift_id)
        .filter(
            models.Shift.facility_id == facility_id,
            models.Shift.date >= start_date,
            models.Shift.date <= end_date,
            models.Claim.status == ClaimStatus.APPROVED,
        )
        .all()
    )

    if not results:
        return {
            "facility_id": str(facility_id),
            "start_date": start_date,
            "end_date": end_date,
            "total_filled_shifts": 0,
            "average_time_to_fill_hours": 0.0,
            "min_time_to_fill_hours": 0.0,
            "max_time_to_fill_hours": 0.0,
        }

    # Calculate time differences in hours
    time_diffs = []
    for result in results:
        time_diff = result.claim_approved_at - result.shift_created_at
        hours = time_diff.total_seconds() / 3600
        time_diffs.append(hours)

    avg_hours = sum(time_diffs) / len(time_diffs) if time_diffs else 0.0
    min_hours = min(time_diffs) if time_diffs else 0.0
    max_hours = max(time_diffs) if time_diffs else 0.0

    return {
        "facility_id": str(facility_id),
        "start_date": start_date,
        "end_date": end_date,
        "total_filled_shifts": len(results),
        "average_time_to_fill_hours": round(avg_hours, 2),
        "min_time_to_fill_hours": round(min_hours, 2),
        "max_time_to_fill_hours": round(max_hours, 2),
    }


def get_shift_statistics(
    db: Session, facility_id: UUID, start_date: date, end_date: date
) -> dict:
    """
    Get comprehensive shift statistics including counts by status and visibility.

    Args:
        db: Database session
        facility_id: UUID of the facility
        start_date: Start date for the analysis period
        end_date: End date for the analysis period

    Returns:
        Dictionary with shift statistics
    """
    # Base query for shifts in the date range
    base_query = db.query(models.Shift).filter(
        models.Shift.facility_id == facility_id,
        models.Shift.date >= start_date,
        models.Shift.date <= end_date,
    )

    total_shifts = base_query.count()

    # Count by status
    status_counts = {}
    for status in ShiftStatus:
        count = base_query.filter(models.Shift.status == status).count()
        status_counts[status.value] = count

    # Count by visibility tier
    tier_counts = {}
    for visibility in ShiftVisibility:
        count = base_query.filter(models.Shift.visibility == visibility).count()
        tier_counts[visibility.value] = count

    # Count premium shifts
    premium_count = base_query.filter(models.Shift.is_premium == True).count()

    return {
        "facility_id": str(facility_id),
        "start_date": start_date,
        "end_date": end_date,
        "total_shifts": total_shifts,
        "by_status": status_counts,
        "by_visibility": tier_counts,
        "premium_shifts": premium_count,
    }


def get_agency_performance(
    db: Session, agency_id: UUID, start_date: date, end_date: date
) -> dict:
    """
    Calculate agency performance metrics including claim statistics and response times.

    Args:
        db: Database session
        agency_id: UUID of the agency
        start_date: Start date for the analysis period
        end_date: End date for the analysis period

    Returns:
        Dictionary with agency performance metrics
    """
    # Get all claims from users belonging to this agency for shifts in the date range
    claims = (
        db.query(models.Claim)
        .join(models.User, models.Claim.user_id == models.User.id)
        .join(models.Shift, models.Claim.shift_id == models.Shift.id)
        .filter(
            models.User.company_id == agency_id,
            models.Shift.date >= start_date,
            models.Shift.date <= end_date,
        )
        .all()
    )

    if not claims:
        return {
            "agency_id": str(agency_id),
            "start_date": start_date,
            "end_date": end_date,
            "total_claims": 0,
            "approved_claims": 0,
            "denied_claims": 0,
            "pending_claims": 0,
            "approval_rate_percentage": 0.0,
            "average_response_time_hours": 0.0,
        }

    total_claims = len(claims)
    approved_claims = sum(1 for c in claims if c.status == ClaimStatus.APPROVED)
    denied_claims = sum(1 for c in claims if c.status == ClaimStatus.DENIED)
    pending_claims = sum(1 for c in claims if c.status == ClaimStatus.PENDING)

    # Calculate approval rate (excluding pending claims)
    decided_claims = approved_claims + denied_claims
    approval_rate = (approved_claims / decided_claims * 100) if decided_claims > 0 else 0.0

    # Calculate average response time (time from claim creation to approval/denial)
    response_times = []
    for claim in claims:
        if claim.status in {ClaimStatus.APPROVED, ClaimStatus.DENIED}:
            time_diff = claim.updated_at - claim.claimed_at
            hours = time_diff.total_seconds() / 3600
            response_times.append(hours)

    avg_response_time = sum(response_times) / len(response_times) if response_times else 0.0

    return {
        "agency_id": str(agency_id),
        "start_date": start_date,
        "end_date": end_date,
        "total_claims": total_claims,
        "approved_claims": approved_claims,
        "denied_claims": denied_claims,
        "pending_claims": pending_claims,
        "approval_rate_percentage": round(approval_rate, 2),
        "average_response_time_hours": round(avg_response_time, 2),
    }

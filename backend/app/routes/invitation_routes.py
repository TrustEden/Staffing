"""Routes for managing facility-to-agency invitations."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app import models
from backend.app.database import get_db
from backend.app.dependencies import get_current_agency_admin, get_current_facility_admin, get_current_user
from backend.app.schemas import InvitationCreate, InvitationResponse
from backend.app.utils.constants import CompanyType, InvitationStatus, RelationshipStatus, UserRole

router = APIRouter(tags=["invitations"])


@router.post("/", response_model=InvitationResponse, status_code=status.HTTP_201_CREATED)
def create_invitation(
    payload: InvitationCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_facility_admin),
) -> InvitationResponse:
    """
    Facility admin creates an invitation for an agency.
    Generates a unique token and sends it to the agency email.
    """
    if not current_user.company_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User must be associated with a facility")

    # Verify the company is a facility
    facility = db.get(models.Company, current_user.company_id)
    if not facility or facility.type != CompanyType.FACILITY:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User must be part of a facility")

    # Generate unique token
    token = secrets.token_urlsafe(32)
    while db.query(models.Invitation).filter(models.Invitation.token == token).first():
        token = secrets.token_urlsafe(32)

    # Calculate expiration datetime
    expires_at = datetime.utcnow() + timedelta(days=payload.expires_in_days)

    # Create invitation
    invitation = models.Invitation(
        facility_id=current_user.company_id,
        agency_email=str(payload.agency_email),
        token=token,
        status=InvitationStatus.PENDING,
        expires_at=expires_at,
    )
    db.add(invitation)
    db.commit()
    db.refresh(invitation)

    # Prepare response
    response = InvitationResponse.model_validate(invitation)
    response.facility_name = facility.name
    return response


@router.get("/{token}", response_model=InvitationResponse)
def verify_invitation(
    token: str,
    db: Session = Depends(get_db),
) -> InvitationResponse:
    """
    Verify an invitation token (public endpoint - no auth required).
    Returns facility info if the token is valid.
    Returns 410 Gone if the token is expired.
    """
    invitation = db.query(models.Invitation).filter(models.Invitation.token == token).first()

    if not invitation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")

    # Check if already accepted
    if invitation.status == InvitationStatus.ACCEPTED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Invitation already accepted")

    # Check if expired
    if invitation.expires_at < datetime.utcnow() or invitation.status == InvitationStatus.EXPIRED:
        # Update status to expired if not already
        if invitation.status != InvitationStatus.EXPIRED:
            invitation.status = InvitationStatus.EXPIRED
            db.commit()
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Invitation has expired")

    # Get facility info
    facility = db.get(models.Company, invitation.facility_id)
    if not facility:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Facility not found")

    response = InvitationResponse.model_validate(invitation)
    response.facility_name = facility.name
    return response


@router.post("/{token}/accept", response_model=dict)
def accept_invitation(
    token: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_agency_admin),
) -> dict:
    """
    Agency admin accepts an invitation.
    Creates a FacilityAgencyRelationship with status='active'.
    """
    if not current_user.company_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User must be associated with an agency")

    # Verify the user's company is an agency
    agency = db.get(models.Company, current_user.company_id)
    if not agency or agency.type != CompanyType.AGENCY:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User must be part of an agency")

    # Get and verify the invitation
    invitation = db.query(models.Invitation).filter(models.Invitation.token == token).first()

    if not invitation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")

    # Check if already accepted
    if invitation.status == InvitationStatus.ACCEPTED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Invitation already accepted")

    # Check if expired
    if invitation.expires_at < datetime.utcnow() or invitation.status == InvitationStatus.EXPIRED:
        # Update status to expired if not already
        if invitation.status != InvitationStatus.EXPIRED:
            invitation.status = InvitationStatus.EXPIRED
            db.commit()
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Invitation has expired")

    # Verify the invitation is for this agency's email
    if current_user.email and current_user.email.lower() != invitation.agency_email.lower():
        # Also check company contact email
        if not agency.contact_email or agency.contact_email.lower() != invitation.agency_email.lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This invitation was sent to a different email address"
            )

    # Get facility
    facility = db.get(models.Company, invitation.facility_id)
    if not facility:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Facility not found")

    # Check if relationship already exists
    existing_relationship = (
        db.query(models.Relationship)
        .filter(
            models.Relationship.facility_id == invitation.facility_id,
            models.Relationship.agency_id == current_user.company_id,
        )
        .first()
    )

    if existing_relationship:
        if existing_relationship.status == RelationshipStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Relationship already exists between this facility and agency"
            )
        elif existing_relationship.status == RelationshipStatus.REVOKED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Previous relationship was revoked. Contact platform admin."
            )
        else:
            # Update existing invited relationship to active
            existing_relationship.status = RelationshipStatus.ACTIVE
            existing_relationship.invite_accepted_at = datetime.utcnow()
    else:
        # Create new relationship
        relationship = models.Relationship(
            facility_id=invitation.facility_id,
            agency_id=current_user.company_id,
            status=RelationshipStatus.ACTIVE,
            invited_by_id=current_user.id,
            invite_accepted_at=datetime.utcnow(),
        )
        db.add(relationship)

    # Mark invitation as accepted
    invitation.status = InvitationStatus.ACCEPTED
    db.commit()

    return {
        "message": "Invitation accepted successfully",
        "facility": facility.name,
        "agency": agency.name,
        "status": "active",
    }


@router.get("/", response_model=list[InvitationResponse])
def list_invitations(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> list[InvitationResponse]:
    """
    List all invitations for the current user's facility.
    Only facility admins can view invitations.
    """
    # Check if user is a facility admin
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can view invitations")

    if not current_user.company_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User must be associated with a company")

    # Verify the user's company is a facility
    facility = db.get(models.Company, current_user.company_id)
    if not facility or facility.type != CompanyType.FACILITY:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only facility admins can view invitations")

    # Get all invitations for this facility
    invitations = (
        db.query(models.Invitation)
        .filter(models.Invitation.facility_id == current_user.company_id)
        .order_by(models.Invitation.created_at.desc())
        .all()
    )

    # Prepare responses with facility name
    responses = []
    for invitation in invitations:
        response = InvitationResponse.model_validate(invitation)
        response.facility_name = facility.name
        responses.append(response)

    return responses

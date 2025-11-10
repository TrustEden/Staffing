from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from backend.app import models
from backend.app.database import get_db
from backend.app.dependencies import get_current_user
from backend.app.schemas import ClaimWithShiftOut, ShiftOut

router = APIRouter(tags=["claims"])


@router.get("/me", response_model=List[ClaimWithShiftOut])
def list_my_claims(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> list[ClaimWithShiftOut]:
    claims = (
        db.query(models.Claim)
        .options(joinedload(models.Claim.shift).joinedload(models.Shift.facility))
        .filter(models.Claim.user_id == current_user.id)
        .order_by(models.Claim.created_at.desc())
        .all()
    )

    # Add facility name to each claim's shift
    claim_outs = []
    for claim in claims:
        claim_dict = ClaimWithShiftOut.model_validate(claim).model_dump()
        if claim.shift and claim.shift.facility:
            claim_dict['shift']['facility_name'] = claim.shift.facility.name
        claim_outs.append(ClaimWithShiftOut(**claim_dict))

    return claim_outs

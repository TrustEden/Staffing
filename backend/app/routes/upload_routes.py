from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from backend.app import models
from backend.app.database import get_db
from backend.app.dependencies import get_current_user
from backend.app.schemas import ShiftOut
from backend.app.services.excel_parser import ExcelParser
from backend.app.services.scheduler import ShiftScheduler
from backend.app.utils.constants import CompanyType, ShiftStatus, ShiftVisibility, UserRole

router = APIRouter(tags=["uploads"])
parser = ExcelParser()
scheduler = ShiftScheduler()


@router.post("/shifts", response_model=list[ShiftOut], status_code=status.HTTP_201_CREATED)
async def upload_shifts(
    facility_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> list[ShiftOut]:
    _ensure_facility_admin(current_user, facility_id)
    facility = db.get(models.Company, facility_id)
    if not facility or facility.type != CompanyType.FACILITY:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Facility not found")

    file_bytes = await file.read()
    try:
        records = parser.parse(file_bytes, file_name=file.filename or "upload.xlsx")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    created_shifts: list[models.Shift] = []
    for record in records:
        visibility_value = record.get("visibility", "all")
        try:
            visibility = ShiftVisibility(visibility_value)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid visibility '{visibility_value}'",
            ) from exc

        release_at = None
        if visibility == ShiftVisibility.TIERED:
            base = datetime.combine(record["date"], record["start_time"], tzinfo=timezone.utc)
            release_at = base - timedelta(hours=scheduler.settings.default_tiered_release_hours)

        shift = models.Shift(
            facility_id=facility_id,
            date=record["date"],
            start_time=record["start_time"],
            end_time=record["end_time"],
            role_required=record["role_required"],
            visibility=visibility,
            notes=record.get("notes"),
            posted_by_id=current_user.id,
            status=ShiftStatus.OPEN,
            release_at=release_at,
        )
        db.add(shift)
        created_shifts.append(shift)

    db.commit()
    for shift in created_shifts:
        db.refresh(shift)
    return [ShiftOut.model_validate(shift) for shift in created_shifts]


def _ensure_facility_admin(user: models.User, facility_id: UUID) -> None:
    if user.company_id is None:
        return
    if user.company_id != facility_id or user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Facility admin required")

from __future__ import annotations

from datetime import datetime
from typing import NamedTuple
from uuid import UUID

from sqlalchemy.orm import Session

from backend.app import models
from backend.app.utils.constants import BACK_TO_BACK_WARNING_MINUTES, ClaimStatus


class ConflictResult(NamedTuple):
    hard_conflicts: list[str]
    warnings: list[str]


class ShiftConflictChecker:
    def __init__(self, session: Session):
        self.session = session

    def check_for_user(self, user_id: UUID, shift: models.Shift) -> ConflictResult:
        hard_conflicts: list[str] = []
        warnings: list[str] = []

        claims = (
            self.session.query(models.Claim)
            .filter(
                models.Claim.user_id == user_id,
                models.Claim.status.in_([ClaimStatus.PENDING, ClaimStatus.APPROVED]),
            )
            .all()
        )

        shift_start = datetime.combine(shift.date, shift.start_time)
        shift_end = datetime.combine(shift.date, shift.end_time)

        for claim in claims:
            existing_shift = claim.shift
            existing_start = datetime.combine(existing_shift.date, existing_shift.start_time)
            existing_end = datetime.combine(existing_shift.date, existing_shift.end_time)

            if existing_shift.id == shift.id:
                continue

            if self._overlaps(existing_start, existing_end, shift_start, shift_end):
                hard_conflicts.append(
                    f"Overlaps with shift {existing_shift.id} from {existing_shift.start_time} to {existing_shift.end_time}"
                )
                continue

            gap_minutes = (shift_start - existing_end).total_seconds() / 60
            if 0 <= gap_minutes < BACK_TO_BACK_WARNING_MINUTES:
                warnings.append(
                    f"Less than {BACK_TO_BACK_WARNING_MINUTES} minutes between this shift and {existing_shift.id}"
                )

        return ConflictResult(hard_conflicts=hard_conflicts, warnings=warnings)

    @staticmethod
    def _overlaps(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
        return max(a_start, b_start) < min(a_end, b_end)

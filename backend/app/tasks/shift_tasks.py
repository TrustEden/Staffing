"""Background tasks for automated shift tier releases."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from backend.app.database import SessionLocal
from backend.app.models import Notification, Shift, User
from backend.app.utils.constants import ShiftStatus, ShiftVisibility, UserRole

logger = logging.getLogger(__name__)


def release_tier_1_shifts() -> dict[str, int]:
    """
    Find shifts where tier_1_release <= now and visibility='internal',
    update visibility to 'tier_1'.

    Returns:
        dict with count of shifts released
    """
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)

        # Find all shifts that need to be released to tier 1
        stmt = select(Shift).where(
            Shift.visibility == ShiftVisibility.INTERNAL,
            Shift.tier_1_release <= now,
            Shift.tier_1_release.isnot(None),
            Shift.status == ShiftStatus.OPEN,
        )
        shifts = db.execute(stmt).scalars().all()

        count = 0
        for shift in shifts:
            shift.visibility = ShiftVisibility.TIER_1
            count += 1
            logger.info(
                f"Released shift {shift.id} to tier 1 (facility: {shift.facility_id}, "
                f"date: {shift.date})"
            )

        if count > 0:
            db.commit()
            logger.info(f"Released {count} shifts to tier 1")

        return {"released_to_tier_1": count}

    except Exception as e:
        db.rollback()
        logger.error(f"Error in release_tier_1_shifts: {e}", exc_info=True)
        raise
    finally:
        db.close()


def release_tier_2_shifts() -> dict[str, int]:
    """
    Find shifts where tier_2_release <= now and visibility='tier_1',
    update visibility to 'tier_2'.

    Returns:
        dict with count of shifts released
    """
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)

        # Find all shifts that need to be released to tier 2
        stmt = select(Shift).where(
            Shift.visibility == ShiftVisibility.TIER_1,
            Shift.tier_2_release <= now,
            Shift.tier_2_release.isnot(None),
            Shift.status == ShiftStatus.OPEN,
        )
        shifts = db.execute(stmt).scalars().all()

        count = 0
        for shift in shifts:
            shift.visibility = ShiftVisibility.TIER_2
            count += 1
            logger.info(
                f"Released shift {shift.id} to tier 2 (facility: {shift.facility_id}, "
                f"date: {shift.date})"
            )

        if count > 0:
            db.commit()
            logger.info(f"Released {count} shifts to tier 2")

        return {"released_to_tier_2": count}

    except Exception as e:
        db.rollback()
        logger.error(f"Error in release_tier_2_shifts: {e}", exc_info=True)
        raise
    finally:
        db.close()


def check_shift_releases() -> dict[str, int]:
    """
    Periodic task that runs both tier release functions.
    This should be called by the scheduler every 15 minutes.

    Returns:
        dict with counts of shifts released in both tiers
    """
    logger.info("Running periodic shift release check")

    try:
        tier_1_result = release_tier_1_shifts()
        tier_2_result = release_tier_2_shifts()

        result = {
            **tier_1_result,
            **tier_2_result,
        }

        total = result.get("released_to_tier_1", 0) + result.get("released_to_tier_2", 0)
        logger.info(f"Shift release check completed. Total releases: {total}")

        return result

    except Exception as e:
        logger.error(f"Error in check_shift_releases: {e}", exc_info=True)
        raise


def send_reminder_notifications() -> dict[str, int]:
    """
    Find unfilled shifts starting in 24 hours and notify facility admins.

    Returns:
        dict with count of notifications sent
    """
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        reminder_window_start = now + timedelta(hours=23, minutes=45)
        reminder_window_end = now + timedelta(hours=24, minutes=15)

        # Find shifts starting in approximately 24 hours that are still open
        stmt = select(Shift).where(
            Shift.status == ShiftStatus.OPEN,
        )
        shifts = db.execute(stmt).scalars().all()

        # Filter shifts that start in the 24-hour window
        shifts_to_notify = []
        for shift in shifts:
            shift_start = datetime.combine(shift.date, shift.start_time, tzinfo=timezone.utc)
            if reminder_window_start <= shift_start <= reminder_window_end:
                shifts_to_notify.append(shift)

        notification_count = 0
        for shift in shifts_to_notify:
            # Find facility admins for this shift
            admin_stmt = select(User).where(
                User.company_id == shift.facility_id,
                User.role == UserRole.ADMIN,
                User.is_active == True,
            )
            admins = db.execute(admin_stmt).scalars().all()

            for admin in admins:
                notification = Notification(
                    recipient_id=admin.id,
                    type="shift_reminder",
                    content=(
                        f"Reminder: Shift on {shift.date} at {shift.start_time} "
                        f"for {shift.role_required} is still unfilled and starts in 24 hours."
                    ),
                    read=False,
                )
                db.add(notification)
                notification_count += 1
                logger.info(
                    f"Sent reminder notification to admin {admin.id} for shift {shift.id}"
                )

        if notification_count > 0:
            db.commit()
            logger.info(f"Sent {notification_count} reminder notifications")

        return {"notifications_sent": notification_count}

    except Exception as e:
        db.rollback()
        logger.error(f"Error in send_reminder_notifications: {e}", exc_info=True)
        raise
    finally:
        db.close()

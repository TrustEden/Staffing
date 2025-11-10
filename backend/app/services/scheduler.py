from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from backend.app import models
from backend.app.utils.constants import ShiftVisibility
from backend.config import get_settings

logger = logging.getLogger(__name__)

# Optional RQ imports - gracefully handle if Redis is not available
try:
    import redis
    from rq import Queue
    from rq_scheduler import Scheduler

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis/RQ not available. Background tasks will be disabled.")


class ShiftScheduler:
    """Scheduler utilities for tiered shift release with RQ support."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.redis_conn = None
        self.queue = None
        self.scheduler = None

        if REDIS_AVAILABLE:
            try:
                self.redis_conn = redis.from_url(self.settings.redis_url)
                self.queue = Queue("default", connection=self.redis_conn)
                self.scheduler = Scheduler(queue=self.queue, connection=self.redis_conn)
                logger.info("Redis connection established for task scheduling")
            except Exception as e:
                logger.warning(f"Could not connect to Redis: {e}. Background tasks disabled.")
                self.redis_conn = None
                self.queue = None
                self.scheduler = None

    def compute_release_at(self, shift: models.Shift) -> datetime:
        if shift.release_at:
            return shift.release_at
        base = datetime.combine(shift.date, shift.start_time, tzinfo=timezone.utc)
        return base - timedelta(hours=self.settings.default_tiered_release_hours)

    def should_release_to_agencies(self, shift: models.Shift) -> bool:
        if shift.visibility != ShiftVisibility.TIERED:
            return False
        release_at = shift.release_at or self.compute_release_at(shift)
        return datetime.now(timezone.utc) >= release_at

    def schedule_shift_release(
        self,
        shift_id: UUID,
        tier_1_time: datetime | None,
        tier_2_time: datetime | None,
    ) -> bool:
        """
        Schedule background tasks for shift tier releases.

        Args:
            shift_id: ID of the shift to release
            tier_1_time: When to release to tier 1 (optional)
            tier_2_time: When to release to tier 2 (optional)

        Returns:
            True if tasks were scheduled, False if Redis is unavailable
        """
        if not self.scheduler:
            logger.warning(
                f"Cannot schedule release for shift {shift_id}: Redis not available"
            )
            return False

        try:
            # Note: RQ doesn't schedule individual tasks for specific times efficiently.
            # Instead, we rely on the periodic check_shift_releases task to handle
            # releases when the time comes. This function is here for API compatibility
            # and could be extended to use RQ's scheduled jobs if needed.

            # For now, just log that the shift has tier release times set
            if tier_1_time:
                logger.info(
                    f"Shift {shift_id} scheduled for tier 1 release at {tier_1_time}"
                )
            if tier_2_time:
                logger.info(
                    f"Shift {shift_id} scheduled for tier 2 release at {tier_2_time}"
                )

            return True

        except Exception as e:
            logger.error(f"Error scheduling shift release: {e}", exc_info=True)
            return False

    def setup_scheduler(self) -> bool:
        """
        Configure periodic tasks for shift releases.
        Sets up check_shift_releases to run every 15 minutes.

        Returns:
            True if scheduler was set up, False if Redis is unavailable
        """
        if not self.scheduler:
            logger.warning("Cannot setup scheduler: Redis not available")
            return False

        try:
            from backend.app.tasks.shift_tasks import (
                check_shift_releases,
                send_reminder_notifications,
            )

            # Schedule check_shift_releases every 15 minutes
            self.scheduler.cron(
                "*/15 * * * *",  # Every 15 minutes
                func=check_shift_releases,
                queue_name="default",
                id="check_shift_releases",
                timeout=300,  # 5 minute timeout
            )
            logger.info("Scheduled check_shift_releases to run every 15 minutes")

            # Schedule reminder notifications to run every hour
            self.scheduler.cron(
                "0 * * * *",  # Every hour at minute 0
                func=send_reminder_notifications,
                queue_name="default",
                id="send_reminder_notifications",
                timeout=300,
            )
            logger.info("Scheduled send_reminder_notifications to run every hour")

            return True

        except Exception as e:
            logger.error(f"Error setting up scheduler: {e}", exc_info=True)
            return False

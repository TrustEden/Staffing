#!/usr/bin/env python3
"""
RQ Worker entrypoint for Healthcare Staffing Bridge background tasks.

This worker processes background jobs from the Redis queue, including:
- Automated shift tier releases
- Reminder notifications for unfilled shifts
- Periodic maintenance tasks

Usage:
    python -m backend.worker

Or with multiple workers:
    rq worker -c backend.worker_config

Environment variables:
    REDIS_URL: Redis connection URL (default: redis://localhost:6379)
"""

import logging
import sys

import redis
from rq import Worker
from rq_scheduler import Scheduler

from backend.config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def main():
    """Start the RQ worker and scheduler."""
    settings = get_settings()

    try:
        # Connect to Redis
        redis_conn = redis.from_url(settings.redis_url)
        redis_conn.ping()
        logger.info(f"Connected to Redis at {settings.redis_url}")

    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        logger.error("Make sure Redis is running and REDIS_URL is configured correctly.")
        sys.exit(1)

    # Setup the scheduler for periodic tasks
    try:
        from backend.app.services.scheduler import ShiftScheduler

        scheduler_service = ShiftScheduler()
        if scheduler_service.scheduler:
            # Setup periodic tasks (this is idempotent)
            scheduler_service.setup_scheduler()
            logger.info("Periodic tasks scheduled successfully")
        else:
            logger.warning("Scheduler not available - periodic tasks will not run")

    except Exception as e:
        logger.error(f"Failed to setup scheduler: {e}", exc_info=True)
        logger.warning("Worker will continue without periodic task scheduling")

    # Start the worker
    logger.info("Starting RQ worker for 'default' queue...")
    logger.info("Listening for tasks. Press Ctrl+C to exit.")

    try:
        # Create worker instance
        worker = Worker(
            queues=["default"],
            connection=redis_conn,
            name=f"healthcare-bridge-worker",
        )

        # Start processing jobs
        worker.work(with_scheduler=True)

    except KeyboardInterrupt:
        logger.info("Worker interrupted by user. Shutting down...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Worker error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

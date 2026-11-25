"""Bounded background job queue for running Playwright search jobs."""

import asyncio
import sys
from concurrent.futures import ThreadPoolExecutor
from uuid import UUID

from app.automation.bot import execute_igr_job
from app.config import settings
from app.database import SessionLocal
from app.models import AutomationLog, SearchJob

_executor = ThreadPoolExecutor(max_workers=max(1, settings.job_concurrency), thread_name_prefix="igr-worker")


def _run_job_sync(job_id: UUID):
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(execute_igr_job(job_id))


def submit_job_to_queue(job_id: UUID):
    """Submit a job UUID to the bounded worker pool."""
    _executor.submit(_run_job_sync, job_id)


def recover_interrupted_jobs():
    """Mark jobs left in PROCESSING/AWAITING_CAPTCHA after a crash so users can retry them."""
    db = SessionLocal()
    try:
        stale_jobs = (
            db.query(SearchJob)
            .filter(SearchJob.status.in_(["PROCESSING", "AWAITING_CAPTCHA"]))
            .all()
        )
        for job in stale_jobs:
            job.status = "FAILED"
            job.captcha_image_base64 = None
            job.error_message = "Server restarted while job was active. Click Retry to re-run."
            db.add(
                AutomationLog(
                    job_id=job.id,
                    level="WARNING",
                    step="RECOVERY",
                    message=job.error_message,
                )
            )
        db.commit()
    finally:
        db.close()

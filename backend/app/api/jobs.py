import asyncio
from pathlib import Path
from uuid import UUID
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.automation.bot import execute_igr_job
from app.database import get_db
from app.models import SearchJob, PropertyRecord, DocumentFile, AutomationLog
from app.models.schemas import (
    CreateJobRequest,
    CaptchaSolutionRequest,
    JobSummaryResponse,
    JobDetailResponse,
    PropertyRecordResponse,
)
import sys
import asyncio
router = APIRouter(prefix="/api", tags=["IGR Automation"])


def add_log(db: Session, job_id: UUID, message: str, level: str = "INFO", step: str | None = None):
    log = AutomationLog(job_id=job_id, level=level, step=step, message=message)
    db.add(log)
    db.commit()


def enqueue_job(job_id: UUID):
    """Runs the async Playwright bot inside a background task."""
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(execute_igr_job(job_id))


@router.post("/jobs", response_model=JobSummaryResponse, status_code=201)
def create_search_job(
    payload: CreateJobRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    job = SearchJob(
        search_type=payload.search_type,
        criteria=payload.criteria,
        status="PENDING",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    add_log(db, job.id, f"Queued {job.search_type} search job.", step="QUEUE")
    background_tasks.add_task(enqueue_job, job.id)

    return JobSummaryResponse(
        id=job.id,
        search_type=job.search_type,
        criteria=job.criteria,
        status=job.status,
        error_message=job.error_message,
        retry_count=job.retry_count,
        created_at=job.created_at,
        updated_at=job.updated_at,
        record_count=0,
    )


@router.get("/jobs", response_model=list[JobSummaryResponse])
def list_jobs(db: Session = Depends(get_db)):
    jobs = db.query(SearchJob).order_by(SearchJob.created_at.desc()).all()
    return [
        JobSummaryResponse(
            id=j.id,
            search_type=j.search_type,
            criteria=j.criteria,
            status=j.status,
            error_message=j.error_message,
            retry_count=j.retry_count,
            created_at=j.created_at,
            updated_at=j.updated_at,
            record_count=len(j.records),
        )
        for j in jobs
    ]


@router.get("/jobs/{job_id}", response_model=JobDetailResponse)
def get_job_detail(job_id: UUID, db: Session = Depends(get_db)):
    job = db.query(SearchJob).filter(SearchJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobDetailResponse(
        id=job.id,
        search_type=job.search_type,
        criteria=job.criteria,
        status=job.status,
        error_message=job.error_message,
        retry_count=job.retry_count,
        created_at=job.created_at,
        updated_at=job.updated_at,
        record_count=len(job.records),
        captcha_image_base64=job.captcha_image_base64,
        logs=job.logs,
        records=job.records,
    )


@router.post("/jobs/{job_id}/captcha")
def submit_captcha(job_id: UUID, payload: CaptchaSolutionRequest, db: Session = Depends(get_db)):
    job = db.query(SearchJob).filter(SearchJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job.captcha_solution = payload.solution.strip()
    job.status = "PROCESSING"
    db.commit()
    add_log(db, job.id, "CAPTCHA solution received from dashboard.", step="CAPTCHA")
    return {"message": "CAPTCHA solution submitted", "job_id": str(job.id)}


@router.post("/jobs/{job_id}/retry", response_model=JobSummaryResponse)
def retry_job(job_id: UUID, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    job = db.query(SearchJob).filter(SearchJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job.status = "PENDING"
    job.error_message = None
    job.captcha_solution = None
    job.captcha_image_base64 = None
    job.retry_count = (job.retry_count or 0) + 1
    db.commit()
    db.refresh(job)
    add_log(db, job.id, f"Retry #{job.retry_count} queued.", step="RETRY")
    background_tasks.add_task(enqueue_job, job.id)
    return JobSummaryResponse(
        id=job.id,
        search_type=job.search_type,
        criteria=job.criteria,
        status=job.status,
        error_message=job.error_message,
        retry_count=job.retry_count,
        created_at=job.created_at,
        updated_at=job.updated_at,
        record_count=len(job.records),
    )


@router.get("/records", response_model=list[PropertyRecordResponse])
def list_records(db: Session = Depends(get_db)):
    return db.query(PropertyRecord).order_by(PropertyRecord.created_at.desc()).all()


@router.get("/documents/{doc_id}/download")
def download_document(doc_id: UUID, db: Session = Depends(get_db)):
    doc = db.query(DocumentFile).filter(DocumentFile.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    file_path = Path(doc.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File missing on disk")
    return FileResponse(path=file_path, filename=doc.file_name, media_type=doc.mime_type)